#!/usr/bin/env python

"""
Copyright 2023 neXenio
"""

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import overload

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

    def __init__(self, inventory_path, ignore_class_notfound=False, compose_node_name=False, targets=[]):
        self.inventory_path = inventory_path
        self.ignore_class_notfound = ignore_class_notfound

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
    targets: list
    compose_node_name: bool
    logfile: str

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

        self.targets = targets
        self.compose_node_name = compose_node_name
        self.logfile = logfile

        super().__init__(inventory_path, ignore_class_notfound)

    def inventory(self):
        return inventory_omegaconf(
            self.inventory_path,
            self.ignore_class_notfound,
            self.targets,
            self.compose_node_name,
            self.logfile,
        )

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

        return updated_content


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
