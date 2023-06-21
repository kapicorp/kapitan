#!/usr/bin/env python3

# Copyright 2023 nexenio
import logging
import os

from kapitan.errors import InventoryError
from omegaconf import Node, OmegaConf, errors, ListMergeMode

logger = logging.getLogger(__name__)


def inventory_omegaconf(
    inventory_path: str,
    ignore_class_notfound: bool = False,
    targets: list = [],
    compose_node_name: bool = False,
) -> dict:
    """
    generates inventory from yaml files using OmegaConf
    """

    # add config option to specify paths
    targets_searchpath = os.path.join(inventory_path, "targets")
    classes_searchpath = os.path.join(inventory_path, "classes")

    register_resolvers()

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

    # load targets
    for target in selected_targets:
        try:
            name, config = load_target(target, classes_searchpath, ignore_class_notfound)
            inv["nodes"][name] = config
        except Exception as e:
            logger.error(f"{target['name']}: {e}")

    return inv


def load_target(target: dict, classes_searchpath: str, ignore_class_notfound: bool = False):
    """
    load only one target with all its classes
    """

    target_name = target["name"]
    target_path = target["path"]

    target_config = OmegaConf.load(target_path)

    target_config_classes = target_config.pop("classes", [])

    # load classes for targets
    for class_name in target_config_classes:
        # resolve class paths
        class_path = os.path.join(classes_searchpath, *class_name.split("."))

        # search for init file
        if os.path.isdir(class_path):
            init_path = os.path.join(classes_searchpath, *class_name.split("."), "init") + ".yml"
            if os.path.isfile(init_path):
                class_path = init_path
        else:
            class_path += ".yml"

        if not os.path.isfile(class_path):
            if not ignore_class_notfound:
                raise InventoryError(f"Class {class_name} not found.")

        # load classes recursively
        class_config = OmegaConf.load(class_path)

        # resolve relative class names
        new_classes = class_config.pop("classes", [])
        for new in new_classes:
            if new.startswith("."):
                new = ".".join(class_name.split(".")[0:-1]) + new

            target_config_classes.append(new)

        # merge target with loaded classes
        if target_config.get("parameters"):
            target_config = OmegaConf.merge(class_config, target_config, list_merge_mode=ListMergeMode.EXTEND)
        else:
            target_config = class_config

    if not target_config:
        raise InventoryError("empty target")

    if not target_config.get("parameters"):
        raise InventoryError("target has no parameters")

    # append meta data _reclass_ (legacy)
    target_config["parameters"]["_reclass_"] = {
        "name": {
            "full": target_name,
            "parts": target_name.split("."),
            "path": target_name,
            "short": target_name,
        }
    }

    # resolve references / interpolate values
    try:
        target_config = OmegaConf.to_container(target_config, resolve=True)
    except errors.OmegaConfBaseException as e:
        raise InventoryError(e.__context__)

    # obtain target name to insert in inv dict
    try:
        target_name = target_config["parameters"]["kapitan"]["vars"]["target"]
    except KeyError:
        logger.warning(f"Could not resolve target name on target {target_name}")

    return target_name, target_config


def key(_node_: Node):
    """resolver function, that returns the name of its parent key"""
    return _node_._key()


def fullkey(_node_: Node):
    """resolver function, that returns the full name of its parent key"""
    return _node_._get_full_key("")


def dep(name: str, name2):
    """resolver function, that returns a parameterized dependency"""
    return {name: "abc", name2: "ghf"}


def register_resolvers():
    # utils
    OmegaConf.register_new_resolver("key", key)
    OmegaConf.register_new_resolver("fullkey", fullkey)

    # kapitan helpers
    OmegaConf.register_new_resolver("dep", dep)
