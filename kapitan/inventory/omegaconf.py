#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
import tempfile
from copy import deepcopy
from time import time

import regex
import yaml
from omegaconf import ListMergeMode, OmegaConf

from kapitan.errors import InventoryError
from kapitan.inventory.resolvers import register_resolvers

logger = logging.getLogger(__name__)


class InventoryTarget:
    targets_path: str
    logfile: str

    def __init__(self, target_name: str, target_path: str) -> None:

        self.path = target_path
        self.name = target_name

        # compose node name
        self.composed_name = (
            os.path.splitext(target_path)[0].replace(self.targets_path + os.sep, "").replace("/", ".")
        )

        self.classes: list = []
        self.parameters: dict = {}
        self.classes_redundancy_check: set = set()

    def _merge(self, class_parameters):
        if not self.parameters:
            self.parameters = class_parameters
        else:
            # TODO: if BackendOmegaConf.logfile:
            merged_parameters = OmegaConf.unsafe_merge(
                class_parameters,
                self.parameters,
                list_merge_mode=ListMergeMode.EXTEND,
                # log_filename=logfile,
            )

            self.parameters = merged_parameters

    def _resolve(self):
        escape_interpolation_strings = False
        OmegaConf.resolve(self.parameters, escape_interpolation_strings)
        self.parameters = OmegaConf.to_object(self.parameters)

    def add_metadata(self):
        # append meta data (legacy: _reclass_)
        _meta_ = {
            "name": {
                "full": self.name,
                "parts": self.name.split("."),
                "path": self.name.replace(".", "/"),
                "short": self.name.split(".")[-1],
            }
        }
        self.parameters["_meta_"] = _meta_
        self.parameters["_reclass_"] = _meta_  # legacy


class InventoryClass:
    classes_path: str = "./inventory/classes"

    def __init__(self, class_path: str) -> None:
        self.path = class_path
        self.name = os.path.splitext(class_path)[0].replace(self.classes_path + os.sep, "").replace("/", ".")
        self.parameters = {}
        self.dependents = []


class OmegaConfBackend:
    inventory_path: str
    targets_searchpath: str
    classes_searchpath: str
    ignore_class_notfound: bool
    targets: list
    compose_node_name: bool
    logfile: str
    classes_cache: dict = {}

    def __init__(
        self,
        inventory_path: str,
        ignore_class_notfound: bool = False,
        targets: list = [],
        compose_node_name: bool = False,
        logfile: str = "",
    ):
        logger.debug("Using omegaconf as inventory backend")
        logger.warning("NOTE: OmegaConf inventory is currently in experimental mode.")

        self.inventory_path = inventory_path
        self.ignore_class_notfound = ignore_class_notfound
        self.targets = targets
        self.compose_node_name = compose_node_name
        self.logfile = logfile
        # TODO: add config option to specify paths
        self.targets_searchpath = os.path.join(inventory_path, "targets")
        self.classes_searchpath = os.path.join(inventory_path, "classes")
        InventoryTarget.targets_path = self.targets_searchpath
        InventoryClass.classes_path = self.classes_searchpath

    def inventory(self):

        register_resolvers(self.inventory_path)
        selected_targets = self.get_selected_targets()

        # TODO: add flag for multiprocessing
        use_mp = False

        if not use_mp:
            nodes = {}
            # load targets one by one
            for target in selected_targets:
                try:
                    self.load_target(target)
                    nodes[target.name] = {"parameters": target.parameters}
                except Exception as e:
                    raise InventoryError(f"{target.name}: {e}")

        else:
            # load targets parallel
            nodes = mp.Manager().dict()

            mp.set_start_method("spawn", True)  # platform independent
            with mp.Pool() as pool:
                r = pool.map_async(
                    self.inventory_worker, [(self, target, nodes) for target in selected_targets]
                )
                r.wait()

        # using nodes for reclass legacy code
        return {"nodes": nodes}

    @staticmethod
    def inventory_worker(zipped_args):
        try:
            start = time()
            self, target, nodes = zipped_args
            register_resolvers(self.inventory_path)
            self.load_target(target)
            nodes[target.name] = {"parameters": target.parameters}
            logger.info(f"Rendered {target.name} ({round(time()-start, 2)})")
        except Exception as e:
            logger.error(f"{target.name}: e")

    def lint(self):
        temp = tempfile.mktemp()

        self.inventory()
        with open(temp, "r") as f:
            for line in f.readlines():
                logger.info(line)

    def searchvar(self):
        raise NotImplementedError()

    @staticmethod
    def migrate(input: str):
        if os.path.exists(input):
            if os.path.isdir(input):
                OmegaConfBackend.migrate_dir(input)
            elif os.path.isfile(input):
                OmegaConfBackend.migrate_file(input)
        else:
            return OmegaConfBackend.migrate_str(input)

    @staticmethod
    def migrate_dir(path: str):
        """migrates all .yml/.yaml files in the given path to omegaconfs syntax"""

        # TODO: write migrations to temp dir and copy only if suceeded

        for root, subdirs, files in os.walk(path):
            for file in files:
                file = os.path.join(root, file)
                name, ext = os.path.splitext(file)

                if ext not in (".yml", ".yaml"):
                    continue

                logger.debug(f"Migrating file '{file}'")

                try:
                    OmegaConfBackend.migrate_file(file)
                except Exception as e:
                    InventoryError(f"{file}: error with migration: {e}")

    @staticmethod
    def migrate_file(file: str):
        with open(file, "r") as fp:
            content = fp.read()

        updated_content = OmegaConfBackend.migrate_str(content)

        with open(file, "w") as fp:
            fp.write(updated_content)

    @staticmethod
    def migrate_str(content: str):

        # TODO: dont migrate custom resolvers
        # TODO: migrate interpolations with '.' in the keyname

        # search for interpolation pattern
        updated_content = regex.sub(
            r"(?<!\\)\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
            lambda match: "${" + match.group(1)
            # .replace(".", ",") # support interpolations with '.' in keyname
            .replace(":", ".",).replace(  # migrate path delimiter
                "_reclass_", "_meta_"
            )
            + "}",  # migrate meta data
            content,
        )

        # replace escaped tags with specific resolver
        excluded_chars = "!"
        invalid = any(c in updated_content for c in excluded_chars)
        updated_content = regex.sub(
            r"\\\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
            lambda match: ("${escape:" if not invalid else "\\\\\\${") + match.group(1) + "}",
            updated_content,
        )

        return updated_content

    # ----------
    # private
    # ----------
    def get_selected_targets(self):

        selected_targets = []

        # loop through targets searchpath and load all targets
        for root, dirs, files in os.walk(self.targets_searchpath):
            for target_file in files:

                # split file extension and check if yml/yaml
                target_path = os.path.join(root, target_file)
                target_name, ext = os.path.splitext(target_file)
                if ext not in (".yml", ".yaml"):
                    logger.debug(f"{target_file}: targets have to be .yml or .yaml files.")
                    continue

                # skip targets if they are not specified with -t flag
                if self.targets and target_name not in self.targets:
                    continue

                # initialize target
                target = InventoryTarget(target_name, target_path)
                selected_targets.append(target)

        return selected_targets

    def load_target(self, target: InventoryTarget):
        """
        load only one target with all its classes
        """

        # load the target parameters
        target.classes, target.parameters = self.load_config(target.path)

        # load classes for targets
        for class_name in target.classes:

            # search in cache, otherwise load class
            if class_name in self.classes_cache.keys():
                inv_class = self.classes_cache[class_name]
            else:
                inv_class = self.load_class(target, class_name)
                self.classes_cache[class_name] = inv_class

            if not inv_class:
                # TODO: display warning
                continue

            params = deepcopy(inv_class.parameters)
            target._merge(params)
            target.classes += inv_class.dependents

        if not target.parameters:
            # TODO: improve error msg
            raise InventoryError("empty target")

        # resolve interpolations
        target.add_metadata()
        target._resolve()

        # obtain target name to insert in inv dict
        vars_target_name = target.parameters.get("kapitan", {}).get("vars", {}).get("target")
        if not vars_target_name:
            # TODO: add hint to kapitan.vars.target
            logger.warning(f"Could not resolve target name on target {target.name}")

    def load_class(self, target: InventoryTarget, class_name: str):

        # resolve class path (has to be absolute)
        class_path = os.path.join(self.classes_searchpath, *class_name.split("."))
        if class_path in target.classes_redundancy_check:
            return None

        # target.classes_redundancy_check.add(class_path)

        # check if file exists
        if os.path.isfile(class_path + ".yml"):
            class_path += ".yml"
        elif os.path.isdir(class_path):
            # search for init file
            init_path = os.path.join(self.classes_searchpath, *class_name.split("."), "init") + ".yml"
            if os.path.isfile(init_path):
                class_path = init_path
        elif self.ignore_class_notfound:
            logger.debug(f"Could not find {class_path}")
            return None
        else:
            raise InventoryError(f"Class {class_name} not found.")

        # load classes recursively
        classes, parameters = self.load_config(class_path)

        # initialize inventory class
        inv_class = InventoryClass(class_path)
        inv_class.parameters = parameters
        # resolve relative class names for new classes
        for c in classes:
            if c.startswith("."):
                c = ".".join(class_name.split(".")[0:-1]) + c
            inv_class.dependents.append(c)

        return inv_class

    def load_config(self, path: str):
        with open(path, "r") as f:
            f.seek(0)
            config = yaml.load(f, yaml.SafeLoader)
        classes = OmegaConf.create(config.get("classes", []))
        parameters = OmegaConf.create(config.get("parameters", {}))
        return classes, parameters
