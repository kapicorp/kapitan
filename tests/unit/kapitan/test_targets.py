#!/usr/bin/env python3

from pathlib import Path
from types import SimpleNamespace

import pytest

from kapitan.errors import CompileError, InventoryError
from kapitan.targets import (
    compile_target,
    compile_targets,
    load_target_inventory,
    search_targets,
)


class _Target:
    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters


class _Inventory:
    def __init__(self, targets):
        self.targets = targets

    def get_targets(self, requested):
        return {name: self.targets[name] for name in requested}


def _params_with_labels(labels):
    return SimpleNamespace(kapitan=SimpleNamespace(labels=labels, compile=[]))


def test_search_targets_matches_labels():
    inventory = _Inventory(
        {
            "prod": _Target("prod", _params_with_labels({"env": "prod"})),
            "dev": _Target("dev", _params_with_labels({"env": "dev"})),
        }
    )

    targets = search_targets(inventory, ["prod", "dev"], ["env=prod"])
    assert targets == ["prod"]


def test_search_targets_no_labels_returns_requested():
    inventory = _Inventory(
        {
            "prod": _Target("prod", _params_with_labels({"env": "prod"})),
            "dev": _Target("dev", _params_with_labels({"env": "dev"})),
        }
    )

    targets = search_targets(inventory, ["prod"], None)
    assert targets == ["prod"]


def test_search_targets_invalid_label_format():
    inventory = _Inventory({})
    with pytest.raises(CompileError):
        search_targets(inventory, [], ["env"])


def test_search_targets_no_match():
    inventory = _Inventory(
        {
            "prod": _Target("prod", _params_with_labels({"env": "prod"})),
        }
    )

    with pytest.raises(CompileError):
        search_targets(inventory, ["prod"], ["env=dev"])


def test_search_targets_skips_targets_missing_requested_label():
    inventory = _Inventory(
        {
            "missing": _Target("missing", _params_with_labels({"app": "demo"})),
            "prod": _Target("prod", _params_with_labels({"env": "prod"})),
        }
    )

    assert search_targets(inventory, ["missing", "prod"], ["env=prod"]) == ["prod"]


def test_load_target_inventory_empty_parameters():
    inventory = _Inventory({"prod": _Target("prod", None)})
    with pytest.raises(InventoryError):
        load_target_inventory(inventory, ["prod"])


def test_load_target_inventory_skip_when_missing_params():
    inventory = _Inventory({"prod": _Target("prod", None)})
    targets = load_target_inventory(inventory, ["prod"], ignore_class_not_found=True)
    assert targets == []


def test_load_target_inventory_missing_kapitan():
    inventory = _Inventory({"prod": _Target("prod", SimpleNamespace(kapitan=None))})
    with pytest.raises(InventoryError):
        load_target_inventory(inventory, ["prod"])


def test_load_target_inventory_sets_full_path():
    target = _Target(
        "prod.app", SimpleNamespace(kapitan=SimpleNamespace(compile=[], labels={}))
    )
    inventory = _Inventory({"prod.app": target})

    targets = load_target_inventory(inventory, ["prod.app"])
    assert len(targets) == 1
    assert targets[0].target_full_path == "prod/app"


def test_load_target_inventory_with_all_targets():
    inventory = _Inventory(
        {
            "prod": _Target(
                "prod", SimpleNamespace(kapitan=SimpleNamespace(compile=[], labels={}))
            )
        }
    )

    targets = load_target_inventory(inventory, None)
    assert len(targets) == 1


def test_load_target_inventory_key_error_path():
    class _Targets:
        def items(self):
            return [("prod", _Target("prod", _params_with_labels({"env": "prod"})))]

        def __getitem__(self, _key):
            raise KeyError("missing")

    inventory = _Inventory(_Targets())
    targets = load_target_inventory(inventory, None)
    assert targets == []


class _FailingCompiler:
    def __init__(self, *args, **kwargs):
        pass

    def compile_obj(self, _config):
        raise RuntimeError("boom")


class _NoCompileMethod:
    def __init__(self, *args, **kwargs):
        pass


def _target_config(continue_on_compile_error):
    return SimpleNamespace(
        compile=[
            SimpleNamespace(
                input_type="fake", continue_on_compile_error=continue_on_compile_error
            )
        ],
        vars=SimpleNamespace(target="target"),
        target_full_path="target",
    )


def test_compile_target_continue_on_error(monkeypatch):
    monkeypatch.setattr("kapitan.targets.get_compiler", lambda _t: _FailingCompiler)

    compile_target(
        _target_config(continue_on_compile_error=True),
        search_paths=[],
        compile_path="out",
        ref_controller=None,
        args=SimpleNamespace(inventory_pool_cache=False),
    )


def test_compile_target_raises_compile_error(monkeypatch):
    monkeypatch.setattr("kapitan.targets.get_compiler", lambda _t: _FailingCompiler)

    with pytest.raises(CompileError):
        compile_target(
            _target_config(continue_on_compile_error=False),
            search_paths=[],
            compile_path="out",
            ref_controller=None,
            args=SimpleNamespace(inventory_pool_cache=False),
        )


def test_compile_target_attribute_error(monkeypatch):
    monkeypatch.setattr("kapitan.targets.get_compiler", lambda _t: _NoCompileMethod)

    with pytest.raises(CompileError):
        compile_target(
            _target_config(continue_on_compile_error=False),
            search_paths=[],
            compile_path="out",
            ref_controller=None,
            args=SimpleNamespace(inventory_pool_cache=False),
        )


def test_compile_target_populates_cache(monkeypatch):
    from kapitan import cached

    cached.inv = None
    cache_dict = cached.as_dict()

    try:
        compile_target(
            SimpleNamespace(
                compile=[],
                vars=SimpleNamespace(target="target"),
                target_full_path="target",
            ),
            search_paths=[],
            compile_path="out",
            ref_controller=None,
            args=SimpleNamespace(inventory_pool_cache=False),
            globals_cached=cache_dict,
        )

        assert cached.inv is cache_dict["inv"]
    finally:
        cached.inv = None


class _FakePool:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def imap_unordered(self, worker, targets):
        for target in targets:
            worker(target)
            yield None

    def terminate(self):
        return None


@pytest.fixture
def patch_compile_targets_runtime(monkeypatch):
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    def _patch(
        *,
        inventory_targets=None,
        searched_targets=None,
        target_objs=None,
    ):
        searched = searched_targets or ["a"]
        targets = inventory_targets or {name: object() for name in searched}
        inventory = SimpleNamespace(targets=targets)
        monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
        monkeypatch.setattr(
            "kapitan.targets.search_targets", lambda _i, _t, _labels: searched
        )
        if target_objs is None:
            target_objs = [
                SimpleNamespace(target_full_path=name, dependencies=[])
                for name in searched
            ]
        monkeypatch.setattr(
            "kapitan.targets.load_target_inventory", lambda *_a, **_k: target_objs
        )
        return inventory

    return _patch


def test_compile_targets_success(
    tmp_path, monkeypatch, patch_compile_targets_runtime, targets_compile_args
):
    target_objs = [
        SimpleNamespace(
            target_full_path="a",
            dependencies=[SimpleNamespace(force_fetch=True)],
        ),
        SimpleNamespace(target_full_path="b", dependencies=[]),
    ]
    patch_compile_targets_runtime(
        searched_targets=["a", "b"],
        target_objs=target_objs,
    )

    def _compile_target(target_config, search_paths, compile_path, **_kwargs):
        temp_root = tmp_path / "scratch"
        temp_root.mkdir(exist_ok=True)
        temp_path = temp_root / target_config.target_full_path
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "ok.txt").write_text("ok", encoding="utf-8")
        compile_root = Path(compile_path)
        compile_target = compile_root / target_config.target_full_path
        compile_target.mkdir(parents=True, exist_ok=True)
        (compile_target / "ok.txt").write_text("ok", encoding="utf-8")

    monkeypatch.setattr("kapitan.targets.compile_target", _compile_target)
    monkeypatch.setattr("kapitan.targets.fetch_dependencies", lambda *_a, **_k: None)

    args = targets_compile_args(output_path=str(tmp_path))
    compile_targets("inventory", [], None, args)

    assert (tmp_path / "compiled" / "a" / "ok.txt").is_file()


def test_compile_targets_partial_targets(
    tmp_path, monkeypatch, patch_compile_targets_runtime, targets_compile_args
):
    patch_compile_targets_runtime(
        searched_targets=["a"],
        target_objs=[SimpleNamespace(target_full_path="a", dependencies=[])],
    )

    def _compile_target(target_config, search_paths, compile_path, **_kwargs):
        temp_path = Path(compile_path) / target_config.target_full_path
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "ok.txt").write_text("ok", encoding="utf-8")

    monkeypatch.setattr("kapitan.targets.compile_target", _compile_target)
    args = targets_compile_args(output_path=str(tmp_path), targets=["a"])
    compile_targets("inventory", [], None, args)

    assert (tmp_path / "compiled" / "a" / "ok.txt").is_file()


def test_compile_targets_force_flag(
    tmp_path, monkeypatch, patch_compile_targets_runtime, targets_compile_args
):
    patch_compile_targets_runtime(
        searched_targets=["a"],
        target_objs=[SimpleNamespace(target_full_path="a", dependencies=[])],
    )

    def _compile_target(target_config, search_paths, compile_path, **_kwargs):
        temp_path = Path(compile_path) / target_config.target_full_path
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "ok.txt").write_text("ok", encoding="utf-8")

    monkeypatch.setattr("kapitan.targets.compile_target", _compile_target)
    monkeypatch.setattr("kapitan.targets.fetch_dependencies", lambda *_a, **_k: None)

    args = targets_compile_args(output_path=str(tmp_path), force=True)
    compile_targets("inventory", [], None, args)


def test_compile_targets_fetch_path_uses_ignore_class_not_found(
    tmp_path, monkeypatch, targets_compile_args
):
    inventory = SimpleNamespace(targets={"a": object()})
    target_objs = [SimpleNamespace(target_full_path="a", dependencies=[])]
    load_calls = {}
    fetch_calls = []

    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
    monkeypatch.setattr("kapitan.targets.search_targets", lambda *_a, **_k: ["a"])
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    def _load_target_inventory(_inventory, _targets, ignore_class_not_found=False):
        load_calls["ignore_class_not_found"] = ignore_class_not_found
        return target_objs

    def _compile_target(target_config, search_paths, compile_path, **_kwargs):
        temp_path = Path(compile_path) / target_config.target_full_path
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "ok.txt").write_text("ok", encoding="utf-8")

    monkeypatch.setattr("kapitan.targets.load_target_inventory", _load_target_inventory)
    monkeypatch.setattr("kapitan.targets.compile_target", _compile_target)
    monkeypatch.setattr(
        "kapitan.targets.fetch_dependencies",
        lambda output_path, objs, dep_cache_dir, force_fetch, pool: fetch_calls.append(
            (output_path, objs, dep_cache_dir, force_fetch)
        ),
    )

    args = targets_compile_args(output_path=str(tmp_path), fetch=True)
    compile_targets("inventory", [], None, args)

    assert load_calls["ignore_class_not_found"] is True
    assert len(fetch_calls) == 1
    assert fetch_calls[0][0] == str(tmp_path)
    assert fetch_calls[0][1] == target_objs
    assert fetch_calls[0][3] is False


def test_compile_targets_no_target_objs(
    patch_compile_targets_runtime, targets_compile_args
):
    patch_compile_targets_runtime(searched_targets=["a"], target_objs=[])

    with pytest.raises(CompileError, match="no targets found"):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


def test_compile_targets_search_targets_error(monkeypatch, targets_compile_args):
    inventory = SimpleNamespace(targets={"a": object()})
    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
    monkeypatch.setattr(
        "kapitan.targets.search_targets",
        lambda *_a, **_k: (_ for _ in ()).throw(CompileError("nope")),
    )
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    with pytest.raises(CompileError):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


def test_compile_targets_no_match(monkeypatch, targets_compile_args):
    inventory = SimpleNamespace(targets={"a": object()})
    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
    monkeypatch.setattr("kapitan.targets.search_targets", lambda *_a, **_k: [])
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    with pytest.raises(CompileError):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


def test_compile_targets_no_discovered_targets(monkeypatch, targets_compile_args):
    class _Keys:
        def __len__(self):
            return 0

        def __eq__(self, other):
            return other == 0

    inventory = SimpleNamespace(targets=SimpleNamespace(keys=lambda: _Keys()))
    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)

    with pytest.raises(CompileError):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


def test_compile_targets_reclass_error(monkeypatch, targets_compile_args):
    from reclass.errors import NotFoundError

    inventory = SimpleNamespace(targets={"a": object()})
    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
    monkeypatch.setattr("kapitan.targets.search_targets", lambda *_a, **_k: ["a"])
    monkeypatch.setattr(
        "kapitan.targets.load_target_inventory",
        lambda *_a, **_k: (_ for _ in ()).throw(NotFoundError("missing")),
    )
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    with pytest.raises(InventoryError):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


def test_compile_targets_reclass_error_non_notfound(monkeypatch, targets_compile_args):
    from reclass.errors import ReclassException

    inventory = SimpleNamespace(targets={"a": object()})
    monkeypatch.setattr("kapitan.targets.get_inventory", lambda _p: inventory)
    monkeypatch.setattr("kapitan.targets.search_targets", lambda *_a, **_k: ["a"])
    monkeypatch.setattr(
        "kapitan.targets.load_target_inventory",
        lambda *_a, **_k: (_ for _ in ()).throw(ReclassException(msg="boom")),
    )
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    with pytest.raises(InventoryError):
        compile_targets("inventory", [], None, targets_compile_args(output_path="/tmp"))


@pytest.mark.parametrize("verbose", [False, True])
def test_compile_targets_worker_error(
    monkeypatch, patch_compile_targets_runtime, targets_compile_args, verbose
):
    patch_compile_targets_runtime(
        searched_targets=["a"],
        target_objs=[SimpleNamespace(target_full_path="a", dependencies=[])],
    )

    def _compile_target(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("kapitan.targets.compile_target", _compile_target)
    monkeypatch.setattr("kapitan.targets.multiprocessing.Pool", _FakePool)

    with pytest.raises(CompileError):
        compile_targets(
            "inventory",
            [],
            None,
            targets_compile_args(output_path="/tmp", verbose=verbose),
        )
