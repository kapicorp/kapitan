#!/usr/bin/env python3

from types import SimpleNamespace

import pytest

from kapitan.inputs import get_compiler
from kapitan.inventory.model.input_types import InputTypes


@pytest.fixture(autouse=True)
def _reset_get_compiler_cache():
    get_compiler.cache_clear()
    yield
    get_compiler.cache_clear()


@pytest.mark.parametrize(
    ("input_type", "expected_class_name"),
    [
        (InputTypes.JINJA2, "Jinja2"),
        (InputTypes.HELM, "Helm"),
        (InputTypes.JSONNET, "Jsonnet"),
        (InputTypes.KADET, "Kadet"),
        (InputTypes.COPY, "Copy"),
        (InputTypes.EXTERNAL, "External"),
        (InputTypes.REMOVE, "Remove"),
        (InputTypes.KUSTOMIZE, "Kustomize"),
        (InputTypes.CUELANG, "Cuelang"),
    ],
)
def test_get_compiler_returns_expected_class(input_type, expected_class_name):
    compiler_cls = get_compiler(input_type)
    assert compiler_cls.__name__ == expected_class_name


def test_get_compiler_returns_none_for_unknown_type():
    assert get_compiler("unknown-type") is None


def test_get_compiler_wraps_import_error(monkeypatch):
    def _raise_import_error(*_args, **_kwargs):
        raise ImportError("boom")

    monkeypatch.setattr("kapitan.inputs.importlib.import_module", _raise_import_error)

    with pytest.raises(ImportError, match="Could not import module or class"):
        get_compiler(InputTypes.JINJA2)


def test_get_compiler_wraps_attribute_error(monkeypatch):
    monkeypatch.setattr(
        "kapitan.inputs.importlib.import_module",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )

    with pytest.raises(ImportError, match="Could not import module or class"):
        get_compiler(InputTypes.JINJA2)


def test_get_compiler_uses_cache(monkeypatch):
    calls = {"count": 0}

    class _FakeJinja2:
        pass

    def _import_module(*_args, **_kwargs):
        calls["count"] += 1
        return SimpleNamespace(Jinja2=_FakeJinja2)

    monkeypatch.setattr("kapitan.inputs.importlib.import_module", _import_module)

    first = get_compiler(InputTypes.JINJA2)
    second = get_compiler(InputTypes.JINJA2)

    assert first is _FakeJinja2
    assert second is _FakeJinja2
    assert calls["count"] == 1
