#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
import time
from functools import singledispatch

import yaml
from cachetools import LRUCache, cached
from kadet import Dict
from omegaconf import ListMergeMode, OmegaConf

from kapitan.inventory.model import KapitanInventoryMetadata, KapitanInventoryParameters

from ..inventory import Inventory, InventoryError, InventoryTarget
from .migrate import migrate
from .resolvers import register_resolvers

logger = logging.getLogger(__name__)


@singledispatch
def keys_to_strings(ob):
    return ob


@keys_to_strings.register
def _handle_dict(ob: dict):
    return {str(k): keys_to_strings(v) for k, v in ob.items()}


@keys_to_strings.register
def _handle_list(ob: list):
    return [keys_to_strings(v) for v in ob]


class OmegaConfTarget(InventoryTarget):
    resolved: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__add_metadata()

    def __add_metadata(self):
        name_metadata = {
            "short": self.name.split(".")[-1],
            "full": self.name,
            "path": os.path.splitext(self.path)[0],
            "parts": self.name.split("."),
        }
        kapitan_metadata = KapitanInventoryMetadata(name=name_metadata)

        self.parameters = KapitanInventoryParameters(_kapitan_=kapitan_metadata, _reclass_=kapitan_metadata)


class OmegaConfInventory(Inventory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, target_class=OmegaConfTarget)

    def render_targets(
        self, targets: list[OmegaConfTarget] = None, ignore_class_not_found: bool = False
    ) -> None:
        if not self.initialised:
            manager = mp.Manager()
            shared_targets = manager.dict()
            with mp.Pool(min(len(targets), os.cpu_count())) as pool:
                r = pool.map_async(
                    self.inventory_worker, [(self, target, shared_targets) for target in targets.values()]
                )
                r.wait()

            for target in shared_targets.values():
                self.targets[target.name] = target

    @staticmethod
    def inventory_worker(zipped_args):
        self, target, shared_targets = zipped_args
        try:
            register_resolvers()
            self.load_target(target)
            shared_targets[target.name] = target

        except Exception as e:
            logger.error(f"{target.name}: could not render due to error {e}")
            raise

    @cached(cache=LRUCache(maxsize=1024))
    def resolve_class_file_path(
        self, class_name: str, class_parent_dir: str = None, class_parent_name: str = None
    ):
        class_file = None

        # Finds relative paths based on the parent directory
        if class_name.startswith(".") and class_parent_dir:
            class_path_base = os.path.join(self.classes_path, class_parent_dir)
        else:
            class_path_base = self.classes_path

        # Now try to find the class file
        extension = ".yml"

        cases = [
            # case components.kapicorp is absolute and a directory, look for components/kapicorp/init.yml
            # case .components.kapicorp is relative and a directory, look for <class_parent_dir>/components/kapicorp/init.yml
            os.path.join(class_path_base, *class_name.split("."), "init" + extension),
            # case components.kapicorp is absolute and a file, look for components/kapicorp.yml
            # case components.kapicorp is relative and a file, look for <class_parent_dir>/components/kapicorp.yml
            os.path.join(class_path_base, *class_name.split(".")) + extension,
            # Reclass compatibility mode
            # case .components.kapicorp  points to <class_parent_dir>/kapicorp.yml
            os.path.join(class_path_base, *class_name.split(".")[2:]) + extension,
            # case components.kapicorp points to components/kapicorp/init.yml
            os.path.join(class_path_base, *class_name.split(".")[2:], "init" + extension),
        ]

        for case in cases:
            if os.path.isfile(case):
                class_file = case
                return class_file

        logger.error(f"class file not found for class {class_name}, tried {cases}")
        return None

    @cached(cache=LRUCache(maxsize=1024))
    def load_file(self, filename):
        with open(filename, "r") as f:
            return yaml.safe_load(f)

    def load_parameters_from_file(self, filename, parameters={}) -> Dict:
        parameters = OmegaConf.create(parameters)
        applications = []
        classes = []
        exports = Dict()

        content = self.load_file(filename)

        _classes = content.get("classes", [])
        _parameters = keys_to_strings(content.get("parameters", {}))
        _applications = content.get("applications", [])
        _exports = content.get("exports", {})

        # first processes all classes
        for class_name in _classes:

            class_parent_dir = os.path.dirname(filename.removeprefix(self.classes_path).removeprefix("/"))
            class_parent_name = os.path.basename(filename)
            class_file = self.resolve_class_file_path(
                class_name, class_parent_dir=class_parent_dir, class_parent_name=class_parent_name
            )
            if not class_file:
                if self.ignore_class_not_found:
                    continue
                raise InventoryError(f"Class {class_name} not found")
            p, c, a, e = self.load_parameters_from_file(class_file)
            if p:
                parameters = OmegaConf.unsafe_merge(
                    parameters, p, list_merge_mode=ListMergeMode.EXTEND_UNIQUE
                )
            classes.extend(c)
            classes.append(class_name)
            applications.extend(a)
            exports.merge_update(e, box_merge_lists="unique")

        # finally merges the parameters from the current file
        if _parameters:
            parameters = OmegaConf.unsafe_merge(
                parameters, _parameters, list_merge_mode=ListMergeMode.EXTEND_UNIQUE
            )

        exports.merge_update(_exports, box_merge_lists="unique")
        applications.extend(_applications)
        return parameters, classes, applications, exports

    def load_target(self, target: OmegaConfTarget):
        full_target_path = os.path.join(self.targets_path, target.path)

        start = time.perf_counter()
        parameters = OmegaConf.create(keys_to_strings(target.parameters.model_dump(by_alias=True)))
        p, c, a, e = self.load_parameters_from_file(full_target_path, parameters=parameters)
        load_parameters = time.perf_counter() - start
        target.parameters = OmegaConf.to_container(p, resolve=True)
        to_container = time.perf_counter() - load_parameters
        target.classes = c
        target.applications = a
        target.exports = e
        finish_loading = time.perf_counter() - start
        logger.debug(
            f"{target.name}: Config loaded in {load_parameters:.2f}s, resolved in {to_container:.2f}s. Total {finish_loading:.2f}s"
        )

    def migrate(self):
        migrate(self.inventory_path)

    def resolve_targets(self, targets: list[OmegaConfTarget] = None) -> None:
        if not targets:
            targets = self.targets.values()
        map(lambda target: target.resolve(), targets)
