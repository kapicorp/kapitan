# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import ast
import base64
import time
from pathlib import Path

import pytest

from kapitan import cached
from kapitan.jinja2_filters import base64_encode
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan.resources import inventory
from kapitan.utils import render_jinja2_file


pytestmark = pytest.mark.usefixtures("reset_cached_args")
REPO_ROOT = Path(__file__).resolve().parents[2]


def _render_template(
    tmp_path: Path,
    template: str,
    context: dict,
    *,
    filter_path: str | None = None,
) -> str:
    template_path = tmp_path / "template.j2"
    template_path.write_text(template, encoding="utf-8")
    if filter_path is None:
        return render_jinja2_file(str(template_path), context)
    return render_jinja2_file(str(template_path), context, filter_path)


def test_sha256(tmp_path):
    context = {"text": "this and that"}
    output = "e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5"
    assert _render_template(tmp_path, "{{ text|sha256 }}", context) == output


def test_base64_encode(tmp_path):
    context = {"text": "this and that"}
    output = "dGhpcyBhbmQgdGhhdA=="
    assert _render_template(tmp_path, "{{ text|b64encode }}", context) == output


def test_base64_decode(tmp_path):
    context = {"text": "dGhpcyBhbmQgdGhhdA=="}
    output = "this and that"
    assert _render_template(tmp_path, "{{ text|b64decode }}", context) == output


def test_toml(tmp_path):
    context = {"text": {"foo": ["this", "that"]}}
    output = 'foo = [ "this", "that",]\n'
    assert _render_template(tmp_path, "{{ text|toml }}", context) == output


def test_yaml(tmp_path):
    context = {"text": ["this", "that"]}
    output = "- this\n- that\n"
    assert _render_template(tmp_path, "{{ text|yaml }}", context) == output


def test_fileglob(tmp_path):
    tests_dir = Path(__file__).resolve().parent
    context = {"text": str(tests_dir / "*jinja2.py")}
    output = _render_template(tmp_path, "{{ text|fileglob }}", context)
    expected = sorted(str(path) for path in tests_dir.glob("*jinja2.py"))
    assert sorted(ast.literal_eval(output)) == expected


def test_bool(tmp_path):
    context = {"text": "yes"}
    output = "True"
    assert _render_template(tmp_path, "{{ text|bool }}", context) == output


def test_to_datetime(tmp_path):
    context = {"text": "2019-03-07 13:37:00"}
    output = "2019-03-07 13:37:00"
    assert _render_template(tmp_path, "{{ text|to_datetime }}", context) == output


def test_strftime(tmp_path):
    format = "%a, %d %b %Y %H:%M"
    context = {"text": format}
    output = time.strftime(format)
    assert _render_template(tmp_path, "{{ text|strftime }}", context) == output


def test_regex_replace(tmp_path):
    context = {"text": "hello world"}
    output = "hello kapitan"
    assert (
        _render_template(
            tmp_path,
            "{{ text|regex_replace(pattern='world', replacement='kapitan') }}",
            context,
        )
        == output
    )


def test_regex_escape(tmp_path):
    context = {"text": "+s[a-z].*"}
    output = "\\+s\\[a\\-z\\]\\.\\*"
    assert _render_template(tmp_path, "{{ text|regex_escape }}", context) == output


def test_regex_search(tmp_path):
    context = {"text": "hello world"}
    output = "world"
    assert (
        _render_template(tmp_path, "{{ text|regex_search('world.*') }}", context)
        == output
    )


def test_regex_findall(tmp_path):
    context = {"text": "hello world"}
    output = "['world']"
    assert (
        _render_template(tmp_path, "{{ text|regex_findall('world.*') }}", context)
        == output
    )


def test_ternary(tmp_path):
    context = {"text": "kapitan == kapitan"}
    output = "yes"
    assert (
        _render_template(tmp_path, "{{ text|ternary('yes', 'no') }}", context) == output
    )


def test_shuffle(tmp_path):
    array = [1, 2, 3, 4, 5]
    context = {"text": array}
    assert _render_template(tmp_path, "{{ text|shuffle }}", context) != array


def test_reveal_maybe_b64encode_tag(tmp_path):
    cached.args = argparse.Namespace(reveal=True, refs_path=str(tmp_path))
    cached.ref_controller_obj = RefController(cached.args.refs_path)
    cached.revealer_obj = Revealer(cached.ref_controller_obj)

    ref_tag = "?{base64:some_value}"
    ref_value = b"sitar_rock!"
    cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
    context = {"my_ref_tag_var": ref_tag}
    ref_value_b64 = base64.b64encode(ref_value).decode()
    assert (
        _render_template(
            tmp_path, "{{ my_ref_tag_var|reveal_maybe|b64encode }}", context
        )
        == ref_value_b64
    )


def test_reveal_maybe_tag_no_reveal_flag(tmp_path):
    cached.args = argparse.Namespace(reveal=False, refs_path=str(tmp_path))
    cached.ref_controller_obj = RefController(cached.args.refs_path)
    cached.revealer_obj = Revealer(cached.ref_controller_obj)

    ref_tag = "?{base64:some_value}"
    ref_value = b"sitar_rock!"
    cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
    context = {"my_ref_tag_var": ref_tag}
    assert (
        _render_template(tmp_path, "{{ my_ref_tag_var|reveal_maybe }}", context)
        == "?{base64:some_value}"
    )


def test_reveal_maybe_no_tag(tmp_path):
    cached.args = argparse.Namespace(reveal=True, refs_path=str(tmp_path))
    cached.ref_controller_obj = RefController(cached.args.refs_path)
    cached.revealer_obj = Revealer(cached.ref_controller_obj)

    var_value = "heavy_rock!"
    context = {"my_var": var_value}
    assert _render_template(tmp_path, "{{ my_var|reveal_maybe }}", context) == var_value


def test_inventory_context(tmp_path):
    cluster_name = "minikube"
    target_name = "minikube-es"
    kubernetes_dir = REPO_ROOT / "examples/kubernetes"
    inv = inventory([str(kubernetes_dir)], target_name, inventory_path="inventory/")
    context = {"inventory": inv}
    assert (
        _render_template(tmp_path, "{{ inventory.parameters.cluster.name }}", context)
        == cluster_name
    )


def test_inventory_global_context(tmp_path):
    target_name = "minikube-es"
    cluster_name = "minikube"
    kubernetes_dir = REPO_ROOT / "examples/kubernetes"
    inv_global = inventory([str(kubernetes_dir)], None, inventory_path="inventory/")
    context = {"inventory_global": inv_global}
    template = f'{{{{ inventory_global["{target_name}"].parameters.cluster.name }}}}'
    assert _render_template(tmp_path, template, context) == cluster_name


def test_custom_filter_jinja2(tmp_path):
    cluster_name = "minikube"
    target_name = "minikube-es"
    kubernetes_dir = REPO_ROOT / "examples/kubernetes"
    inv = inventory([str(kubernetes_dir)], target_name, inventory_path="inventory/")
    context = {"inventory": inv}
    filter_path = kubernetes_dir / "lib/custom_jinja2_filter.py"
    actual_output = _render_template(
        tmp_path,
        "{{ inventory.parameters.cluster.name | custom_jinja2_filter }}",
        context,
        filter_path=str(filter_path),
    )
    expected_output = base64_encode(cluster_name)
    assert actual_output == expected_output
