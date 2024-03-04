import glob
import logging
import os
import shutil
import tempfile
import unittest

from kapitan.inventory import ReclassInventory
from kapitan.inventory import ReclassRsInventory
from kapitan.inventory.inventory import InventoryError
from kapitan import setup_logging


class ReclassComposeNodeNameTest(unittest.TestCase):
    def setUp(self):
        self.inventory = ReclassInventory

    def test_compose_target_name(self):
        inventory_path = "examples/kubernetes/inventory"
        example_target_names = [
            os.path.splitext(f)[0] for f in os.listdir(os.path.join(inventory_path, "targets"))
        ]

        temp_inventory_dir = tempfile.mkdtemp()
        shutil.copytree(inventory_path, temp_inventory_dir, dirs_exist_ok=True)

        # ensure normal rendering works
        compose_target_name = True
        inv = self.inventory(temp_inventory_dir, compose_target_name)
        found_targets = inv.search_targets()
        self.assertEqual(example_target_names, list(found_targets.keys()))
        # ensure that actual rendering finds the same nodes as `search_targets()`
        for t in example_target_names:
            nodeinfo = inv.get_target(t)
            self.assertTrue(nodeinfo is not None)

        # create compose_target_name setup
        targets_path = os.path.join(inventory_path, "targets")
        shutil.copytree(targets_path, os.path.join(temp_inventory_dir, "targets", "env1"))
        shutil.copytree(targets_path, os.path.join(temp_inventory_dir, "targets", "env2"))

        composed_target_names = []
        for name in example_target_names:
            composed_target_names.extend([name, f"env1.{name}", f"env2.{name}"])

        # ensure inventory detects name collision
        compose_target_name = False
        inv = self.inventory(temp_inventory_dir, compose_target_name)
        with self.assertRaises(InventoryError):
            inv.search_targets()

        # ensure compose_target_name works as intended
        compose_target_name = True
        inv = self.inventory(temp_inventory_dir, compose_target_name)
        found_targets = inv.search_targets()

        self.assertEqual(set(composed_target_names), set(found_targets.keys()))
        # ensure that actual rendering finds the same nodes as `search_targets()`
        for t in composed_target_names:
            nodeinfo = inv.get_target(t)
            self.assertTrue(nodeinfo is not None)

        shutil.rmtree(temp_inventory_dir)


class ReclassRsComposeNodeNameTest(ReclassComposeNodeNameTest):
    def setUp(self):
        self.inventory = ReclassRsInventory
