#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"inventory tests"

import importlib
import logging
import os
import shutil
import tempfile
import unittest

import kapitan.cached
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory


logger = logging.getLogger(__name__)


TEST_PWD = os.getcwd()
TEST_KUBERNETES_INVENTORY = os.path.join(TEST_PWD, "examples/kubernetes/")


class InventoryTargetTestBase(unittest.TestCase):
    backend_id = None
    inventory_path = None
    expected_targets_count = None

    def setUp(self) -> None:
        args = build_parser().parse_args(["compile"])

        # Fix inconsistency between reclass-rs (option name) and reclass_rs (module name)
        backend_module_name = self.backend_id.replace("-", "_")
        if not importlib.util.find_spec(backend_module_name):
            self.skipTest(f"backend module {backend_module_name} not available")
        args.inventory_backend = self.backend_id
        kapitan.cached.args = args

    def test_inventory_target(self):
        inv = inventory(inventory_path=self.inventory_path, target_name="minikube-es")
        logger.error(inv)
        self.assertEqual(inv["parameters"]["cluster"]["name"], "minikube")

    def test_inventory_all_targets(self):
        inv = inventory(inventory_path=self.inventory_path)
        self.assertNotEqual(inv.get("minikube-es"), None)
        self.assertEqual(len(inv), self.expected_targets_count)


class InventoryTargetTestReclass(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.RECLASS
        self.expected_targets_count = 10
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestReclassRs(InventoryTargetTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.RECLASS_RS
        self.expected_targets_count = 10
        self.inventory_path = "examples/kubernetes/inventory"
        super().setUp()


class InventoryTargetTestOmegaConf(InventoryTargetTestBase):
    temp_dir = tempfile.mkdtemp()

    def setUp(self) -> None:
        shutil.copytree(TEST_KUBERNETES_INVENTORY, self.temp_dir, dirs_exist_ok=True)
        self.backend_id = InventoryBackends.OMEGACONF
        self.expected_targets_count = 10
        from kapitan.inventory.backends.omegaconf import migrate

        self.inventory_path = os.path.join(self.temp_dir, "inventory")
        migrate(self.inventory_path)
        super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        return super().tearDown()


del InventoryTargetTestBase  # remove InventoryTargetTestBase so that it doesn't run


class InventoryTopicsTestBase(unittest.TestCase):
    """Tests for `kapitan.topics` aggregation across targets."""

    backend_id = None

    def setUp(self) -> None:
        backend_module_name = self.backend_id.replace("-", "_")
        if not importlib.util.find_spec(backend_module_name):
            self.skipTest(f"backend module {backend_module_name} not available")

        self.tmp = tempfile.mkdtemp()
        inv_dir = os.path.join(self.tmp, "inventory")
        os.makedirs(os.path.join(inv_dir, "classes"))
        targets_dir = os.path.join(inv_dir, "targets")
        os.makedirs(targets_dir)

        def write(name, body):
            with open(os.path.join(targets_dir, name), "w") as fp:
                fp.write(body)

        write(
            "target-1.yml",
            "parameters:\n  colour: red\n  kapitan:\n    topics:\n      colours:\n        parameters:\n          colour: ${colour}\n",
        )
        write(
            "target-2.yml",
            "parameters:\n  colour: blue\n  kapitan:\n    topics:\n      colours:\n        parameters:\n          colour: ${colour}\n",
        )
        write("target-3.yml", "parameters:\n  unrelated: true\n")

        # Consumer-only target: declares consume but produces no parameters.
        write(
            "consumer.yml",
            "parameters:\n  kapitan:\n    topics:\n      colours:\n        consume: true\n",
        )

        self.inventory_path = inv_dir
        if self.backend_id == InventoryBackends.OMEGACONF:
            from kapitan.inventory.backends.omegaconf import migrate

            migrate(self.inventory_path)
        args = build_parser().parse_args(["compile"])
        args.inventory_backend = self.backend_id
        kapitan.cached.reset_cache()
        kapitan.cached.args = args

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_topics_aggregated_on_inventory(self):
        inventory(inventory_path=self.inventory_path)
        topics = kapitan.cached.inv.topics
        self.assertIn("colours", topics)
        targets = topics["colours"]["parameters"]["targets"]
        self.assertEqual(targets["target-1"]["colour"], "red")
        self.assertEqual(targets["target-2"]["colour"], "blue")
        self.assertNotIn("target-3", targets)

        # Consumer-only target has no ``parameters:`` node on the topic so it
        # must not appear as a producer in the aggregated view.
        self.assertNotIn("consumer", targets)

    def test_topics_cli_excludes_consumer_only_targets(self):
        """``kapitan inventory --topics`` must not list targets that only
        declared ``consume: true`` (no ``parameters:`` sub-block) — those are
        consumers of the topic, not contributors to it.
        """
        from kapitan.topics import topics as topics_view

        inventory(inventory_path=self.inventory_path)

        # Full mapping path: ``kapitan inventory --topics``.
        all_topics = topics_view()
        self.assertIn("colours", all_topics)
        all_targets = all_topics["colours"]["parameters"]["targets"]
        self.assertIn("target-1", all_targets)
        self.assertIn("target-2", all_targets)
        self.assertNotIn("consumer", all_targets)

        # Single-topic path: ``kapitan inventory --topics colours``.
        one_topic = topics_view("colours")
        single_targets = one_topic["parameters"]["targets"]
        self.assertIn("target-1", single_targets)
        self.assertIn("target-2", single_targets)
        self.assertNotIn("consumer", single_targets)

    def test_consumed_topics_reflects_declaration(self):
        inventory(inventory_path=self.inventory_path)
        inv = kapitan.cached.inv
        self.assertEqual(inv.consumed_topics("consumer"), {"colours"})
        # Producers that did not declare ``consume: true`` are not consumers.
        self.assertEqual(inv.consumed_topics("target-1"), set())
        self.assertEqual(inv.consumed_topics("target-3"), set())
        # Unknown target gracefully returns the empty set.
        self.assertEqual(inv.consumed_topics("does-not-exist"), set())


class InventoryTopicsTestReclass(InventoryTopicsTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.RECLASS
        super().setUp()


class InventoryTopicsTestReclassRs(InventoryTopicsTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.RECLASS_RS
        super().setUp()


class InventoryTopicsTestOmegaConf(InventoryTopicsTestBase):
    def setUp(self):
        self.backend_id = InventoryBackends.OMEGACONF
        super().setUp()


del InventoryTopicsTestBase  # remove base so it doesn't run on its own
