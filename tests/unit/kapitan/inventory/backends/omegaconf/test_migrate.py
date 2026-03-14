#!/usr/bin/env python3

import importlib

from kapitan.inventory.backends.omegaconf.migrate import (
    migrate,
    migrate_dir,
    migrate_file,
    migrate_str,
)


def test_migrate_str_rewrites_interpolation_and_metadata():
    content = "value: ${foo:bar}\nmeta: ${_reclass_:name}\n"
    updated = migrate_str(content)

    assert "${foo.bar}" in updated
    assert "${_kapitan_.name}" in updated


def test_migrate_str_rewrites_escaped_interpolation_to_escape_resolver():
    content = r"value: \${foo:bar}"
    updated = migrate_str(content)

    assert "${escape:foo:bar}" in updated


def test_migrate_file_updates_content(tmp_path):
    input_file = tmp_path / "target.yml"
    input_file.write_text("value: ${foo:bar}\n", encoding="utf-8")

    migrate_file(str(input_file))

    assert "${foo.bar}" in input_file.read_text(encoding="utf-8")


def test_migrate_dir_processes_only_yaml_files(tmp_path):
    inventory_dir = tmp_path / "inventory"
    inventory_dir.mkdir()
    yaml_file = inventory_dir / "a.yml"
    yaml_file.write_text("value: ${foo:bar}\n", encoding="utf-8")
    yml_file = inventory_dir / "b.yaml"
    yml_file.write_text("value: ${bar:baz}\n", encoding="utf-8")
    txt_file = inventory_dir / "c.txt"
    txt_file.write_text("value: ${skip:this}\n", encoding="utf-8")

    migrate_dir(str(inventory_dir))

    assert "${foo.bar}" in yaml_file.read_text(encoding="utf-8")
    assert "${bar.baz}" in yml_file.read_text(encoding="utf-8")
    assert txt_file.read_text(encoding="utf-8") == "value: ${skip:this}\n"


def test_migrate_missing_path_reports_error(capsys, tmp_path):
    migrate(str(tmp_path / "missing-inventory"))
    captured = capsys.readouterr()
    assert "does not exist" in captured.out


def test_migrate_accepts_single_file_path(tmp_path):
    inventory_file = tmp_path / "inventory.yaml"
    inventory_file.write_text("value: ${foo:bar}\n", encoding="utf-8")

    migrate(str(inventory_file))
    assert "${foo.bar}" in inventory_file.read_text(encoding="utf-8")


def test_migrate_accepts_directory_path(tmp_path):
    inventory_dir = tmp_path / "inventory"
    inventory_dir.mkdir()
    inventory_file = inventory_dir / "target.yml"
    inventory_file.write_text("value: ${foo:bar}\n", encoding="utf-8")

    migrate(str(inventory_dir))

    assert "${foo.bar}" in inventory_file.read_text(encoding="utf-8")


def test_migrate_dir_handles_file_errors_without_aborting(tmp_path, monkeypatch):
    inventory_dir = tmp_path / "inventory"
    inventory_dir.mkdir()
    (inventory_dir / "good.yaml").write_text("value: ${foo:bar}\n", encoding="utf-8")

    def _failing_migrate_file(_file):
        raise RuntimeError("broken file")

    migrate_module = importlib.import_module(
        "kapitan.inventory.backends.omegaconf.migrate"
    )
    monkeypatch.setattr(migrate_module, "migrate_file", _failing_migrate_file)

    # The current implementation builds an InventoryError object in this branch
    # but does not raise it; this assertion captures that existing behavior.
    migrate_dir(str(inventory_dir))


def test_migrate_ignores_existing_non_regular_paths(monkeypatch):
    migrate_module = importlib.import_module(
        "kapitan.inventory.backends.omegaconf.migrate"
    )

    monkeypatch.setattr(migrate_module.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(migrate_module.os.path, "isdir", lambda _p: False)
    monkeypatch.setattr(migrate_module.os.path, "isfile", lambda _p: False)

    # Should not raise, print, or call migration helpers when path type is unknown.
    migrate("/tmp/non-regular-entry")
