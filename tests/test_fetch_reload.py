# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""`kapitan compile --fetch` reloads the inventory, so fetched classes take effect (#1638)."""

from pathlib import Path

import pytest
import yaml
from git import Repo

from kapitan.cached import reset_cache
from kapitan.cli import main as kapitan


# each backend with its reference to the parameter demo.value
each_backend = pytest.mark.parametrize(
    ("backend", "ref"),
    [
        ("reclass", "${demo:value}"),
        ("reclass-rs", "${demo:value}"),
        ("omegaconf", "${demo.value}"),
    ],
)

DEMO_PATH = "inventory/classes/recipes/demo"


def write_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def commit(repo: Repo, files: dict, ref: str):
    """Write `files` (path -> YAML data) into the repo and commit them on branch `ref`."""
    root = Path(repo.working_tree_dir)
    for name, data in files.items():
        write_yaml(root / name, data)
    repo.index.add(list(files))
    repo.create_head(ref, repo.index.commit(ref))


def git_dep(repo: Repo, subdir: str, output_path: str, ref: str | None = None):
    dep = {
        "type": "git",
        "source": repo.working_tree_dir,
        "subdir": subdir,
        "output_path": output_path,
    }
    if ref:
        dep["ref"] = ref
    return dep


@pytest.fixture
def project(temp_dir, monkeypatch):
    root = Path(temp_dir) / "project"
    (root / "templates").mkdir(parents=True)
    (root / "inventory/classes").mkdir(parents=True)
    monkeypatch.chdir(root)
    (root / "templates" / "out.txt").write_text(
        "{{ inventory.parameters.greeting }}{{ inventory.parameters.get('extra', '') }}"
    )
    return root


@pytest.fixture
def recipes(temp_dir):
    """A git repo holding the class `recipes.demo` under demo/, at refs v1 and v2."""
    repo = Repo.init(Path(temp_dir) / "recipes.git")
    commit(repo, {"demo/init.yml": {"parameters": {"demo": {"value": "one"}}}}, "v1")
    commit(
        repo,
        {
            "demo/init.yml": {"parameters": {"demo": {"value": "two"}}},
            "demo/extra.yml": {"parameters": {"extra": "-extra"}},
        },
        "v2",
    )
    return repo


def write_target(root: Path, classes=("recipes.demo",), deps=(), **params):
    write_yaml(
        root / "inventory/targets/t.yml",
        {
            "classes": list(classes),
            "parameters": {
                **params,
                "kapitan": {
                    "vars": {"target": "t"},
                    "dependencies": list(deps),
                    "compile": [
                        {
                            "input_type": "jinja2",
                            "input_paths": ["templates/out.txt"],
                            "output_path": ".",
                        }
                    ],
                },
            },
        },
    )


def compile_(backend, *flags):
    # each CLI run is a fresh process, the inventory cache would survive in-process
    reset_cache()
    kapitan("compile", f"--inventory-backend={backend}", *flags)


def output(root: Path) -> str:
    return (root / "compiled/t/out.txt").read_text()


@each_backend
def test_fetch_missing_class(project, recipes, backend, ref):
    """The target includes a class that only the fetch provides and points into it."""
    write_target(
        project, deps=[git_dep(recipes, "demo", DEMO_PATH, "v1")], greeting=ref
    )
    compile_(backend, "--fetch")
    assert output(project) == "one"


@each_backend
def test_fetch_pin_raised_adds_class(project, recipes, backend, ref):
    """--fetch after a pin bump makes a class that only the new pin ships available."""
    write_target(
        project, deps=[git_dep(recipes, "demo", DEMO_PATH, "v1")], greeting=ref
    )
    compile_(backend, "--fetch")
    write_target(
        project,
        classes=("recipes.demo", "recipes.demo.extra"),
        deps=[git_dep(recipes, "demo", DEMO_PATH, "v2")],
        greeting=ref,
    )
    compile_(backend, "--fetch")
    # --fetch keeps files that already exist, so demo/init.yml stays at v1
    assert output(project) == "one-extra"


@each_backend
def test_force_fetch_pin_raised_compiles_new_class(project, recipes, backend, ref):
    write_target(
        project, deps=[git_dep(recipes, "demo", DEMO_PATH, "v1")], greeting=ref
    )
    compile_(backend, "--fetch")
    write_target(
        project, deps=[git_dep(recipes, "demo", DEMO_PATH, "v2")], greeting=ref
    )
    compile_(backend, "--force-fetch")
    assert output(project) == "two"


@each_backend
def test_force_fetch_entry_reloads_without_flag(project, recipes, backend, ref):
    """Plain compile fetches `force_fetch: true` entries and compiles what they fetched."""
    write_target(
        project, deps=[git_dep(recipes, "demo", DEMO_PATH, "v1")], greeting=ref
    )
    compile_(backend, "--fetch")
    dep = git_dep(recipes, "demo", DEMO_PATH, "v2") | {"force_fetch": True}
    write_target(project, deps=[dep], greeting=ref)
    compile_(backend)
    assert output(project) == "two"


@each_backend
def test_fetched_class_declares_own_dependency(project, temp_dir, backend, ref):
    """A fetched class includes a second class, which its own dependency fetches in round 2."""
    repo = Repo.init(Path(temp_dir) / "nested.git")
    sub_path = f"{DEMO_PATH}/sub"
    commit(repo, {"sub/init.yml": {"parameters": {"demo": {"value": "deep"}}}}, "v1")
    commit(
        repo,
        {
            "demo/init.yml": {
                "classes": ["recipes.demo.sub"],
                "parameters": {
                    "kapitan": {"dependencies": [git_dep(repo, "sub", sub_path, "v1")]}
                },
            }
        },
        "v2",
    )
    write_target(project, deps=[git_dep(repo, "demo", DEMO_PATH, "v2")], greeting=ref)
    compile_(backend, "--fetch")
    assert output(project) == "deep"


@each_backend
def test_fetch_rounds_are_capped(project, temp_dir, backend, ref, capfd):
    """A chain of classes that keeps declaring new dependencies stops after 5 rounds."""
    repo = Repo.init(Path(temp_dir) / "chain.git")
    files = {}
    for level in range(1, 8):
        path = "inventory/classes/" + "/".join(f"l{i}" for i in range(1, level + 1))
        name = ".".join(f"l{i}" for i in range(1, level + 2))
        nxt = path + f"/l{level + 1}"
        files[f"l{level}/init.yml"] = {
            "classes": [name],
            "parameters": {
                "kapitan": {"dependencies": [git_dep(repo, f"l{level + 1}", nxt)]}
            },
        }
    commit(repo, files, "v1")
    write_target(
        project,
        classes=("l1",),
        deps=[git_dep(repo, "l1", "inventory/classes/l1")],
        greeting="x",
    )
    with pytest.raises(SystemExit):
        compile_(backend, "--fetch")
    err = capfd.readouterr().err
    assert "after 5 rounds" in err
    assert "l1.l2.l3.l4.l5.l6" in err


@each_backend
def test_duplicate_output_path_fails(project, recipes, temp_dir, backend, ref, capfd):
    other = Repo.init(Path(temp_dir) / "other.git")
    commit(other, {"demo/init.yml": {"parameters": {"demo": {"value": "x"}}}}, "v1")
    deps = [
        git_dep(recipes, "demo", DEMO_PATH, "v1"),
        git_dep(other, "demo", DEMO_PATH, "v1"),
    ]
    write_target(project, deps=deps, greeting=ref)
    with pytest.raises(SystemExit):
        compile_(backend, "--fetch")
    err = capfd.readouterr().err
    assert recipes.working_tree_dir in err
    assert other.working_tree_dir in err
    assert not (project / DEMO_PATH).exists()


@each_backend
def test_fetched_class_dependency_confined(project, temp_dir, backend, ref, capfd):
    """A dependency declared by a fetched class may not write outside the class."""
    repo = Repo.init(Path(temp_dir) / "evil.git")
    commit(
        repo,
        {
            "demo/init.yml": {
                "parameters": {
                    "demo": {"value": "one"},
                    "kapitan": {
                        "dependencies": [git_dep(repo, "demo", "templates/evil")]
                    },
                }
            }
        },
        "v1",
    )
    write_target(project, deps=[git_dep(repo, "demo", DEMO_PATH, "v1")], greeting=ref)
    with pytest.raises(SystemExit):
        compile_(backend, "--fetch")
    err = capfd.readouterr().err
    assert "templates/evil" in err
    assert not (project / "templates/evil").exists()
