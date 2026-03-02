# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from pathlib import Path

import pytest

from kapitan.inventory import InventoryBackends, get_inventory_backend
from kapitan.inventory.inventory import InventoryError


def _collect_target_names(targets_path: Path) -> list[str]:
    target_names = []
    for root, _, files in os.walk(targets_path):
        for filename in files:
            path = os.path.relpath(os.path.join(root, filename), targets_path)
            name = os.path.splitext(path)[0].replace(os.sep, ".")
            target_names.append(name)
    return target_names


def _assert_targets_resolvable(inv, target_names: list[str]) -> None:
    for target_name in target_names:
        nodeinfo = inv.get_target(target_name)
        assert nodeinfo is not None


@pytest.mark.parametrize(
    "backend_id", [InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS]
)
def test_compose_target_name(kubernetes_inventory_copy, backend_id, tmp_path):
    inventory_backend = get_inventory_backend(backend_id)
    inventory_path = Path(kubernetes_inventory_copy) / "inventory"
    targets_path = inventory_path / "targets"
    example_target_names = _collect_target_names(targets_path)

    # ensure normal rendering works
    inv = inventory_backend(
        inventory_path=str(inventory_path), compose_target_name=True
    )
    found_targets = inv.targets
    assert sorted(example_target_names) == sorted(list(found_targets.keys()))
    _assert_targets_resolvable(inv, example_target_names)

    # create compose_target_name setup from a snapshot to avoid nested copies
    snapshot_path = tmp_path / "targets_snapshot"
    shutil.copytree(targets_path, snapshot_path)
    shutil.copytree(snapshot_path, inventory_path / "targets" / "env1")
    shutil.copytree(snapshot_path, inventory_path / "targets" / "env2")

    composed_target_names = []
    for name in example_target_names:
        composed_target_names.extend([name, f"env1.{name}", f"env2.{name}"])

    # ensure inventory detects name collision
    with pytest.raises(InventoryError):
        inventory_backend(inventory_path=str(inventory_path), compose_target_name=False)

    # ensure compose_target_name works as intended
    inv = inventory_backend(
        inventory_path=str(inventory_path), compose_target_name=True
    )
    found_targets = inv.targets

    assert set(composed_target_names) == set(found_targets.keys())
    _assert_targets_resolvable(inv, composed_target_names)
