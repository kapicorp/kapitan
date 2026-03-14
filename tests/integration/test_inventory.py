# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import importlib
from pathlib import Path

import pytest

import kapitan.cached
from kapitan.cli import build_parser
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory


EXPECTED_TARGETS_COUNT = 10


def _set_inventory_backend(backend_id: str) -> None:
    args = build_parser().parse_args(["compile"])
    backend_module_name = backend_id.replace("-", "_")
    if not importlib.util.find_spec(backend_module_name):
        pytest.skip(f"backend module {backend_module_name} not available")
    args.inventory_backend = backend_id
    kapitan.cached.args = args


@pytest.mark.parametrize(
    "backend_id", [InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS]
)
def test_inventory_target(kubernetes_inventory_copy, backend_id, reset_cached_args):
    _set_inventory_backend(backend_id)
    inventory_path = Path(kubernetes_inventory_copy) / "inventory"
    inv = inventory(inventory_path=str(inventory_path), target_name="minikube-es")
    assert inv["parameters"]["cluster"]["name"] == "minikube"


@pytest.mark.parametrize(
    "backend_id", [InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS]
)
def test_inventory_all_targets(
    kubernetes_inventory_copy, backend_id, reset_cached_args
):
    _set_inventory_backend(backend_id)
    inventory_path = Path(kubernetes_inventory_copy) / "inventory"
    inv = inventory(inventory_path=str(inventory_path))
    assert inv.get("minikube-es") is not None
    assert len(inv) == EXPECTED_TARGETS_COUNT


def test_inventory_target_omegaconf(migrated_omegaconf_inventory, reset_cached_args):
    _set_inventory_backend(InventoryBackends.OMEGACONF)
    inv = inventory(
        inventory_path=str(migrated_omegaconf_inventory), target_name="minikube-es"
    )
    assert inv["parameters"]["cluster"]["name"] == "minikube"


def test_inventory_all_targets_omegaconf(
    migrated_omegaconf_inventory, reset_cached_args
):
    _set_inventory_backend(InventoryBackends.OMEGACONF)
    inv = inventory(inventory_path=str(migrated_omegaconf_inventory))
    assert inv.get("minikube-es") is not None
    assert len(inv) == EXPECTED_TARGETS_COUNT
