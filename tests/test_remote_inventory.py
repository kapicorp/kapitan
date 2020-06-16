import os
import sys
import unittest
import tempfile
from shutil import rmtree, copytree

from kapitan.cached import reset_cache
from kapitan.cli import main
from kapitan.remoteinventory.fetch import fetch_git_source, fetch_git_inventories
from kapitan.dependency_manager.base import DEPENDENCY_OUTPUT_CONFIG


class RemoteInventoryTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), "tests", "test_remote_inventory", "environment_one"))

    def test_fetch_git_inventory(self):
        temp_dir = tempfile.mkdtemp()
        git_source = "https://github.com/deepmind/kapitan.git"
        fetch_git_source(git_source, temp_dir)
        self.assertTrue(os.path.isdir(os.path.join(temp_dir, "kapitan.git", "kapitan")))
        rmtree(temp_dir)

    def test_clone_inv_subdir(self):
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        git_source = "https://github.com/deepmind/kapitan.git"
        inv = [{"output_path": os.path.join(output_dir, "subdir"), "ref": "master", "subdir": "tests"}]
        fetch_git_inventories((git_source, inv), "./inventory", temp_dir)
        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir")))
        rmtree(output_dir)
        rmtree(temp_dir)

    def test_compile_fetch(self):
        temp_dep = tempfile.mkdtemp()
        temp_inv = tempfile.mkdtemp()

        copytree(os.path.join("test_remote_inventory", "environment_one"), temp_inv)
        DEPENDENCY_OUTPUT_CONFIG["root_dir"] = temp_dep
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--output-path",
            temp_dep,
            "--inventory-path",
            temp_inv,
            "-t",
            "remoteinv-example",
            "remoteinv-nginx",
            "nginx",
            "nginx-dev",
        ]
        main()

        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "remoteinv-nginx.yml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "nginx.yml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "nginx-dev.yml")))
        self.assertTrue(os.path.isdir(os.path.join(temp_dep, "component", "tests")))
        self.assertTrue(os.path.isdir(os.path.join(temp_dep, "component", "acs-engine-autoscaler")))
        self.assertTrue(os.path.isdir(os.path.join(temp_dep, "component", "kapitan-repository")))
        self.assertTrue(os.path.isdir(os.path.join(temp_dep, "component", "source")))

        rmtree(temp_inv)
        rmtree(temp_dep)

    def tearDown(self):
        os.chdir("../../../")
        reset_cache()