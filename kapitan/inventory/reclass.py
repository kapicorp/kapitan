#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import reclass
import reclass.core
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan.errors import InventoryError

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader


logger = logging.getLogger(__name__)


class ReclassBackend:
    inventory_path: str
    targets_searchpath: str
    classes_searchpath: str
    ignore_class_notfound: bool

    def __init__(self, inventory_path: str, ignore_class_notfound: bool):
        logger.debug("Using reclass as inventory backend")
        self.inventory_path = inventory_path
        self.ignore_class_notfound = ignore_class_notfound

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
                    "{}: Empty config file. Using reclass inventory config defaults".format(
                        cfg_file
                    )
                )
        else:
            logger.debug(
                "Inventory reclass: No config file found. Using reclass inventory config defaults"
            )

        # normalise relative nodes_uri and classes_uri paths
        for uri in ("nodes_uri", "classes_uri"):
            reclass_config[uri] = os.path.normpath(
                os.path.join(self.inventory_path, reclass_config[uri])
            )

        try:
            storage = reclass.get_storage(
                reclass_config["storage_type"],
                reclass_config["nodes_uri"],
                reclass_config["classes_uri"],
                reclass_config["compose_node_name"],
            )
            class_mappings = reclass_config.get(
                "class_mappings"
            )  # this defaults to None (disabled)
            _reclass = reclass.core.Core(
                storage, class_mappings, reclass.settings.Settings(reclass_config)
            )

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
