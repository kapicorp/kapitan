#!/usr/bin/env python3

import os

import pytest
import yaml

from kapitan.errors import InventoryError


pytest.importorskip("reclass")
reclass_backend = pytest.importorskip("kapitan.inventory.backends.reclass")


def _build_inventory(tmp_path):
    inventory_path = tmp_path / "inventory"
    targets_path = inventory_path / "targets"
    targets_path.mkdir(parents=True)
    (targets_path / "node1.yml").write_text("parameters: {}\n", encoding="utf-8")
    return inventory_path


def _minimal_config(inventory_path):
    return {
        "storage_type": "yaml_fs",
        "inventory_base_uri": str(inventory_path),
        "nodes_uri": "targets",
        "classes_uri": "classes",
        "compose_node_name": False,
    }


def test_get_reclass_config_defaults(tmp_path):
    inventory_path = _build_inventory(tmp_path)
    config = reclass_backend.get_reclass_config(str(inventory_path))

    assert config["storage_type"] == "yaml_fs"
    assert config["inventory_base_uri"] == str(inventory_path)
    assert config["nodes_uri"] == os.path.normpath(str(inventory_path / "targets"))
    assert config["classes_uri"] == os.path.normpath(str(inventory_path / "classes"))


def test_get_reclass_config_file_overrides(tmp_path):
    inventory_path = _build_inventory(tmp_path)
    config_file = inventory_path / "reclass-config.yml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "nodes_uri": "my-targets",
                "classes_uri": "my-classes",
                "class_mappings": {"old": "new"},
                "storage_type": "yaml_fs",
            }
        ),
        encoding="utf-8",
    )

    config = reclass_backend.get_reclass_config(
        str(inventory_path), ignore_class_not_found=True, compose_target_name=True
    )

    assert config["compose_node_name"] is True
    assert config["ignore_class_notfound"] is True
    assert config["class_mappings"] == {"old": "new"}
    assert config["nodes_uri"] == os.path.normpath(str(inventory_path / "my-targets"))
    assert config["classes_uri"] == os.path.normpath(str(inventory_path / "my-classes"))


def test_get_reclass_config_can_skip_path_normalization(tmp_path):
    inventory_path = _build_inventory(tmp_path)
    config = reclass_backend.get_reclass_config(
        str(inventory_path), normalise_nodes_classes=False
    )

    assert config["nodes_uri"] == "targets"
    assert config["classes_uri"] == "classes"


def test_render_targets_populates_target_data(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_backend.ReclassInventory(
        inventory_path=str(inventory_path), initialise=False
    )
    inv.targets = {"node1": inv.target_class(name="node1", path="node1.yml")}

    monkeypatch.setattr(
        reclass_backend,
        "get_reclass_config",
        lambda *_args, **_kwargs: _minimal_config(inventory_path),
    )
    monkeypatch.setattr(
        reclass_backend.reclass, "get_storage", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(
        reclass_backend.reclass.settings, "Settings", lambda config: config
    )

    class _FakeCore:
        def __init__(self, *_args, **_kwargs):
            pass

        def inventory(self):
            return {
                "nodes": {
                    "node1": {
                        "parameters": {"hello": "world"},
                        "classes": ["base"],
                        "applications": ["app1"],
                        "exports": {"foo": "bar"},
                    }
                }
            }

    monkeypatch.setattr(reclass_backend.reclass.core, "Core", _FakeCore)

    inv.render_targets()

    node = inv.targets["node1"]
    assert node.parameters.model_dump(by_alias=True)["hello"] == "world"
    assert node.classes == ["base"]
    assert node.applications == ["app1"]
    assert node.exports == {"foo": "bar"}


def test_render_targets_wraps_not_found_error(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_backend.ReclassInventory(
        inventory_path=str(inventory_path), initialise=False
    )
    inv.targets = {"node1": inv.target_class(name="node1", path="node1.yml")}

    class _FakeReclassException(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    class _FakeNotFoundError(_FakeReclassException):
        pass

    monkeypatch.setattr(reclass_backend, "ReclassException", _FakeReclassException)
    monkeypatch.setattr(reclass_backend, "NotFoundError", _FakeNotFoundError)
    monkeypatch.setattr(
        reclass_backend,
        "get_reclass_config",
        lambda *_args, **_kwargs: _minimal_config(inventory_path),
    )

    def _raise_not_found(*_args, **_kwargs):
        raise _FakeNotFoundError("inventory not found")

    monkeypatch.setattr(reclass_backend.reclass, "get_storage", _raise_not_found)

    with pytest.raises(InventoryError, match="inventory not found"):
        inv.render_targets()


def test_render_targets_wraps_generic_reclass_error(monkeypatch, tmp_path):
    inventory_path = _build_inventory(tmp_path)
    inv = reclass_backend.ReclassInventory(
        inventory_path=str(inventory_path), initialise=False
    )
    inv.targets = {"node1": inv.target_class(name="node1", path="node1.yml")}

    class _FakeReclassException(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    monkeypatch.setattr(reclass_backend, "ReclassException", _FakeReclassException)
    monkeypatch.setattr(reclass_backend, "NotFoundError", type("NotFoundError", (), {}))
    monkeypatch.setattr(
        reclass_backend,
        "get_reclass_config",
        lambda *_args, **_kwargs: _minimal_config(inventory_path),
    )

    def _raise_error(*_args, **_kwargs):
        raise _FakeReclassException("boom")

    monkeypatch.setattr(reclass_backend.reclass, "get_storage", _raise_error)

    with pytest.raises(InventoryError, match="boom"):
        inv.render_targets()
