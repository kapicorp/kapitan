#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import logging
import os
import sys
import unittest

from omegaconf import OmegaConf

from kapitan.inventory import get_inventory_backend
from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers


logger = logging.getLogger(__name__)

TEST_PWD = os.getcwd()
TEST_OMEGACONF_INVENTORY = os.path.join(TEST_PWD, "tests/test_resources copy/inventory")
TEST_OMEGACONF_SYSTEM = os.path.join(TEST_PWD, "tests/test_resources copy/system")


def register_custom_resolvers():
    """Register custom resolvers from the test resources"""
    # Add the system path to import custom resolvers
    resolvers_path = os.path.join(TEST_OMEGACONF_SYSTEM, "omegaconf/resolvers")
    if resolvers_path not in sys.path:
        sys.path.insert(0, resolvers_path)

    from resolvers import pass_resolvers

    custom_resolvers = pass_resolvers()
    for name, func in custom_resolvers.items():
        if not OmegaConf.has_resolver(name):
            OmegaConf.register_new_resolver(name, func)


class InventoryTestOmegaConf(unittest.TestCase):
    def setUp(self) -> None:
        register_resolvers()
        register_custom_resolvers()
        inventory_backend = get_inventory_backend("omegaconf")
        self.inventory_path = TEST_OMEGACONF_INVENTORY
        self.extraArgv = ["--inventory-backend=omegaconf"]
        self.inventory_backend = inventory_backend(
            inventory_path=TEST_OMEGACONF_INVENTORY, initialise=False
        )

    def test_load_and_resolve_single_target(self):
        target_name = "oc-testxxx"
        target_kapitan_metadata = dict(
            {
                "_kapitan_": {
                    "name": {
                        "short": "oc-testxxx",
                        "full": "oc-testxxx",
                        "path": "oc-testxxx",
                        "parts": ["oc-testxxx"],
                    }
                }
            }
        )

        # Load inventory but does not initialises targets
        inventory = self.inventory_backend

        # Manually create a new Target
        target = inventory.target_class(name=target_name, path="oc-testxxx.yml")
        logger.error(f"Loading target {target_name} from {target.path}")
        logger.error(target.parameters)
        # Adds target to Inventory
        inventory.targets.update({target_name: target})

        # Loads the target using the inventory
        inventory.load_target(target)

        # Check if the target is loaded correctly
        metadata = target.parameters.model_dump(by_alias=True)["_kapitan_"]
        self.assertDictEqual(target_kapitan_metadata["_kapitan_"], metadata)
        self.assertEqual(metadata["name"]["short"], "oc-testxxx")
        self.assertEqual(target.parameters.target_name, "oc-testxxx")
