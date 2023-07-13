#!/usr/bin/env python3

# Copyright 2023 nexenio
import logging
import os
import time

import regex

from kapitan.errors import InventoryError
from kapitan.resolvers import register_resolvers
from omegaconf import ListMergeMode, Node, OmegaConf, errors

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

    register_resolvers(inventory_path)

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

    # using nodes for reclass legacy code
    inv = {"nodes": {}}

    # prepare logging
    logger.info(f"Found {len(selected_targets)} targets")

    # load targets
    for target in selected_targets:
        try:
            # start = time.time()
            name, config = load_target(target, classes_searchpath, ignore_class_notfound)
            inv["nodes"][name] = config
            # print(time.time() - start)
        except Exception as e:
            raise InventoryError(f"{target['name']}: {e}")

    return inv


def load_target(target: dict, classes_searchpath: str, ignore_class_notfound: bool = False):
    """
    load only one target with all its classes
    """

    target_name = target["name"]
    target_path = target["path"]

    target_config = OmegaConf.load(target_path)
    target_config_classes = target_config.get("classes", [])
    target_config_parameters = OmegaConf.create(target_config.get("parameters", {}))
    target_config = {}

    classes_redundancy_check = set()

    # load classes for targets
    for class_name in target_config_classes:
        # resolve class path
        class_path = os.path.join(classes_searchpath, *class_name.split("."))

        if class_path in classes_redundancy_check:
            continue

        classes_redundancy_check.add(class_path)

        if os.path.isfile(class_path + ".yml"):
            class_path += ".yml"
        elif os.path.isdir(class_path):
            # search for init file
            init_path = os.path.join(classes_searchpath, *class_name.split("."), "init") + ".yml"
            if os.path.isfile(init_path):
                class_path = init_path
        elif ignore_class_notfound:
            logger.debug(f"Could not find {class_path}")
            continue
        else:
            raise InventoryError(f"Class {class_name} not found.")

        # load classes recursively
        class_config = OmegaConf.load(class_path)

        # resolve relative class names
        new_classes = class_config.pop("classes", [])
        for new in new_classes:
            if new.startswith("."):
                new = ".".join(class_name.split(".")[0:-1]) + new

            target_config_classes.append(new)

        class_config_parameters = OmegaConf.create(class_config.get("parameters", {}))

        # merge target with loaded classes
        if target_config_parameters:
            target_config_parameters = OmegaConf.unsafe_merge(
                class_config_parameters, target_config_parameters, list_merge_mode=ListMergeMode.EXTEND
            )
        else:
            target_config_parameters = class_config_parameters

    if not target_config_parameters:
        raise InventoryError("empty target")

    # append meta data (legacy: _reclass_)
    target_config_parameters["_reclass_"] = {
        "name": {
            "full": target_name,
            "parts": target_name.split("."),
            "path": target_name.replace(".", "/"),
            "short": target_name.split(".")[-1],
        }
    }

    # resolve references / interpolate values
    OmegaConf.resolve(target_config_parameters)
    target_config["parameters"] = OmegaConf.to_object(target_config_parameters)

    # obtain target name to insert in inv dict
    try:
        target_name = target_config["parameters"]["kapitan"]["vars"]["target"]
    except KeyError:
        logger.warning(f"Could not resolve target name on target {target_name}")

    return target_name, target_config


def migrate(inventory_path: str) -> None:
    """migrates all .yml/.yaml files in the given path to omegaconfs syntax"""

    for root, subdirs, files in os.walk(inventory_path):
        for file in files:
            file = os.path.join(root, file)
            name, ext = os.path.splitext(file)

            if ext not in (".yml", ".yaml"):
                continue

            try:
                with open(file, "r+") as file:
                    content = file.read()
                    file.seek(0)

                    # replace colons in tags and replace _reclass_ with _meta_
                    updated_content = regex.sub(
                        r"(?<!\\)\${([^{}\\]+?)}",
                        lambda match: "${"
                        + match.group(1).replace(":", ".").replace("_reclass_", "_meta_")
                        + "}",
                        content,
                    )

                    # replace escaped tags with specific resolver
                    excluded_chars = "!"
                    invalid = any(c in updated_content for c in excluded_chars)
                    updated_content = regex.sub(
                        r"\\\${([^{}]+?)}",
                        lambda match: ("${tag:" if not invalid else "\\\\\\${") + match.group(1) + "}",
                        updated_content,
                    )

                    file.write(updated_content)
            except Exception as e:
                InventoryError(f"{file}: error with migration: {e}")
