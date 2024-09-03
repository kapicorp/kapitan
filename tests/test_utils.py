#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"utils tests"

import glob
import os
import shutil
import stat
import tempfile
import unittest

from kapitan.utils import SafeCopyError, copy_tree, directory_hash, force_copy_file

TEST_PWD = os.getcwd()
TEST_RESOURCES_PATH = os.path.join(os.getcwd(), "tests/test_resources")
TEST_DOCKER_PATH = os.path.join(os.getcwd(), "examples/docker/")
TEST_TERRAFORM_PATH = os.path.join(os.getcwd(), "examples/terraform/")
TEST_KUBERNETES_PATH = os.path.join(os.getcwd(), "examples/kubernetes/")


class CopyTreeTest(unittest.TestCase):
    "Test copy_tree function"

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_copy_dir(self):
        original = set(glob.iglob(f"{TEST_KUBERNETES_PATH}/*", recursive=True))
        copied = copy_tree(TEST_KUBERNETES_PATH, self.temp_dir)
        self.assertEqual(len(copied), len(original))

        original_hash = directory_hash(TEST_KUBERNETES_PATH)
        copied_hash = directory_hash(self.temp_dir)
        self.assertEqual(copied_hash, original_hash)

    def test_validate_copy_dir(self):
        with self.assertRaises(SafeCopyError):
            copy_tree("non_existent_dir", self.temp_dir)

        dst = os.path.join(self.temp_dir, "test")
        with open(dst, "w", encoding="utf-8") as f:
            f.write("Hello\n")
        with self.assertRaises(SafeCopyError):
            copy_tree(TEST_KUBERNETES_PATH, dst)

    def test_copy_dir_missing_dst(self):
        dst = os.path.join(self.temp_dir, "subdir")
        original = set(glob.iglob(f"{TEST_KUBERNETES_PATH}/*", recursive=True))
        copied = copy_tree(TEST_KUBERNETES_PATH, dst)
        self.assertEqual(len(copied), len(original))

        original_hash = directory_hash(TEST_KUBERNETES_PATH)
        copied_hash = directory_hash(dst)
        self.assertEqual(copied_hash, original_hash)

    def test_copy_dir_overwrite_readonly_file(self):
        src = os.path.join(self.temp_dir, "source")
        os.makedirs(src, exist_ok=True)
        f = os.path.join(src, "ro.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("Hello!\n")
        os.chmod(f, 0o444)

        dst = os.path.join(self.temp_dir, "dest")
        copied = copy_tree(src, dst)
        self.assertEqual(copied, [os.path.join(dst, "ro.txt")])
        self.assertEqual(stat.S_IMODE(os.stat(copied[0]).st_mode), 0o444)

        with self.assertRaises(shutil.Error):
            copy_tree(src, dst)

        copied2 = copy_tree(src, dst, clobber_files=True)
        self.assertEqual(copied2, [])
        self.assertEqual(stat.S_IMODE(os.stat(copied[0]).st_mode), 0o444)

    def test_force_copy_file(self):
        src = os.path.join(self.temp_dir, "test.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("Test\n")

        # Test that we don't delete `dst` if it's not a file
        dst1 = os.path.join(self.temp_dir, "path")
        os.makedirs(dst1, exist_ok=True)
        force_copy_file(src, dst1)
        self.assertTrue(os.path.isfile(os.path.join(dst1, "test.txt")))

        # Test that we can create file `dst` if it doesn't exist
        dst2 = os.path.join(self.temp_dir, "test2.txt")
        self.assertFalse(os.path.exists(dst2))
        force_copy_file(src, dst2)
        self.assertTrue(os.path.isfile(dst2))

        # Test that we correctly overwrite a readonly file pointed to by `dst`
        os.chmod(dst2, 0o444)
        with open(src, "w", encoding="utf-8") as f:
            f.write("Test2\n")
        force_copy_file(src, dst2)
        self.assertTrue(os.path.isfile(dst2))
        with open(dst2, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "Test2\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
