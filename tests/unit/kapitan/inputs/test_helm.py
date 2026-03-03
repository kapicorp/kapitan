#!/usr/bin/env python3

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kapitan.errors import HelmTemplateError
from kapitan.inputs.helm import (
    Helm,
    HelmChart,
    render_chart,
    write_helm_values_file,
)
from kapitan.inventory.model.input_types import KapitanInputTypeHelmConfig


def test_render_chart_invalid_short_flag():
    with pytest.raises(ValueError):
        render_chart(
            chart_dir="/tmp",
            output_path="/tmp",
            helm_path="helm",
            helm_params={"x": "1"},
            helm_values_file=None,
            helm_values_files=None,
        )


def test_render_chart_invalid_dash_flag():
    with pytest.raises(ValueError):
        render_chart(
            chart_dir="/tmp",
            output_path="/tmp",
            helm_path="helm",
            helm_params={"bad-flag": True},
            helm_values_file=None,
            helm_values_files=None,
        )


def test_render_chart_denied_flag():
    with pytest.raises(ValueError):
        render_chart(
            chart_dir="/tmp",
            output_path="/tmp",
            helm_path="helm",
            helm_params={"dry_run": True},
            helm_values_file=None,
            helm_values_files=None,
        )


def test_render_chart_set_flag():
    with pytest.raises(ValueError):
        render_chart(
            chart_dir="/tmp",
            output_path="/tmp",
            helm_path="helm",
            helm_params={"set": "a=b"},
            helm_values_file=None,
            helm_values_files=None,
        )


def test_render_chart_output_dash(monkeypatch):
    def _helm_cli(_helm_path, _args, stdout=None, **_kwargs):
        if stdout is not None:
            stdout.write("hello")
        return ""

    monkeypatch.setattr("kapitan.inputs.helm.helm_cli", _helm_cli)

    output, error = render_chart(
        chart_dir="/tmp",
        output_path="-",
        helm_path="helm",
        helm_params={},
        helm_values_file=None,
        helm_values_files=None,
    )

    assert output == "hello"
    assert error == ""


def test_render_chart_output_file(tmp_path, monkeypatch):
    def _helm_cli(_helm_path, _args, stdout=None, **_kwargs):
        if stdout is not None:
            stdout.write(b"hello")
        return ""

    monkeypatch.setattr("kapitan.inputs.helm.helm_cli", _helm_cli)

    output, error = render_chart(
        chart_dir="/tmp",
        output_path=str(tmp_path),
        helm_path="helm",
        helm_params={"output_file": "out.yaml"},
        helm_values_file=None,
        helm_values_files=None,
    )

    assert output == ""
    assert error == ""
    assert (tmp_path / "out.yaml").read_text(encoding="utf-8") == "hello"


def test_write_helm_values_file_quotes_numeric():
    values_file = write_helm_values_file({"value": "03190301"})
    content = Path(values_file).read_text(encoding="utf-8")
    assert "'03190301'" in content or '"03190301"' in content


def test_compile_file_writes_rendered_yaml(monkeypatch, tmp_path):
    def _fake_render_chart(
        chart_dir,
        output_path,
        helm_path,
        helm_params,
        helm_values_file,
        helm_values_files,
        helm_flags=None,
    ):
        output_dir = Path(output_path) / "chart" / "templates"
        output_dir.mkdir(parents=True, exist_ok=True)
        template = output_dir / "deployment.yaml"
        template.write_text(
            "kind: Deployment\nmetadata:\n  name: demo\n", encoding="utf-8"
        )
        return ("", "")

    monkeypatch.setattr("kapitan.inputs.helm.render_chart", _fake_render_chart)

    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    args = SimpleNamespace(reveal=False, indent=2)
    monkeypatch.setattr(
        "kapitan.inputs.base.cached.inv", {"target": {"parameters": {}}}
    )
    helm = Helm(str(compile_path), [], None, "target", args)
    config = KapitanInputTypeHelmConfig(input_paths=[], output_path=str(compile_path))

    helm.compile_file(config, "chart", str(compile_path))

    rendered = compile_path / "chart" / "templates" / "deployment.yaml"
    assert rendered.is_file()
    assert yaml.safe_load(rendered.read_text(encoding="utf-8"))["kind"] == "Deployment"


def test_compile_file_uses_values_and_kube_version_and_raises_on_render_error(
    monkeypatch, tmp_path
):
    compile_path = tmp_path / "compiled"
    compile_path.mkdir()

    monkeypatch.setattr(
        "kapitan.inputs.helm.write_helm_values_file",
        lambda _values: str(tmp_path / "values.yaml"),
    )
    monkeypatch.setattr(
        "kapitan.inputs.helm.render_chart", lambda **_kwargs: ("", "boom")
    )

    args = SimpleNamespace(reveal=False, indent=2)
    monkeypatch.setattr(
        "kapitan.inputs.base.cached.inv", {"target": {"parameters": {}}}
    )
    helm = Helm(str(compile_path), [], None, "target", args)
    config = KapitanInputTypeHelmConfig(
        input_paths=[],
        output_path=str(compile_path),
        helm_values={"key": "value"},
        kube_version="v1.30.0",
    )

    with pytest.raises(HelmTemplateError, match="boom"):
        helm.compile_file(config, "chart", str(compile_path))


def test_helm_render_chart_method_delegates(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(
        "kapitan.inputs.helm.render_chart",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs})
        or ("rendered", ""),
    )

    helm = Helm(
        str(tmp_path), [], None, "target", SimpleNamespace(reveal=False, indent=2)
    )
    output, error = helm.render_chart(
        "/tmp/chart",
        "-",
        "helm",
        {"name": "demo"},
        None,
        None,
    )

    assert (output, error) == ("rendered", "")
    assert captured["args"][0] == "/tmp/chart"


def test_render_chart_rejects_values_param():
    with pytest.raises(ValueError, match="helm 'values' flag is not supported"):
        render_chart(
            chart_dir="/tmp",
            output_path="/tmp",
            helm_path="helm",
            helm_params={"values": "bad"},
            helm_values_file=None,
            helm_values_files=None,
        )


def test_render_chart_builds_args_with_release_name_and_values_files(
    monkeypatch, tmp_path
):
    captured = {}

    def _helm_cli(_helm_path, args, **_kwargs):
        captured["args"] = args
        return ""

    monkeypatch.setattr("kapitan.inputs.helm.helm_cli", _helm_cli)

    output, error = render_chart(
        chart_dir="/tmp/chart",
        output_path=str(tmp_path),
        helm_path="helm",
        helm_params={"release_name": "legacy-name", "timeout": "5m"},
        helm_values_file="/tmp/one.yaml",
        helm_values_files=["/tmp/two.yaml", "/tmp/three.yaml"],
    )

    assert output == ""
    assert error == ""
    args = captured["args"]
    assert "--timeout" in args
    assert "5m" in args
    assert args.count("--values") == 3
    assert "legacy-name" in args


def test_render_chart_handles_name_template_and_false_bool_flag(monkeypatch):
    captured = {}

    def _helm_cli(_helm_path, args, stdout=None, **_kwargs):
        captured["args"] = args
        if stdout is not None:
            stdout.write("ok")
        return ""

    monkeypatch.setattr("kapitan.inputs.helm.helm_cli", _helm_cli)

    output, error = render_chart(
        chart_dir="/tmp/chart",
        output_path="-",
        helm_path="helm",
        helm_params={"name_template": "from-template", "include_crds": False},
        helm_values_file=None,
        helm_values_files=None,
    )

    assert output == "ok"
    assert error == ""
    args = captured["args"]
    assert "--include-crds" not in args
    assert "--generate-name" in args
    assert "from-template" in args


def test_render_chart_skips_generate_name_when_name_template_flag_present(monkeypatch):
    captured = {}

    def _helm_cli(_helm_path, args, stdout=None, **_kwargs):
        captured["args"] = args
        if stdout is not None:
            stdout.write("ok")
        return ""

    monkeypatch.setattr("kapitan.inputs.helm.helm_cli", _helm_cli)

    output, error = render_chart(
        chart_dir="/tmp/chart",
        output_path="-",
        helm_path="helm",
        helm_params={},
        helm_values_file=None,
        helm_values_files=None,
        helm_flags={"name_template": True},
    )

    assert output == "ok"
    assert error == ""
    assert "--generate-name" not in captured["args"]


def test_helmchart_load_chart_with_values_and_error_paths(monkeypatch):
    values_calls = []

    monkeypatch.setattr(
        "kapitan.inputs.helm.write_helm_values_file",
        lambda values: values_calls.append(values) or "/tmp/values.yaml",
    )
    monkeypatch.setattr(
        "kapitan.inputs.helm.render_chart",
        lambda *_args, **_kwargs: (
            "---\nkind: ConfigMap\nmetadata:\n  name: demo\n",
            "",
        ),
    )

    chart = HelmChart(
        chart_dir="/tmp/chart", helm_values={"replicas": 1}, helm_path="helm"
    )
    loaded = list(chart.load_chart())
    assert values_calls[0] == {"replicas": 1}
    assert loaded[0]["kind"] == "ConfigMap"

    monkeypatch.setattr(
        "kapitan.inputs.helm.render_chart",
        lambda *_args, **_kwargs: ("", "template failed"),
    )
    with pytest.raises(HelmTemplateError, match="template failed"):
        list(chart.load_chart())


def test_helmchart_load_chart_without_values_skips_values_file(monkeypatch):
    monkeypatch.setattr(
        "kapitan.inputs.helm.write_helm_values_file",
        lambda _values: (_ for _ in ()).throw(
            AssertionError("values file should not be written")
        ),
    )
    monkeypatch.setattr(
        "kapitan.inputs.helm.render_chart",
        lambda *_args, **_kwargs: (
            "---\nkind: Service\nmetadata:\n  name: demo\n",
            "",
        ),
    )

    chart = HelmChart(chart_dir="/tmp/chart", helm_values={}, helm_path="helm")
    loaded = list(chart.load_chart())

    assert loaded[0]["kind"] == "Service"
