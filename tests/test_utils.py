#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import tempfile
from typing import List
import unittest

from kapitan.utils import copy_tree


class CopytreeTest(unittest.TestCase):
    def _create_directory_structure(self, root: Path, structure: List[str]):
        for sub_path in structure:
            full_path = root / sub_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch(exist_ok=True)

    def setUp(self):
        self.template_structure = [
            "components/my_component/my_component.jsonnet",
            "components/other_component/__init__.py",
            "inventory/classes/common.yml",
            "inventory/classes/my_component.yml",
            "templates/docs/my_readme.md",
            "templates/scripts/my_script.sh",
        ]
        self.template_directory = tempfile.TemporaryDirectory()
        self.template_directory_path = Path(self.template_directory.name)

        self._create_directory_structure(self.template_directory_path, self.template_structure)

    def tearDown(self):
        self.template_directory.cleanup()

    def test_empty_dir(self):
        """Validates that all template files were copied to the correct directory and
        the right list of copied files was returned."""
        with tempfile.TemporaryDirectory() as destination_directory:
            template_files = [destination_directory + "/" + f for f in self.template_structure]

            copied_paths = copy_tree(
                source=self.template_directory_path,
                destination=Path(destination_directory),
                dirs_exist_ok=True,
            )
            # We only care about files as they will have full patch anyway.
            copied_files = [p for p in copied_paths if Path(p).is_file()]

            self.assertSequenceEqual(sorted(copied_files), sorted(template_files))
            self.assertTrue([Path(f).exists() for f in template_files])

    def test_non_empty_dir(self):
        """Makes sure that existing directories and files are untouched."""
        with tempfile.TemporaryDirectory() as destination_directory:
            extra_files = [
                "file_that_existed_before.txt",
                "this_existed_before/file.txt",
            ]
            self._create_directory_structure(Path(destination_directory), extra_files)
            template_files = [destination_directory + "/" + f for f in self.template_structure]

            copied_paths = copy_tree(
                source=self.template_directory_path,
                destination=Path(destination_directory),
                dirs_exist_ok=True,
            )
            # We only care about files as they will have full patch anyway.
            copied_files = [p for p in copied_paths if Path(p).is_file()]

            self.assertSequenceEqual(sorted(copied_files), sorted(template_files))
            self.assertTrue([Path(f).exists() for f in template_files])
            self.assertTrue([Path(destination_directory + "/" + f).exists() for f in extra_files])


if __name__ == "__main__":
    unittest.main()
