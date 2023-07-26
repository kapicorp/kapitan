#!/usr/bin/env python

"""
Copyright 2023 neXenio
"""

import logging
import os
from abc import ABC, abstractmethod

import reclass
import reclass.core
import regex
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan.errors import InventoryError
from kapitan.omegaconf_inv import inventory_omegaconf

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


logger = logging.getLogger(__name__)


class InventoryBackend(ABC):
    inventory_path: str
    ignore_class_notfound: bool
    compose_node_name: bool
    targets: list

    def __init__(self, inventory_path, ignore_class_notfound=False, compose_node_name=False, targets=[]):
        self.inventory_path = inventory_path
        self.ignore_class_notfound = ignore_class_notfound
        self.compose_node_name = compose_node_name
        self.targets = targets

    @abstractmethod
    def inventory(self) -> dict:
        ...

    @abstractmethod
    def searchvar(self):
        ...

    @abstractmethod
    def lint(self):
        ...

    @staticmethod
    def output(self):
        ...

    @abstractmethod
    def migrate(self):
        ...


class OmegaConfBackend(InventoryBackend):
    def __init__(self, *args):
        logger.debug("Using omegaconf as inventory backend")
        logger.warning("NOTE: OmegaConf inventory is currently in experimental mode.")
        super().__init__(*args)

    def inventory(self):
        return inventory_omegaconf(
            self.inventory_path, self.ignore_class_notfound, self.targets, self.compose_node_name
        )

    def lint(self):
        raise NotImplementedError()

    def searchvar(self):
        raise NotImplementedError()

    def migrate(self):
        """migrates all .yml/.yaml files in the given path to omegaconfs syntax"""

        for root, subdirs, files in os.walk(self.inventory_path):
            for file in files:
                file = os.path.join(root, file)
                name, ext = os.path.splitext(file)

                if ext not in (".yml", ".yaml"):
                    continue

                try:
                    with open(file, "r") as fp:
                        content = fp.read()

                    # replace colons in tags
                    updated_content = regex.sub(
                        r"(?<!\\)\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
                        lambda match: "${"
                        + match.group(1)
                        .replace(":", ".")
                        .replace("_reclass_", "_reclass_")  # change _reclass_ to _meta_ in the future
                        + "}",
                        content,
                    )

                    # replace escaped tags with specific resolver
                    excluded_chars = "!"
                    invalid = any(c in updated_content for c in excluded_chars)
                    updated_content = regex.sub(
                        r"\\\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
                        lambda match: ("${tag:" if not invalid else "\\\\\\${") + match.group(1) + "}",
                        updated_content,
                    )

                    with open(file, "w") as fp:
                        fp.write(updated_content)
                except Exception as e:
                    InventoryError(f"{file}: error with migration: {e}")


class ReclassBackend(InventoryBackend):
    def __init__(self, *args):
        logger.debug("Using reclass as inventory backend")
        super().__init__(*args)

    def inventory(self):
        """
        Runs a reclass inventory in inventory_path
        (same output as running ./reclass.py -b inv_base_uri/ --inventory)
        Will attempt to read reclass config from 'reclass-config.yml' otherwise
        it will failback to the default config.
        Returns a reclass style dictionary

        Does not throw errors if a class is not found while --fetch flag is enabled
        """
        # set default values initially
        reclass_config = {
            "storage_type": "yaml_fs",
            "inventory_base_uri": self.inventory_path,
            "nodes_uri": "targets",
            "classes_uri": "classes",
            "compose_node_name": False,
            "allow_none_override": True,
            "ignore_class_notfound": self.ignore_class_notfound,  # false by default
        }

        # get reclass config from file 'inventory/reclass-config.yml'
        cfg_file = os.path.join(self.inventory_path, "reclass-config.yml")
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r") as fp:
                config = yaml.load(fp.read(), Loader=YamlLoader)
                logger.debug("Using reclass inventory config at: {}".format(cfg_file))
            if config:
                # set attributes, take default values if not present
                for key, value in config.items():
                    reclass_config[key] = value
            else:
                logger.debug(
                    "{}: Empty config file. Using reclass inventory config defaults".format(cfg_file)
                )
        else:
            logger.debug("Inventory reclass: No config file found. Using reclass inventory config defaults")

        # normalise relative nodes_uri and classes_uri paths
        for uri in ("nodes_uri", "classes_uri"):
            reclass_config[uri] = os.path.normpath(os.path.join(self.inventory_path, reclass_config[uri]))

        try:
            storage = reclass.get_storage(
                reclass_config["storage_type"],
                reclass_config["nodes_uri"],
                reclass_config["classes_uri"],
                reclass_config["compose_node_name"],
            )
            class_mappings = reclass_config.get("class_mappings")  # this defaults to None (disabled)
            _reclass = reclass.core.Core(storage, class_mappings, reclass.settings.Settings(reclass_config))

            return _reclass.inventory()
        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error("Inventory reclass error: %s", e.message)
            raise InventoryError(e.message)

    def lint(self):
        raise NotImplementedError()

    def searchvar(self):
        raise NotImplementedError()

    def migrate(self):
        raise NotImplementedError()
