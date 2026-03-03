#!/usr/bin/env python3

from types import SimpleNamespace

import pytest

from kapitan.errors import InventoryError


pytest.importorskip("reclass_rs")
reclass_rs_backend = pytest.importorskip("kapitan.inventory.backends.reclass_rs")


def _build_inventory(tmp_path):
    inventory_path = tmp_path / "inventory"
    targets_path = inventory_path / "targets"
    targets_path.mkdir(parents=True)
    (targets_path / "node1.yml").write_text("parameters: {}\n", encoding="utf-8")
    return inventory_path


def test_make_reclass_rs_passes_expected_arguments(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_rs_backend.ReclassRsInventory(
        inventory_path=str(inventory_path), initialise=False
    )

    captured = {}

    def _fake_get_reclass_config(
        inventory_path_arg,
        ignore_class_not_found,
        compose_target_name,
        normalise_nodes_classes,
    ):
        captured["get_reclass_config"] = {
            "inventory_path": inventory_path_arg,
            "ignore_class_not_found": ignore_class_not_found,
            "compose_target_name": compose_target_name,
            "normalise_nodes_classes": normalise_nodes_classes,
        }
        return {"nodes_uri": "targets", "classes_uri": "classes"}

    class _FakeConfig:
        @staticmethod
        def from_dict(inventory_path_arg, config_dict, debug):
            captured["from_dict"] = {
                "inventory_path": inventory_path_arg,
                "config_dict": config_dict,
                "debug": debug,
            }
            return "config"

    class _FakeReclass:
        @staticmethod
        def from_config(config):
            captured["from_config"] = config
            return "reclass"

    monkeypatch.setattr(
        reclass_rs_backend, "get_reclass_config", _fake_get_reclass_config
    )
    monkeypatch.setattr(reclass_rs_backend.logger, "isEnabledFor", lambda _lvl: True)
    monkeypatch.setattr(
        reclass_rs_backend,
        "reclass_rs",
        SimpleNamespace(Config=_FakeConfig, Reclass=_FakeReclass),
    )

    result = inv._make_reclass_rs(ignore_class_not_found=True)

    assert result == "reclass"
    assert captured["get_reclass_config"]["normalise_nodes_classes"] is False
    assert captured["from_dict"]["inventory_path"] == str(inventory_path)
    assert captured["from_dict"]["debug"] is True
    assert captured["from_config"] == "config"


def test_render_targets_populates_target_data(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_rs_backend.ReclassRsInventory(
        inventory_path=str(inventory_path), initialise=False
    )
    inv.targets = {"node1": inv.target_class(name="node1", path="node1.yml")}

    node_info = SimpleNamespace(
        parameters={"hello": "world"},
        classes=["base"],
        applications=["app1"],
        exports={"foo": "bar"},
    )
    fake_inventory = SimpleNamespace(nodes={"node1": node_info})

    class _FakeReclass:
        def inventory(self):
            return fake_inventory

    monkeypatch.setattr(
        inv, "_make_reclass_rs", lambda *_args, **_kwargs: _FakeReclass()
    )

    inv.render_targets()

    node = inv.targets["node1"]
    assert node.parameters.model_dump(by_alias=True)["hello"] == "world"
    assert node.classes == ["base"]
    assert node.applications == ["app1"]
    assert node.exports == {"foo": "bar"}


def test_render_targets_wraps_value_error(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_rs_backend.ReclassRsInventory(
        inventory_path=str(inventory_path), initialise=False
    )
    inv.targets = {"node1": inv.target_class(name="node1", path="node1.yml")}

    def _raise_value_error(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(inv, "_make_reclass_rs", _raise_value_error)

    with pytest.raises(InventoryError, match="boom"):
        inv.render_targets()
