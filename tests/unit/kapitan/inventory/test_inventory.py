#!/usr/bin/env python3

import os

import pytest

from kapitan.errors import InventoryError
from kapitan.inventory.inventory import Inventory


class _Inventory(Inventory):
    def render_targets(self, targets=None, ignore_class_not_found=False):
        return None


def _write_target(path, name, content="parameters: {}\n"):
    target_path = os.path.join(path, f"{name}.yaml")
    with open(target_path, "w", encoding="utf-8") as fp:
        fp.write(content)
    return target_path


def test_inventory_initialises_targets(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod")
    _write_target(str(targets_path), "dev")
    (targets_path / "ignore.txt").write_text("nope", encoding="utf-8")

    inv = _Inventory(inventory_path=str(inv_path))

    assert set(inv.targets) == {"prod", "dev"}
    assert inv.initialised is True
    assert "kapitan" in inv.inventory["prod"]["parameters"]


def test_inventory_compose_target_name(tmp_path):
    inv_path = tmp_path / "inventory"
    nested = inv_path / "targets" / "env"
    nested.mkdir(parents=True)
    _write_target(str(nested), "prod")

    inv = _Inventory(inventory_path=str(inv_path), compose_target_name=True)

    assert "env.prod" in inv.targets


def test_inventory_conflicting_targets(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod")
    subdir = targets_path / "env"
    subdir.mkdir()
    _write_target(str(subdir), "prod")

    with pytest.raises(InventoryError):
        _Inventory(inventory_path=str(inv_path))


def test_inventory_getters_and_dunder_getitem(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod")

    inv = _Inventory(inventory_path=str(inv_path), initialise=True)

    assert inv.get_target("prod").name == "prod"
    assert list(inv.get_targets(["prod"])) == ["prod"]
    assert "prod" in inv.get_targets()
    assert isinstance(inv["prod"], dict)


def test_inventory_get_parameters_for_multiple(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod")

    inv = _Inventory(inventory_path=str(inv_path))
    with pytest.raises(ValueError):
        inv.get_parameters(["prod"])


def test_inventory_get_parameters_for_single_target(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod", content="parameters:\n  foo: bar\n")

    inv = _Inventory(inventory_path=str(inv_path))
    assert inv.get_parameters("prod") == inv.get_target("prod").parameters


def test_inventory_initialise_is_idempotent(tmp_path):
    inv_path = tmp_path / "inventory"
    targets_path = inv_path / "targets"
    targets_path.mkdir(parents=True)
    _write_target(str(targets_path), "prod")

    inv = _Inventory(inventory_path=str(inv_path))

    assert inv._Inventory__initialise(ignore_class_not_found=False) is True
