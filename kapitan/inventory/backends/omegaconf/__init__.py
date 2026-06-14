#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import multiprocessing as mp
import os
import time
from collections.abc import Mapping
from functools import singledispatch

import yaml
from cachetools import LRUCache, cached
from kadet import Dict

from kapitan.errors import InventoryError
from kapitan.inventory import Inventory, InventoryTarget
from kapitan.inventory.model import KapitanInventoryMetadata, KapitanInventoryParameters
from kapitan.utils import available_cpu_count
from omegaconf import ListMergeMode, OmegaConf

from .migrate import migrate
from .resolvers import register_resolvers


logger = logging.getLogger(__name__)


@singledispatch
def keys_to_strings(ob):
    return ob


class OmegaConfRenderingError(InventoryError):
    pass


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

        self.parameters = KapitanInventoryParameters(
            _kapitan_=kapitan_metadata, _reclass_=kapitan_metadata
        )


class OmegaConfInventory(Inventory):
    _instance = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, target_class=OmegaConfTarget)

    def render_targets(
        self,
        targets: list[OmegaConfTarget] = None,
        ignore_class_not_found: bool = False,
    ) -> None:
        if not self.initialised:
            if targets is None:
                target_values = []
            elif isinstance(targets, Mapping):
                target_values = list(targets.values())
            else:
                target_values = list(targets)

            if not target_values:
                return

            num_workers = max(1, min(len(target_values), available_cpu_count()))
            chunksize = max(1, len(target_values) // (num_workers * 2))

            try:
                with mp.Pool(
                    num_workers,
                    initializer=_set_inventory_worker_instance,
                    initargs=(self,),
                ) as pool:
                    rendered_targets = list(
                        pool.imap_unordered(
                            OmegaConfInventory.inventory_worker,
                            target_values,
                            chunksize=chunksize,
                        )
                    )
            except Exception as e:
                raise OmegaConfRenderingError(
                    "Error while loading the OmegaConf inventory"
                ) from e

            rendered_by_name = {target.name: target for target in rendered_targets}
            for target in target_values:
                self.targets[target.name] = rendered_by_name[target.name]

    @staticmethod
    def inventory_worker(target):
        self = OmegaConfInventory._instance
        if self is None:
            raise OmegaConfRenderingError("OmegaConf inventory worker not initialised")

        try:
            register_resolvers(self.inventory_path)
            self.load_target(target)

        except Exception as e:
            import traceback

            logger.error(f"{target.name}: could not render due to error {e}")
            logger.debug(f"{target.name}: traceback: {traceback.format_exc()}")
            raise
        else:
            return target

    @cached(cache=LRUCache(maxsize=1024))
    def resolve_class_file_path(
        self,
        class_name: str,
        class_parent_dir: str = None,
        class_parent_name: str = None,
    ):
        class_file = None

        # Finds relative paths based on the parent directory
        if class_name.startswith(".") and class_parent_dir:
            class_path_base = os.path.join(self.classes_path, class_parent_dir)
        else:
            class_path_base = self.classes_path

        # Now try to find the class file
        for ext in (".yml", ".yaml"):
            cases = [
                # case components.kapicorp is absolute and a directory, look for components/kapicorp/init.yml
                # case .components.kapicorp is relative and a directory, look for <class_parent_dir>/components/kapicorp/init.yml
                os.path.join(class_path_base, *class_name.split("."), "init" + ext),
                # case components.kapicorp is absolute and a file, look for components/kapicorp.yml
                # case components.kapicorp is relative and a file, look for <class_parent_dir>/components/kapicorp.yml
                os.path.join(class_path_base, *class_name.split(".")) + ext,
                # Reclass compatibility mode
                # case .components.kapicorp  points to <class_parent_dir>/kapicorp.yml
                os.path.join(class_path_base, *class_name.split(".")[2:]) + ext,
                # case components.kapicorp points to components/kapicorp/init.yml
                os.path.join(class_path_base, *class_name.split(".")[2:], "init" + ext),
            ]

            for case in cases:
                if os.path.isfile(case):
                    class_file = case
                    return class_file

        logger.error(f"class file not found for class {class_name}, tried {cases}")
        return None

    @cached(cache=LRUCache(maxsize=1024))
    def load_file(self, filename):
        with open(filename) as f:
            return yaml.safe_load(f)

    @cached(cache=LRUCache(maxsize=1024))
    def get_class_config(self, filename):
        parameters, classes, applications, exports = self.load_parameters_from_file(
            filename
        )
        if parameters:
            parameters = OmegaConf.to_container(parameters, resolve=False)
        else:
            parameters = {}
        return parameters, classes, applications, exports

    def load_parameters_from_file(self, filename, parameters=None) -> Dict:
        if parameters is None:
            parameters = {}
        parameters = OmegaConf.create(parameters)
        applications = []
        classes = []
        exports = Dict()

        content = self.load_file(filename)

        # Handle empty files (yaml.safe_load returns None for empty files)
        if content is None:
            content = {}

        # Handle None values for classes/parameters/applications/exports
        # (e.g., "classes:" with nothing after it returns None, not [])
        _classes = content.get("classes") or []
        _parameters = keys_to_strings(content.get("parameters") or {})
        _applications = content.get("applications") or []
        _exports = content.get("exports") or {}

        # first processes all classes
        for class_name in _classes:
            class_parent_dir = os.path.dirname(
                filename.removeprefix(self.classes_path).removeprefix("/")
            )
            class_parent_name = os.path.basename(filename)
            class_file = self.resolve_class_file_path(
                class_name,
                class_parent_dir=class_parent_dir,
                class_parent_name=class_parent_name,
            )
            if not class_file:
                if self.ignore_class_not_found:
                    continue
                raise InventoryError(f"Class {class_name} not found")
            p, c, a, e = self.get_class_config(class_file)
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
        parameters = OmegaConf.create(
            keys_to_strings(target.parameters.model_dump(by_alias=True))
        )
        p, c, a, e = self.load_parameters_from_file(
            full_target_path, parameters=parameters
        )
        load_parameters = time.perf_counter() - start

        # First resolve pass - resolves all interpolations, escaped ones become unescaped
        OmegaConf.resolve(p)
        # Second resolve pass - resolves the previously escaped interpolations
        OmegaConf.resolve(p)
        # Convert to container with resolve=True to ensure all interpolations are resolved
        resolved_params = OmegaConf.to_container(p, resolve=True)

        # Process literal markers (from escape resolver) back to actual ${...} syntax
        from .resolvers import process_literals

        resolved_params = process_literals(resolved_params)

        # Validate and construct KapitanInventoryParameters from the resolved dict
        target.parameters = KapitanInventoryParameters.model_validate(resolved_params)

        to_container = time.perf_counter() - load_parameters
        target.classes = c
        target.applications = a
        target.exports = e
        finish_loading = time.perf_counter() - start
        logger.debug(
            f"{target.name}: Config loaded in {load_parameters:.2f}s, resolved in {to_container:.2f}s. Total {finish_loading:.2f}s"
        )

    def migrate(self):
        migrate(self.original_inventory_path)

    def resolve_targets(self, targets: list[OmegaConfTarget] = None) -> None:
        if targets is None:
            target_values = self.targets.values()
        elif isinstance(targets, Mapping):
            target_values = targets.values()
        else:
            target_values = targets

        register_resolvers(self.inventory_path)
        for target in target_values:
            self.load_target(target)


def _set_inventory_worker_instance(inventory):
    OmegaConfInventory._instance = inventory
