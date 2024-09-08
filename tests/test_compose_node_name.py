import os
import shutil
import tempfile
import unittest

from kapitan.inventory import InventoryBackends, get_inventory_backend
from kapitan.inventory.inventory import InventoryError


class ReclassComposeNodeNameTest(unittest.TestCase):
    def setUp(self):
        self.inventory = get_inventory_backend(InventoryBackends.RECLASS)

    def test_compose_target_name(self):
        inventory_path = "examples/kubernetes/inventory"
        targets_path = os.path.join(inventory_path, "targets")
        example_target_names = []

        for root, dirs, files in os.walk(targets_path):
            for file in files:
                # split file extension and check if yml/yaml
                path = os.path.relpath(os.path.join(root, file), targets_path)
                name = os.path.splitext(path)[0].replace(os.sep, ".")
                example_target_names.append(name)

        temp_inventory_dir = tempfile.mkdtemp()
        shutil.copytree(inventory_path, temp_inventory_dir, dirs_exist_ok=True)

        # ensure normal rendering works
        compose_target_name = True
        inv = self.inventory(inventory_path=temp_inventory_dir, compose_target_name=compose_target_name)
        found_targets = inv.targets
        self.assertEqual(sorted(example_target_names), sorted(list(found_targets.keys())))
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
        with self.assertRaises(InventoryError):
            inv = self.inventory(inventory_path=temp_inventory_dir, compose_target_name=compose_target_name)

        # ensure compose_target_name works as intended
        compose_target_name = True
        inv = self.inventory(inventory_path=temp_inventory_dir, compose_target_name=compose_target_name)
        found_targets = inv.targets

        self.assertEqual(set(composed_target_names), set(found_targets.keys()))
        # ensure that actual rendering finds the same nodes as `search_targets()`
        for t in composed_target_names:
            nodeinfo = inv.get_target(t)
            self.assertTrue(nodeinfo is not None)

        shutil.rmtree(temp_inventory_dir)


class ReclassRsComposeNodeNameTest(ReclassComposeNodeNameTest):
    def setUp(self):
        self.inventory = get_inventory_backend(InventoryBackends.RECLASS_RS)
