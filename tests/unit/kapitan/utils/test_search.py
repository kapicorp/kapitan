# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from types import SimpleNamespace

from kapitan.utils.search import search_target_token_paths, searchvar


def test_search_target_token_paths(tmp_path):
    refs_path = tmp_path / "refs"
    target_dir = refs_path / "target-a"
    target_dir.mkdir(parents=True)
    secret_file = target_dir / "secret.yaml"
    secret_file.write_text("type: base64\n", encoding="utf-8")

    results = search_target_token_paths(str(refs_path), {"target-a"})
    assert results == {"target-a": ["?{base64:target-a/secret.yaml}"]}


def test_searchvar_pretty_print_and_target_secret_fallback(tmp_path, capsys):
    inventory_file = tmp_path / "class.yml"
    inventory_file.write_text("foo:\n  bar: baz\n", encoding="utf-8")

    args = SimpleNamespace(
        searchvar="foo.bar",
        inventory_path=str(tmp_path),
        pretty_print=True,
    )
    searchvar(args)
    stdout = capsys.readouterr().out
    assert str(inventory_file) in stdout
    assert "baz" in stdout

    refs_dir = tmp_path / "refs"
    target_dir = refs_dir / "target-a"
    target_dir.mkdir(parents=True)
    (target_dir / "secret.yml").write_text("value: hello\n", encoding="utf-8")
    target_paths = search_target_token_paths(str(refs_dir), {"target-a"})
    assert target_paths == {"target-a": ["?{gpg:target-a/secret.yml}"]}
