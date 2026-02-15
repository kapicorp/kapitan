# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import ast
import base64
import tempfile
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


def test_sha256():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|sha256 }}")
        f.seek(0)
        context = {"text": "this and that"}
        output = "e863c1ac42619a2b429a08775a6acd89ff4c2c6b8dae12e3461a5fa63b2f92f5"
        assert render_jinja2_file(f.name, context) == output


def test_base64_encode():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|b64encode }}")
        f.seek(0)
        context = {"text": "this and that"}
        output = "dGhpcyBhbmQgdGhhdA=="
        assert render_jinja2_file(f.name, context) == output


def test_base64_decode():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|b64decode }}")
        f.seek(0)
        context = {"text": "dGhpcyBhbmQgdGhhdA=="}
        output = "this and that"
        assert render_jinja2_file(f.name, context) == output


def test_toml():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|toml }}")
        f.seek(0)
        context = {"text": {"foo": ["this", "that"]}}
        output = 'foo = [ "this", "that",]\n'
        assert render_jinja2_file(f.name, context) == output


def test_yaml():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|yaml }}")
        f.seek(0)
        context = {"text": ["this", "that"]}
        output = "- this\n- that\n"
        assert render_jinja2_file(f.name, context) == output


def test_fileglob():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|fileglob }}")
        f.seek(0)
        tests_dir = Path(__file__).resolve().parent
        context = {"text": str(tests_dir / "*jinja2.py")}
        output = render_jinja2_file(f.name, context)
        expected = sorted(str(path) for path in tests_dir.glob("*jinja2.py"))
        assert sorted(ast.literal_eval(output)) == expected


def test_bool():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|bool }}")
        f.seek(0)
        context = {"text": "yes"}
        output = "True"
        assert render_jinja2_file(f.name, context) == output


def test_to_datetime():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|to_datetime }}")
        f.seek(0)
        context = {"text": "2019-03-07 13:37:00"}
        output = "2019-03-07 13:37:00"
        assert render_jinja2_file(f.name, context) == output


def test_strftime():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|strftime }}")
        f.seek(0)
        format = "%a, %d %b %Y %H:%M"
        context = {"text": format}
        output = time.strftime(format)
        assert render_jinja2_file(f.name, context) == output


def test_regex_replace():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|regex_replace(pattern='world', replacement='kapitan') }}")
        f.seek(0)
        context = {"text": "hello world"}
        output = "hello kapitan"
        assert render_jinja2_file(f.name, context) == output


def test_regex_escape():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|regex_escape }}")
        f.seek(0)
        context = {"text": "+s[a-z].*"}
        output = "\\+s\\[a\\-z\\]\\.\\*"
        assert render_jinja2_file(f.name, context) == output


def test_regex_search():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|regex_search('world.*') }}")
        f.seek(0)
        context = {"text": "hello world"}
        output = "world"
        assert render_jinja2_file(f.name, context) == output


def test_regex_findall():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|regex_findall('world.*') }}")
        f.seek(0)
        context = {"text": "hello world"}
        output = "['world']"
        assert render_jinja2_file(f.name, context) == output


def test_ternary():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|ternary('yes', 'no') }}")
        f.seek(0)
        context = {"text": "kapitan == kapitan"}
        output = "yes"
        assert render_jinja2_file(f.name, context) == output


def test_shuffle():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ text|shuffle }}")
        f.seek(0)
        array = [1, 2, 3, 4, 5]
        context = {"text": array}
        assert render_jinja2_file(f.name, context) != array


def test_reveal_maybe_b64encode_tag(tmp_path):
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ my_ref_tag_var|reveal_maybe|b64encode }}")
        f.seek(0)

        cached.args = argparse.Namespace(reveal=True, refs_path=str(tmp_path))
        cached.ref_controller_obj = RefController(cached.args.refs_path)
        cached.revealer_obj = Revealer(cached.ref_controller_obj)

        ref_tag = "?{base64:some_value}"
        ref_value = b"sitar_rock!"
        cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
        context = {"my_ref_tag_var": ref_tag}
        ref_value_b64 = base64.b64encode(ref_value).decode()
        assert render_jinja2_file(f.name, context) == ref_value_b64


def test_reveal_maybe_tag_no_reveal_flag(tmp_path):
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ my_ref_tag_var|reveal_maybe }}")
        f.seek(0)

        cached.args = argparse.Namespace(reveal=False, refs_path=str(tmp_path))
        cached.ref_controller_obj = RefController(cached.args.refs_path)
        cached.revealer_obj = Revealer(cached.ref_controller_obj)

        ref_tag = "?{base64:some_value}"
        ref_value = b"sitar_rock!"
        cached.ref_controller_obj[ref_tag] = Base64Ref(ref_value)
        context = {"my_ref_tag_var": ref_tag}
        assert render_jinja2_file(f.name, context) == "?{base64:some_value}"


def test_reveal_maybe_no_tag(tmp_path):
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ my_var|reveal_maybe }}")
        f.seek(0)

        cached.args = argparse.Namespace(reveal=True, refs_path=str(tmp_path))
        cached.ref_controller_obj = RefController(cached.args.refs_path)
        cached.revealer_obj = Revealer(cached.ref_controller_obj)

        var_value = "heavy_rock!"
        context = {"my_var": var_value}
        assert render_jinja2_file(f.name, context) == var_value


def test_inventory_context():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ inventory.parameters.cluster.name }}")
        cluster_name = "minikube"
        target_name = "minikube-es"
        kubernetes_dir = REPO_ROOT / "examples/kubernetes"
        inv = inventory([str(kubernetes_dir)], target_name, inventory_path="inventory/")
        context = {"inventory": inv}
        f.seek(0)
        assert render_jinja2_file(f.name, context) == cluster_name


def test_inventory_global_context():
    with tempfile.NamedTemporaryFile() as f:
        target_name = "minikube-es"
        f.write(
            b'{{ inventory_global["%s"].parameters.cluster.name }}'
            % target_name.encode("UTF-8")
        )
        cluster_name = "minikube"
        kubernetes_dir = REPO_ROOT / "examples/kubernetes"
        inv_global = inventory([str(kubernetes_dir)], None, inventory_path="inventory/")
        context = {"inventory_global": inv_global}
        f.seek(0)
        assert render_jinja2_file(f.name, context) == cluster_name


def test_custom_filter_jinja2():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"{{ inventory.parameters.cluster.name | custom_jinja2_filter }}")
        cluster_name = "minikube"
        target_name = "minikube-es"
        kubernetes_dir = REPO_ROOT / "examples/kubernetes"
        inv = inventory([str(kubernetes_dir)], target_name, inventory_path="inventory/")
        context = {"inventory": inv}
        f.seek(0)
        filter_path = kubernetes_dir / "lib/custom_jinja2_filter.py"
        actual_output = render_jinja2_file(f.name, context, str(filter_path))
        expected_output = base64_encode(cluster_name)
        assert actual_output == expected_output
