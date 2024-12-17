#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"initialiser module tests"

import logging
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from kapitan.errors import KapitanError
from kapitan.initialiser import initialise_skeleton

logger = logging.getLogger(__name__)


class InitialiserTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.template_url = "https://github.com/kapicorp/kapitan-reference"
        self.checkout_ref = "master"

    def test_initialise_skeleton_success(self):
        """
        Verify that initialise_skeleton succeeds when target directory is empty
        """
        initialise_skeleton(self._create_args(self.tmpdir))

        # Assert that the directory is no longer empty (indicating successful initialisation)
        self.assertTrue(len(os.listdir(self.tmpdir)) > 0, "Target directory is still empty")

    @patch("kapitan.initialiser.run_copy")
    def test_initialise_skeleton_non_empty_dir(self, mocked_run_copy):
        """
        Verify that initialise_skeleton logs an error when target directory is not empty
        """
        # Create a dummy file in the temporary directory, simulating a non-empty directory
        dummy_file = os.path.join(self.tmpdir, "dummy.txt")
        with open(dummy_file, "w") as f:
            f.write("This is a dummy file")

        with self.assertRaises(KapitanError):
            initialise_skeleton(self._create_args(self.tmpdir))

            mocked_run_copy.assert_not_called()  # Make sure run_copy was not called

    def tearDown(self):
        # Clean up the temporary directory after each test
        shutil.rmtree(self.tmpdir)

    def _create_args(self, target_dir):
        """Helper function to create Namespace object for testing"""
        return type(
            "args",
            (object,),
            {
                "template_git_url": self.template_url,
                "checkout_ref": self.checkout_ref,
                "directory": target_dir,
            },
        )
