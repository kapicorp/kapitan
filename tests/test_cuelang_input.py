"""Tests for CueLang input type."""

import os
import shutil
import tempfile
import unittest

import yaml

from kapitan.inputs.cuelang import Cuelang
from kapitan.inventory.model.input_types import KapitanInputTypeCuelangConfig


class CuelangInputTest(unittest.TestCase):
    """Test cases for Cuelang input type."""

    def setUp(self):
        """Set up the test environment."""
        self.compile_path = tempfile.mkdtemp()
        self.search_paths = []
        self.ref_controller = None
        self.target_name = "test_target"
        self.args = type("Args", (), {"cue_path": "cue"})()
        self.cuelang = Cuelang(
            compile_path=self.compile_path,
            search_paths=self.search_paths,
            ref_controller=self.ref_controller,
            target_name=self.target_name,
            args=self.args,
        )

    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.compile_path, ignore_errors=True)

    def test_compile_file(self):
        """Compile a CUE-Lang template."""
        temp_dir = tempfile.mkdtemp()

        try:
            shutil.copytree("tests/test_cue/module1", temp_dir, dirs_exist_ok=True)

            config = KapitanInputTypeCuelangConfig(
                input_paths=[temp_dir],
                output_path=self.compile_path,
                input_fill_path="input:",
                input={
                    "numerator": 10,
                    "denominator": 2,
                },
                output_yield_path="output",
            )

            cue_input = Cuelang(
                compile_path=self.compile_path,
                search_paths=self.search_paths,
                ref_controller=self.ref_controller,
                target_name=self.target_name,
                args=self.args,
            )

            cue_input.compile_file(config, temp_dir, self.compile_path)

            output_file = os.path.join(self.compile_path, "output.yaml")
            self.assertTrue(os.path.exists(output_file), "Output file was not created.")

            with open(output_file, "r") as f:
                output = yaml.safe_load(f)
                self.assertEqual(output, {"result": 5}, "Output does not match expected result.")
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
