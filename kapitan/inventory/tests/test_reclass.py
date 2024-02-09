import os
import shutil
import tempfile
import unittest

from kapitan.inventory import ReclassInventory
from kapitan.inventory.inventory import InventoryError


class ReclassInventoryTest(unittest.TestCase):

    def test_compose_target_name(self):

        inventory_path = "examples/kubernetes/inventory"
        example_target_names = [os.path.splitext(f)[0] for f in os.listdir(os.path.join(inventory_path, "targets"))]

        temp_inventory_dir = tempfile.mkdtemp()
        shutil.copytree(inventory_path, temp_inventory_dir, dirs_exist_ok=True)

        # ensure normal rendering works
        compose_target_name = True
        inv = ReclassInventory(temp_inventory_dir, compose_target_name)
        found_targets = inv.search_targets()
        self.assertEqual(example_target_names, list(found_targets.keys()))

        # create compose_target_name setup
        targets_path = os.path.join(inventory_path, "targets")
        shutil.copytree(targets_path, os.path.join(temp_inventory_dir, "targets", "env1"))
        shutil.copytree(targets_path, os.path.join(temp_inventory_dir, "targets", "env2"))

        composed_target_names = []
        for name in example_target_names:
            composed_target_names.extend([name, f"env1.{name}", f"env2.{name}"])

        # ensure inventory detects name collision
        compose_target_name = False
        inv = ReclassInventory(temp_inventory_dir, compose_target_name)
        with self.assertRaises(InventoryError):
            inv.search_targets()

        # ensure compose_target_name works as intended
        compose_target_name = True
        inv = ReclassInventory(temp_inventory_dir, compose_target_name)
        found_targets = inv.search_targets()

        self.assertEqual(set(composed_target_names), set(found_targets.keys()))

        shutil.rmtree(temp_inventory_dir)


if __name__ == '__main__':
    unittest.main()
