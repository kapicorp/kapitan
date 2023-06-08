#!/usr/bin/env python3

# Copyright 2023 nexenio
import logging
from multiprocessing.pool import ThreadPool
from functools import partial
import os
import time

from kapitan.errors import InventoryError
from kapitan.oc.omegaconf import Node, OmegaConf, errors

logger = logging.getLogger(__name__)


def inventory_omegaconf(inventory_path, ignore_class_notfound=False, targets=[], compose_node_name=False):
    """
    generates inventory from yaml files using OmegaConf
    """
    # TBD: add config to specify paths (do we need that?)
    targets_searchpath = os.path.join(inventory_path, "targets")
    classes_searchpath = os.path.join(inventory_path, "classes")

    def key(_node_: Node):
        """resolver function, that returns the name of its parent key"""
        return _node_._key()

    def fullkey(_node_: Node):
        """resolver function, that returns the full name of its parent key"""
        return _node_._get_full_key("")

    def dep(name: str):
        """resolver function, that returns a parameterized dependency"""
        return f"dependency{name}"

    OmegaConf.register_new_resolver("key", key)
    OmegaConf.register_new_resolver("fullkey", fullkey)

    # kapitan helpers
    OmegaConf.register_new_resolver("dep", dep)
    selected_targets = []

    # loop through targets searchpath and load all targets
    for root, dirs, files in os.walk(targets_searchpath):
        for target_name in files:
            target_path = os.path.join(root, target_name)

            # split file extension and check if yml/yaml
            target_name, ext = os.path.splitext(target_name)
            if ext not in (".yml", ".yaml"):
                logger.debug(f"{target_name}: targets have to be .yml or .yaml files.")
                # RAISE ERROR
                continue

            # skip targets if they are not specified with -t flag
            if targets and target_name not in targets:
                continue

            # compose node name
            if compose_node_name:
                target_name = str(os.path.splitext(target_path)[0]).replace(targets_searchpath + os.sep, "")
                target_name = target_name.replace("/", ".")

            selected_targets.append({"name": target_name, "path": target_path})

    inv = {"nodes": {}}
    # load targets parallel

    stamp = time.time()
    for target in selected_targets:
        try:
            name, config = load_target(target, classes_searchpath, ignore_class_notfound)
            inv["nodes"][name] = config
        except Exception as e:
            print(target, e)

    # pool = ThreadPool(8)

    # worker = partial(
    #     load_target,
    #     classes_searchpath=classes_searchpath,
    #     ignore_class_notfound=ignore_class_notfound,
    # )

    # for p in pool.imap(worker, selected_targets):
    #     name, config = p
    #     inv["nodes"][name] = config

    # pool.close()

    print(f"real time: {time.time() - stamp}")

    # TBD: refactor inventory accessing (targets.py, cmd_parser.py)
    # that it only receives the targets and not everything
    return inv


def load_target(target: dict, classes_searchpath: str, ignore_class_notfound: bool = False):
    # load the target
    target_name = target["name"]
    target_path = target["path"]

    try:
        target_config = OmegaConf.load(target_path)
    except:
        print(target)
        return "", {}

    target_config_classes = target_config.pop("classes", [])

    # load classes for targets
    for class_name in target_config_classes:
        # resolve class name (relative paths TBD)
        class_path = os.path.join(classes_searchpath, *class_name.split(".")) + ".yml"
        if os.path.isfile(class_path):
            # load classes recursively
            class_config = OmegaConf.load(class_path)
            target_config_classes.extend(class_config.pop("classes", []))

        elif not ignore_class_notfound:
            raise InventoryError(f"{target_name}: Class {class_name} not found.")
        else:
            continue

        # merge target with loaded classes
        if target_config.get("parameters"):
            target_config = OmegaConf.merge(class_config, target_config, extend_lists=True)
        else:
            target_config = class_config

    if not target_config:
        raise InventoryError(f"{target_name}: empty target")

    if not target_config.get("parameters"):
        raise InventoryError(f"{target_name}: target has no parameters")

    # append meta data _reclass_ (legacy) (refactoring TBD)
    target_config["parameters"]["_reclass_"] = {
        "name": {"full": target_name, "path": target_name, "short": target_name}
    }

    # resolve references / interpolate values
    try:
        target_config = OmegaConf.to_container(target_config, resolve=True)
    except errors.OmegaConfBaseException as e:
        raise InventoryError(f"{target_name}: {e.__context__}")

    # obtain target name to insert in inv dict (legacy) (refactoring TBD)
    try:
        target_name = target_config["parameters"]["kapitan"]["vars"]["target"]
    except KeyError:
        logger.warning(f"Could not resolve target name on target {target_name}")

    # # stamp = time.time()
    # logger.info("loaded %s in %.4f", target_name, 1000*(time.time() - stamp))

    return target_name, target_config
