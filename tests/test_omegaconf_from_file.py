# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""The omegaconf `from_file` resolver only reads files inside the project (#1639)."""

from pathlib import Path

import pytest
import yaml
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan
from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers


@pytest.fixture
def project(temp_dir, monkeypatch):
    """A project with files/inside.txt, and outside.txt one level above it."""
    root = Path(temp_dir) / "project"
    (root / "inventory/classes").mkdir(parents=True)
    (root / "files").mkdir()
    (root / "files/inside.txt").write_text("inside")
    (Path(temp_dir) / "outside.txt").write_text("outside")
    monkeypatch.chdir(root)
    return root


def resolve(path, inventory_path="inventory"):
    register_resolvers(inventory_path)
    return OmegaConf.create({"value": f"${{from_file:{path}}}"}).value


def test_reads_file_inside_project(project):
    assert resolve("files/inside.txt") == "inside"
    assert resolve(str(project / "files/inside.txt")) == "inside"


def test_reads_file_inside_inventory_outside_working_dir(project, temp_dir):
    inventory = Path(temp_dir) / "elsewhere/inventory"
    inventory.mkdir(parents=True)
    (inventory / "data.txt").write_text("inventory")
    assert resolve(str(inventory / "data.txt"), str(inventory)) == "inventory"


@pytest.mark.parametrize("kind", ["absolute", "dotdot", "symlink"])
def test_refuses_file_outside_project(project, temp_dir, kind):
    outside = Path(temp_dir) / "outside.txt"
    if kind == "absolute":
        path = str(outside)
    elif kind == "dotdot":
        path = "../outside.txt"
    else:
        path = "files/link.txt"
        (project / path).symlink_to(outside)
    with pytest.raises(InterpolationResolutionError, match="outside the project"):
        resolve(path)


def write_target(root: Path, path: str):
    (root / "templates").mkdir(exist_ok=True)
    (root / "templates/out.txt").write_text("{{ inventory.parameters.value }}")
    (root / "inventory/targets").mkdir(exist_ok=True)
    target = {
        "parameters": {
            "value": f"${{from_file:{path}}}",
            "kapitan": {
                "vars": {"target": "t"},
                "compile": [
                    {
                        "input_type": "jinja2",
                        "input_paths": ["templates/out.txt"],
                        "output_path": ".",
                    }
                ],
            },
        }
    }
    (root / "inventory/targets/t.yml").write_text(yaml.safe_dump(target))


def compile_omegaconf():
    reset_cache()
    kapitan("compile", "--inventory-backend=omegaconf")


def test_compile_reads_file_inside_project(project):
    write_target(project, "files/inside.txt")
    compile_omegaconf()
    assert (project / "compiled/t/out.txt").read_text() == "inside"


def test_compile_fails_on_file_outside_project(project):
    write_target(project, "../outside.txt")
    with pytest.raises(SystemExit):
        compile_omegaconf()
    assert not (project / "compiled/t").exists()
