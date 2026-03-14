# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from kapitan.errors import CompileError
from kapitan.utils.hashing import sha256_string
from kapitan.utils.jinja import (
    render_jinja2,
    render_jinja2_file,
    render_jinja2_template,
)


def test_render_jinja2_template_and_hash_cache():
    assert (
        render_jinja2_template.__wrapped__("hello {{ name }}", {"name": "kapitan"})
        == "hello kapitan"
    )
    assert sha256_string("kapitan") == sha256_string("kapitan")


def test_render_jinja2_directory_ignores_hidden(tmp_path):
    template = tmp_path / "template.txt"
    template.write_text("hi {{ who }}", encoding="utf-8")
    hidden = tmp_path / ".ignored"
    hidden.write_text("ignore", encoding="utf-8")

    rendered = render_jinja2(str(tmp_path), {"who": "there"})
    assert list(rendered) == ["template.txt"]
    assert rendered["template.txt"]["content"] == "hi there"


def test_render_jinja2_file_error_has_line_info(tmp_path):
    template = tmp_path / "template.txt"
    template.write_text("hi {{ missing }}", encoding="utf-8")
    with pytest.raises(CompileError):
        render_jinja2_file(str(template), {})


def test_render_jinja2_wraps_directory_render_errors(tmp_path):
    bad_template = tmp_path / "broken.j2"
    bad_template.write_text("hello {{ missing }}", encoding="utf-8")

    with pytest.raises(CompileError, match="failed to render"):
        render_jinja2(str(tmp_path), {})
