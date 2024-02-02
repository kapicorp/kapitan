#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
from copy import deepcopy
from time import time

import yaml
from omegaconf import ListMergeMode, OmegaConf

from kapitan import cached
from .migrate import migrate
from ..inventory import InventoryError, Inventory
from .resolvers import register_resolvers

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
            merged_parameters = OmegaConf.unsafe_merge(
                class_parameters,
                self.parameters,
                list_merge_mode=ListMergeMode.EXTEND,
            )

            self.parameters = merged_parameters

    def _resolve(self):
        escape_interpolation_strings = False
        OmegaConf.resolve(self.parameters, escape_interpolation_strings)

        # remove specified keys
        remove_location = "omegaconf.remove"
        removed_keys = OmegaConf.select(self.parameters, remove_location, default=[])
        for key in removed_keys:
            OmegaConf.update(self.parameters, key, {}, merge=False)

        # resolve second time and convert to object
        # add throw_on_missing = True when resolving second time (--> wait for to_object support)
        # reference: https://github.com/omry/omegaconf/pull/1113
        OmegaConf.resolve(self.parameters, escape_interpolation_strings)
        self.parameters = OmegaConf.to_container(self.parameters)

    def add_metadata(self):
        # append meta data (legacy: _reclass_)
        _meta_ = {
            "name": {
                "full": self.name,
                "parts": self.name.split("."),
                "path": self.name.replace(".", "/"),
                "short": self.name,
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


class OmegaConfInventory(Inventory):
    classes_cache: dict = {}

    # InventoryTarget.targets_path = self.targets_searchpath
    # InventoryClass.classes_path = self.classes_searchpath

    def inventory(self):
        register_resolvers(self.inventory_path)
        selected_targets = self.get_selected_targets()

        # FEAT: add flag for multiprocessing
        use_mp = True

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
            manager = mp.Manager()  # perf: bottleneck --> 90 % of the inventory time

            nodes = manager.dict()
            mp.set_start_method("spawn", True)  # platform independent
            with mp.Pool(len(selected_targets)) as pool:
                r = pool.map_async(
                    self.inventory_worker, [(self, target, nodes) for target in selected_targets]
                )
                r.wait()

        # using nodes for reclass legacy code
        nodes = dict(nodes)

        # using nodes for reclass legacy code
        return {"nodes": nodes}

    @staticmethod
    def inventory_worker(zipped_args):
        start = time()
        self, target, nodes = zipped_args

        try:
            register_resolvers(self.inventory_path)
            self.load_target(target)
            nodes[target.name] = {"parameters": target.parameters}
        except Exception as e:
            logger.error(f"{target.name}: {e}")
            return

        logger.info(f"Rendered {target.name} ({time()-start:.2f}s)")

    def migrate(self):
        migrate(self.inventory_path)

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
                if self.compose_node_name:
                    target.name = target.composed_name
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
            inv_class = self.load_class(target, class_name)
            if not inv_class:
                # either redundantly defined or not found (with ignore_not_found: true)
                continue

            params = deepcopy(inv_class.parameters)
            target._merge(params)
            target.classes += inv_class.dependents

        if not target.parameters:
            # improve error msg
            raise InventoryError("empty target")

        # resolve interpolations
        target.add_metadata()
        target._resolve()

        # obtain target name to insert in inv dict
        vars_target_name = target.parameters.get("kapitan", {}).get("vars", {}).get("target")
        if not vars_target_name:
            # add hint to kapitan.vars.target
            logger.warning(f"Could not resolve target name on target {target.name}")

    def load_class(self, target: InventoryTarget, class_name: str):
        # resolve class path (has to be absolute)
        class_path = os.path.join(self.classes_searchpath, *class_name.split("."))
        if class_path in target.classes_redundancy_check:
            logger.debug(f"{class_path}: class {class_name} is redundantly defined")
            return None
        target.classes_redundancy_check.add(class_path)

        # search in inventory classes cache, otherwise load class
        if class_name in self.classes_cache.keys():
            return self.classes_cache[class_name]

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

        if not classes and not parameters:
            return None

        # initialize inventory class
        inv_class = InventoryClass(class_path)
        inv_class.parameters = parameters
        # resolve relative class names for new classes
        for c in classes:
            if c.startswith("."):
                c = ".".join(class_name.split(".")[0:-1]) + c
            inv_class.dependents.append(c)

        # add class to cache
        self.classes_cache[class_name] = inv_class

        return inv_class

    def load_config(self, path: str):
        with open(path, "r") as f:
            f.seek(0)
            config = yaml.load(f, yaml.SafeLoader)

        if not config:
            logger.debug(f"{path}: file is empty")
            return [], {}
        classes = OmegaConf.create(config.get("classes", []))
        parameters = OmegaConf.create(config.get("parameters", {}))

        # add metadata to nodes
        filename = os.path.splitext(os.path.split(path)[1])[0]
        parameters._set_flag(["filename", "path"], [filename, path], recursive=True)

        return classes, parameters