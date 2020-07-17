import os
import sys
import unittest
import tempfile
from shutil import rmtree, copytree
from distutils.dir_util import copy_tree
from kapitan.cached import reset_cache
from kapitan.cli import main
import yaml
from kapitan.resources import yaml_load
import json
from kapitan.dependency_manager.base import (
    fetch_git_dependency,
    fetch_http_dependency,
    fetch_git_source,
    fetch_http_source,
)


class RemoteInventoryTest(unittest.TestCase):
    def setUp(self):
        os.chdir(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "test_remote_inventory", "environment_one"
            )
        )

    def test_fetch_git_inventory(self):
        """
        test fetching of git inventories
        """
        temp_dir = tempfile.mkdtemp()
        repo_dir = os.path.join(temp_dir, "7a8f3940kapitan.git")
        git_source = "https://github.com/deepmind/kapitan.git"
        fetch_git_source(git_source, repo_dir, item_type="Inventory")
        self.assertTrue(os.path.isfile(os.path.join(repo_dir, "README.md")))
        rmtree(temp_dir)

    def test_clone_inv_subdir(self):
        """
        test clonning of inventories from git and storing it in the output path
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        git_source = "https://github.com/deepmind/kapitan.git"
        inv = [{"output_path": os.path.join(output_dir, "subdir"), "ref": "master", "subdir": "tests"}]
        fetch_git_dependency((git_source, inv), temp_dir, force=False, item_type="inventory")
        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir")))
        rmtree(output_dir)
        rmtree(temp_dir)

    def test_fetch_http_inventory(self):
        """
        test fetching of inventories over http
        """
        temp_dir = tempfile.mkdtemp()

        http_sources = [
            ("https://github.com/deepmind/kapitan/archive/master.zip", "009a21cfmaster.zip"),
            (
                "https://raw.githubusercontent.com/deepmind/kapitan/master/tests/test_resources/inventory/classes/common.yml",
                "eac6ceb7common.yml",
            ),
            (
                "https://github.com/deepmind/kapitan/raw/master/tests/test_remote_inventory/zipped_inventories/inventory.zip",
                "47c29a3binventory.zip",
            ),
        ]
        for source, path_hash in http_sources:
            fetch_http_source(source, os.path.join(temp_dir, path_hash), item_type="Inventory")

        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "009a21cfmaster.zip")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "eac6ceb7common.yml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_dir, "47c29a3binventory.zip")))
        rmtree(temp_dir)

    def test_unpack_http_inv(self):
        """
        test unpacking of remote inventories after downloading it over http
        """
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        # tar.gz file
        http_source = "https://github.com/deepmind/kapitan/raw/master/tests/test_remote_inventory/zipped_inventories/inventory.tar.gz"
        inv = [{"output_path": os.path.join(output_dir, "subdir"), "unpack": "True"}]
        fetch_http_dependency((http_source, inv), temp_dir, force=False, item_type="inventory")

        self.assertTrue(os.path.isdir(os.path.join(output_dir, "subdir", "targets")))
        rmtree(temp_dir)
        rmtree(output_dir)

    def test_compile_fetch(self):
        """ Run $ kapitan compile --fetch \
            --output-path=some/dir/ \
            --inventory-path=another/dir \
            --targets remoteinv-example remoteinv-nginx zippedinv\
            --force
            were some/dir/ & another/dir/ are directories chosen by the user

            Recursively force fetch inventories and compile
        """
        temp_output = tempfile.mkdtemp()
        temp_inv = tempfile.mkdtemp()

        copy_tree(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "test_remote_inventory",
                "environment_one",
                "inventory",
            ),
            temp_inv,
        )
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--output-path",
            temp_output,
            "--inventory-path",
            temp_inv,
            "--targets",
            "remoteinv-example",
            "remoteinv-nginx",
            "zippedinv",
            "--force",
        ]
        main()

        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "remoteinv-nginx.yml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "nginx.yml")))
        self.assertTrue(os.path.isfile(os.path.join(temp_inv, "targets", "nginx-dev.yml")))
        self.assertTrue(os.path.isdir(os.path.join(temp_output, "compiled", "remoteinv-nginx")))
        self.assertTrue(os.path.isdir(os.path.join(temp_output, "compiled", "zippedinv")))

        rmtree(temp_inv)
        rmtree(temp_output)

    def test_force_fetch(self):
        """Test overwriting inventory items while using the --force flag

        runs $ kapitan compile --fetch --cache --output-path=temp_output\
            --inventory-pat=temp_inv --targets remoteinv-example
        runs $ kapitan compile --fetch --cache --output-path=temp_output\
            --inventory-pat=temp_inv --targets remoteinv-example --force
        """

        temp_output = tempfile.mkdtemp()
        temp_inv = tempfile.mkdtemp()
        copy_tree(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "test_remote_inventory",
                "environment_one",
                "inventory",
            ),
            temp_inv,
        )
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--cache",
            "--output-path",
            temp_output,
            "--inventory-path",
            temp_inv,
            "--targets",
            "remoteinv-example",
        ]
        main()

        fname = os.path.join(temp_inv, "targets", "zippedinv.yml")
        data = json.loads(yaml_load([os.path.dirname(fname)], os.path.basename(fname)))
        data["parameters"]["compression_type"] = "test"
        with open(fname, "w") as yaml_file:
            yaml_file.write(yaml.dump(data, default_flow_style=False))

        reset_cache()
        main()
        # no change in zippedinv.yml
        new_data = json.loads(yaml_load([os.path.dirname(fname)], os.path.basename(fname)))

        reset_cache()
        sys.argv = [
            "kapitan",
            "compile",
            "--fetch",
            "--cache",
            "--output-path",
            temp_output,
            "--inventory-path",
            temp_inv,
            "--targets",
            "remoteinv-example",
            "--force",
        ]
        main()
        # zippedinv.yml overwritten
        force_fetched_data = json.loads(yaml_load([os.path.dirname(fname)], os.path.basename(fname)))
        self.assertEqual(new_data["parameters"]["compression_type"], "test")
        self.assertEqual(force_fetched_data["parameters"]["compression_type"], "gzip")
        rmtree(temp_inv)
        rmtree(temp_output)

    def tearDown(self):
        os.chdir("../../../")
        reset_cache()
