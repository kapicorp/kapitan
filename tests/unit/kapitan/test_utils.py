# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import builtins
import glob
import importlib.util
import io
import os
import stat
import sys
import tarfile
import types
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.errors import CompileError
from kapitan.inventory import InventoryBackends
from kapitan.utils import (
    SafeCopyError,
    compare_versions,
    copy_tree,
    deep_get,
    dictionary_hash,
    directory_hash,
    dot_kapitan_config,
    filetype,
    flatten_dict,
    force_copy_file,
    from_dot_kapitan,
    make_request,
    multiline_str_presenter,
    normalise_join_path,
    null_presenter,
    prune_empty,
    render_jinja2,
    render_jinja2_file,
    render_jinja2_template,
    safe_copy_file,
    safe_copy_tree,
    search_target_token_paths,
    searchvar,
    sha256_string,
    unpack_downloaded_file,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_KUBERNETES_PATH = REPO_ROOT / "examples/kubernetes"


def test_copy_tree_copies_directory_and_preserves_content_hash(tmp_path):
    """Test copy tree copies directory and preserves content hash.

    Exercises `kapitan/utils.py` for the "copy tree copies directory and
    preserves content hash" path using temporary filesystem fixtures, then
    validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    original = set(glob.iglob(f"{TEST_KUBERNETES_PATH}/*", recursive=True))
    copied = copy_tree(str(TEST_KUBERNETES_PATH), str(tmp_path))
    assert len(copied) == len(original)

    original_hash = directory_hash(str(TEST_KUBERNETES_PATH))
    copied_hash = directory_hash(str(tmp_path))
    assert copied_hash == original_hash


def test_validate_copy_dir(tmp_path):
    """Test validate copy dir.

    Exercises `kapitan/utils.py` for the "validate copy dir" path using
    temporary filesystem fixtures, then validates the expected error-handling
    contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    with pytest.raises(SafeCopyError):
        copy_tree("non_existent_dir", str(tmp_path))

    dst = tmp_path / "test"
    dst.write_text("Hello\n", encoding="utf-8")
    with pytest.raises(SafeCopyError):
        copy_tree(str(TEST_KUBERNETES_PATH), str(dst))


def test_copy_dir_missing_dst(tmp_path):
    """Test copy dir missing dst.

    Exercises `kapitan/utils.py` for the "copy dir missing dst" path using
    temporary filesystem fixtures, then validates the expected result/output
    contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    dst = tmp_path / "subdir"
    original = set(glob.iglob(f"{TEST_KUBERNETES_PATH}/*", recursive=True))
    copied = copy_tree(str(TEST_KUBERNETES_PATH), str(dst))
    assert len(copied) == len(original)

    original_hash = directory_hash(str(TEST_KUBERNETES_PATH))
    copied_hash = directory_hash(str(dst))
    assert copied_hash == original_hash


def test_copy_dir_overwrite_readonly_file(tmp_path):
    """Test copy dir overwrite readonly file.

    Exercises `kapitan/utils.py` for the "copy dir overwrite readonly file" path
    using temporary filesystem fixtures, then validates the expected error-
    handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    src = tmp_path / "source"
    src.mkdir()
    f = src / "ro.txt"
    f.write_text("Hello!\n", encoding="utf-8")
    os.chmod(f, 0o444)

    dst = tmp_path / "dest"
    copied = copy_tree(str(src), str(dst))
    assert copied == [str(dst / "ro.txt")]
    assert stat.S_IMODE(os.stat(copied[0]).st_mode) == 0o444

    with pytest.raises(Exception):
        copy_tree(str(src), str(dst))

    copied2 = copy_tree(str(src), str(dst), clobber_files=True)
    assert copied2 == []
    assert stat.S_IMODE(os.stat(copied[0]).st_mode) == 0o444


def test_force_copy_file(tmp_path):
    """Test force copy file.

    Exercises `kapitan/utils.py` for the "force copy file" path using temporary
    filesystem fixtures, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    src = tmp_path / "test.txt"
    src.write_text("Test\n", encoding="utf-8")

    dst1 = tmp_path / "path"
    dst1.mkdir()
    force_copy_file(str(src), str(dst1))
    assert os.path.isfile(dst1 / "test.txt")

    dst2 = tmp_path / "test2.txt"
    assert not dst2.exists()
    force_copy_file(str(src), str(dst2))
    assert dst2.is_file()

    os.chmod(dst2, 0o444)
    src.write_text("Test2\n", encoding="utf-8")
    force_copy_file(str(src), str(dst2))
    assert dst2.is_file()
    assert dst2.read_text(encoding="utf-8") == "Test2\n"


def test_normalise_join_path():
    """Test normalise join path.

    Exercises `kapitan/utils.py` for the "normalise join path" path, then
    validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    assert normalise_join_path("root", "child") == os.path.join("root", "child")
    assert normalise_join_path("/root", "/child") == "/child"


def test_flatten_dict_and_deep_get():
    """Test flatten dict and deep get.

    Exercises `kapitan/utils.py` for the "flatten dict and deep get" path, then
    validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    nested = {"a": {"b": {"c": 1}}, "x": 2}
    flattened = flatten_dict(nested)
    assert flattened == {"a.b.c": 1, "x": 2}
    assert deep_get(nested, ["a", "b", "c"]) == 1


def test_search_target_token_paths(tmp_path):
    """Test search target token paths.

    Exercises `kapitan/utils.py` for the "search target token paths" path using
    temporary filesystem fixtures, then validates the expected result/output
    contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    refs_path = tmp_path / "refs"
    target_dir = refs_path / "target-a"
    target_dir.mkdir(parents=True)
    secret_file = target_dir / "secret.yaml"
    secret_file.write_text("type: base64\n", encoding="utf-8")

    results = search_target_token_paths(str(refs_path), {"target-a"})
    assert results == {"target-a": ["?{base64:target-a/secret.yaml}"]}


@pytest.mark.parametrize(
    ("dot_kapitan_version", "current_version", "expected"),
    [
        ("0.22.0", "0.22.0", "equal"),
        ("0.22.0-rc.1", "0.22.0-rc.1", "equal"),
        ("0.22", "0.22.1", "equal"),
        ("0.22", "0.22.1-rc.1", "equal"),
        ("0.22.1", "0.22.0", "greater"),
        ("0.22.0", "0.22.0-rc.1", "greater"),
        ("0.22.1-rc.1", "0.22.0-rc.1", "greater"),
        ("0.23.0-rc.1", "0.22.0-rc.1", "greater"),
        ("0.22.0", "0.22.1", "lower"),
        ("0.22.0-rc.1", "0.22.0", "lower"),
        ("0.22.0-rc.1", "0.22.1-rc.1", "lower"),
        ("0.22.0-rc.1", "0.23.0-rc.1", "lower"),
    ],
)
def test_compare_versions(dot_kapitan_version, current_version, expected):
    """Test compare versions.

    Exercises `kapitan/utils.py` for the "compare versions" path, then validates
    the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    assert compare_versions(dot_kapitan_version, current_version) == expected


def _write_dot_kapitan(base_path, config):
    dot_path = os.path.join(base_path, ".kapitan")
    with open(dot_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle)


@pytest.fixture
def in_temp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    reset_cache()


def test_from_dot_kapitan_returns_fallback_when_file_is_missing(in_temp_dir):
    """Test from dot kapitan returns fallback when file is missing.

    Exercises `kapitan/utils.py` for the "from dot kapitan returns fallback when
    file is missing" path, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    assert (
        from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./some/fallback"
    )


def test_from_dot_kapitan_returns_fallback_when_option_is_missing(in_temp_dir):
    """Test from dot kapitan returns fallback when option is missing.

    Exercises `kapitan/utils.py` for the "from dot kapitan returns fallback when
    option is missing" path, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
        == "./some/fallback"
    )


def test_from_dot_kapitan_prefers_command_specific_option(in_temp_dir):
    """Test from dot kapitan prefers command specific option.

    Exercises `kapitan/utils.py` for the "from dot kapitan prefers command
    specific option" path, then validates the expected routing and dispatch
    contract.

    It targets shared filesystem/network/version helper utilities. This protects
    user-facing routing behavior so commands and aliases continue to invoke the
    correct code paths.
    """
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-backend": str(InventoryBackends.RECLASS)},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./path/to/inv"
    )


def test_global_option(in_temp_dir):
    """Test global option.

    Exercises `kapitan/utils.py` for the "global option" path, then validates
    the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-path": "./some/path"},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        from_dot_kapitan("inventory", "inventory-path", "./some/fallback")
        == "./some/path"
    )


def test_command_over_global_option(in_temp_dir):
    """Test command over global option.

    Exercises `kapitan/utils.py` for the "command over global option" path, then
    validates the expected routing and dispatch contract.

    It targets shared filesystem/network/version helper utilities. This protects
    user-facing routing behavior so commands and aliases continue to invoke the
    correct code paths.
    """
    _write_dot_kapitan(
        in_temp_dir,
        {
            "global": {"inventory-path": "./some/path"},
            "compile": {"inventory-path": "./path/to/inv"},
        },
    )
    assert (
        from_dot_kapitan("compile", "inventory-path", "./some/fallback")
        == "./path/to/inv"
    )


def test_prune_empty_removes_empty_containers():
    """Test prune empty removes empty containers.

    Exercises `kapitan/utils.py` for the "prune empty removes empty containers"
    path, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    data = {"a": [], "b": {"c": []}, "d": [1, {}, []], "e": 2}
    assert prune_empty(data) == {"b": {}, "d": [1], "e": 2}
    assert prune_empty([]) is None


def test_deep_get_glob_match():
    """Test deep get glob match.

    Exercises `kapitan/utils.py` for the "deep get glob match" path, then
    validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    data = {"FooBar": {"baz": 3}}
    assert deep_get(data, ["*bar", "baz"]) == 3


def test_render_jinja2_template_and_hash_cache():
    """Test render Jinja2 template and hash cache.

    Exercises `kapitan/utils.py` for the "render jinja2 template and hash cache"
    path, then validates the expected state-transition contract.

    It targets shared filesystem/network/version helper utilities. This protects
    cache/state semantics so repeated operations remain deterministic and safe.
    """
    assert (
        render_jinja2_template.__wrapped__("hello {{ name }}", {"name": "kapitan"})
        == "hello kapitan"
    )
    assert sha256_string("kapitan") == sha256_string("kapitan")


def test_render_jinja2_directory_ignores_hidden(tmp_path):
    """Test render Jinja2 directory ignores hidden.

    Exercises `kapitan/utils.py` for the "render jinja2 directory ignores
    hidden" path using temporary filesystem fixtures, then validates the
    expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    template = tmp_path / "template.txt"
    template.write_text("hi {{ who }}", encoding="utf-8")
    hidden = tmp_path / ".ignored"
    hidden.write_text("ignore", encoding="utf-8")

    rendered = render_jinja2(str(tmp_path), {"who": "there"})
    assert list(rendered) == ["template.txt"]
    assert rendered["template.txt"]["content"] == "hi there"


def test_render_jinja2_file_error_has_line_info(tmp_path):
    """Test render Jinja2 file error has line info.

    Exercises `kapitan/utils.py` for the "render jinja2 file error has line
    info" path using temporary filesystem fixtures, then validates the expected
    error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    template = tmp_path / "template.txt"
    template.write_text("hi {{ missing }}", encoding="utf-8")
    with pytest.raises(CompileError):
        render_jinja2_file(str(template), {})


def test_safe_copy_file_and_tree(tmp_path):
    """Test safe copy file and tree.

    Exercises `kapitan/utils.py` for the "safe copy file and tree" path using
    temporary filesystem fixtures, then validates the expected result/output
    contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("data", encoding="utf-8")
    (src / ".hidden").write_text("secret", encoding="utf-8")

    dst = tmp_path / "dst"
    dst.mkdir()
    existing = dst / "file.txt"
    existing.write_text("old", encoding="utf-8")

    copied_path, copied = safe_copy_file(str(src / "file.txt"), str(dst))
    assert copied_path == str(existing)
    assert copied == 0
    assert existing.read_text(encoding="utf-8") == "old"

    outputs = safe_copy_tree(str(src), str(dst))
    assert str(dst / "file.txt") not in outputs
    assert (dst / ".hidden").exists() is False


def test_compare_versions_and_check_version(monkeypatch, tmp_path, capsys):
    """Test compare versions and check version.

    Exercises `kapitan/utils.py` for the "compare versions and check version"
    path using temporary filesystem fixtures, mocked dependency boundaries and
    captured CLI/output streams, then validates the expected error-handling
    contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    assert compare_versions("1.2.3", "1.2.3") == "equal"
    assert compare_versions("1.2.4", "1.2.3") == "greater"
    assert compare_versions("1.2.3", "1.2.4") == "lower"
    assert compare_versions("1.2.3-rc1", "1.2.3") == "greater"

    kapitan_config = tmp_path / ".kapitan"
    kapitan_config.write_text("version: 1.0.0\n", encoding="utf-8")
    cached.dot_kapitan = None
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kapitan.utils.VERSION", "2.0.0")

    with pytest.raises(SystemExit) as excinfo:
        from kapitan.utils import check_version

        check_version()

    assert excinfo.value.code == 1
    assert "Current version" in capsys.readouterr().out
    cached.dot_kapitan = None


def test_multiline_and_null_presenter_helpers(monkeypatch):
    """Test multiline and null presenter helpers.

    Exercises `kapitan/utils.py` for the "multiline and null presenter helpers"
    path using mocked dependency boundaries, then validates the expected
    result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """

    class _DummyDumper:
        def represent_scalar(self, tag, data, style=None):
            return {"tag": tag, "data": data, "style": style}

    dumper = _DummyDumper()
    multiline_result = multiline_str_presenter(dumper, "line1\nline2", "literal")
    assert multiline_result["style"] == "|"

    monkeypatch.setattr(cached, "args", SimpleNamespace(yaml_dump_null_as_empty=True))
    empty_null = null_presenter(dumper, None)
    assert empty_null["data"] == ""

    monkeypatch.setattr(cached, "args", SimpleNamespace(yaml_dump_null_as_empty=False))
    default_null = null_presenter(dumper, None)
    assert default_null["data"] == "null"


def test_deep_get_additional_edge_paths():
    """Test deep get additional edge paths.

    Exercises `kapitan/utils.py` for the "deep get additional edge paths" path,
    then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    assert deep_get({"a": 1}, ["a", "b"]) is None
    assert deep_get({"FooBar": 9}, ["*bar"]) == 9
    assert deep_get({"foo": 1}, ["*bar"]) is None
    assert deep_get({"outer": {"inner": {"needle": "value"}}}, ["needle"]) == "value"
    assert deep_get({"a": 1}, []) is None


def test_searchvar_pretty_print_and_target_secret_fallback(tmp_path, capsys):
    """Test searchvar pretty print and target secret fallback.

    Exercises `kapitan/utils.py` for the "searchvar pretty print and target
    secret fallback" path using temporary filesystem fixtures and captured
    CLI/output streams, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
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


def test_directory_hash_covers_error_and_binary_paths(tmp_path, monkeypatch):
    """Test directory hash covers error and binary paths.

    Exercises `kapitan/utils.py` for the "directory hash covers error and binary
    paths" path using temporary filesystem fixtures and mocked dependency
    boundaries, then validates the expected error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    with pytest.raises(OSError):
        from kapitan.utils import directory_hash

        directory_hash(str(tmp_path / "missing"))

    plain_file = tmp_path / "file.txt"
    plain_file.write_text("value", encoding="utf-8")
    with pytest.raises(OSError):
        from kapitan.utils import directory_hash

        directory_hash(str(plain_file))

    binary_dir = tmp_path / "binary"
    binary_dir.mkdir()
    (binary_dir / "payload.bin").write_bytes(b"\xff\xfe\xfd")
    from kapitan.utils import directory_hash

    digest = directory_hash(str(binary_dir))
    assert len(digest) == 64

    error_dir = tmp_path / "error"
    error_dir.mkdir()
    blocked_file = error_dir / "blocked.txt"
    blocked_file.write_text("data", encoding="utf-8")
    original_open = builtins.open

    def _raising_open(path, *args, **kwargs):
        if str(path).endswith("blocked.txt"):
            raise PermissionError("blocked")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _raising_open)
    with pytest.raises(CompileError):
        directory_hash(str(error_dir))


def test_dictionary_hash_and_dot_kapitan_cached_short_circuit(monkeypatch):
    """Test dictionary hash and dot kapitan cached short circuit.

    Exercises `kapitan/utils.py` for the "dictionary hash and dot kapitan cached
    short circuit" path using mocked dependency boundaries, then validates the
    expected state-transition contract.

    It targets shared filesystem/network/version helper utilities. This protects
    cache/state semantics so repeated operations remain deterministic and safe.
    """
    assert dictionary_hash({"a": 1, "b": 2}) == dictionary_hash({"b": 2, "a": 1})

    cached.dot_kapitan = {"cached": True}

    def _should_not_be_called(_path):
        raise AssertionError("filesystem check should be skipped when cache is set")

    monkeypatch.setattr("kapitan.utils.os.path.exists", _should_not_be_called)
    assert dot_kapitan_config() == {"cached": True}
    cached.dot_kapitan = None


def test_check_version_equal_greater_and_missing_version(monkeypatch, capsys):
    """Test check version equal greater and missing version.

    Exercises `kapitan/utils.py` for the "check version equal greater and
    missing version" path using mocked dependency boundaries and captured
    CLI/output streams, then validates the expected error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    from kapitan import utils

    monkeypatch.setattr(utils, "dot_kapitan_config", lambda: {"version": "1.2.3"})
    monkeypatch.setattr(utils, "VERSION", "1.2.3")
    assert utils.check_version() is None

    monkeypatch.setattr(utils, "dot_kapitan_config", lambda: {"version": "2.0.0"})
    monkeypatch.setattr(utils, "VERSION", "1.0.0")
    with pytest.raises(SystemExit) as excinfo:
        utils.check_version()
    assert excinfo.value.code == 1
    assert "Upgrade kapitan to '2.0.0'" in capsys.readouterr().out

    monkeypatch.setattr(utils, "dot_kapitan_config", dict)
    assert utils.check_version() is None


def test_make_request_non_raising_error_response(monkeypatch):
    """Test make request non raising error response.

    Exercises `kapitan/utils.py` for the "make request non raising error
    response" path using mocked dependency boundaries, then validates the
    expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """

    class _Response:
        ok = False
        content = b""
        headers = {"Content-Type": "application/octet-stream"}

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr("kapitan.utils.requests.get", lambda _url: _Response())
    assert make_request("https://example.test") == (None, None)


def test_unpack_downloaded_file_detects_zip_and_rejects_plain_gzip(
    tmp_path, monkeypatch
):
    """Test unpack downloaded file detects zip and rejects plain gzip.

    Exercises `kapitan/utils.py` for the "unpack downloaded file detects zip and
    rejects plain gzip" path using temporary filesystem fixtures and mocked
    dependency boundaries, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    archive = tmp_path / "payload.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("file.txt", "hello")

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    class _ZipKind:
        mime = "application/zip"

    monkeypatch.setattr(filetype, "guess", lambda _path: _ZipKind())
    assert unpack_downloaded_file(str(archive), str(output_dir), None) is True
    assert (output_dir / "file.txt").read_text(encoding="utf-8") == "hello"

    fake_gzip = tmp_path / "payload.gz"
    fake_gzip.write_bytes(b"not a tar archive")
    assert (
        unpack_downloaded_file(str(fake_gzip), str(output_dir), "application/gzip")
        is False
    )


def test_safe_copy_helpers_cover_error_paths(tmp_path, monkeypatch):
    """Test safe copy helpers cover error paths.

    Exercises `kapitan/utils.py` for the "safe copy helpers cover error paths"
    path using temporary filesystem fixtures and mocked dependency boundaries,
    then validates the expected error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    with pytest.raises(SafeCopyError):
        safe_copy_file(str(tmp_path / "missing.txt"), str(tmp_path / "dest.txt"))

    not_dir = tmp_path / "not_dir.txt"
    not_dir.write_text("data", encoding="utf-8")
    with pytest.raises(SafeCopyError):
        safe_copy_tree(str(not_dir), str(tmp_path / "dst"))

    src_dir = tmp_path / "src"
    src_dir.mkdir()

    monkeypatch.setattr(
        "kapitan.utils.os.listdir",
        lambda _src: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(SafeCopyError):
        safe_copy_tree(str(src_dir), str(tmp_path / "dst2"))

    monkeypatch.setattr("kapitan.utils.os.listdir", lambda _src: [])
    monkeypatch.setattr(
        "kapitan.utils.os.makedirs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    assert safe_copy_tree(str(src_dir), str(tmp_path / "dst3")) == []


def test_render_jinja2_wraps_directory_render_errors(tmp_path):
    """Test render jinja2 wraps directory render errors.

    Exercises `kapitan/utils.py` for the "render jinja2 wraps directory render
    errors" path using temporary filesystem fixtures, then validates the expected
    error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    bad_template = tmp_path / "broken.j2"
    bad_template.write_text("hello {{ missing }}", encoding="utf-8")

    with pytest.raises(CompileError, match="failed to render"):
        render_jinja2(str(tmp_path), {})


def test_utils_module_falls_back_to_strenum_and_yaml_safeloader(monkeypatch):
    """Test utils module falls back to strenum and YAML safe loader.

    Exercises `kapitan/utils.py` for import fallback branches when `enum.StrEnum`
    and `yaml.CSafeLoader` are unavailable, then validates the expected fallback
    selection contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    import enum as real_enum

    import yaml as real_yaml

    import kapitan.utils as utils_module

    class _FakeStrEnum(str):
        __slots__ = ()

    fake_enum = types.ModuleType("enum")
    for attr in dir(real_enum):
        if attr == "StrEnum":
            continue
        setattr(fake_enum, attr, getattr(real_enum, attr))

    fake_strenum = types.ModuleType("strenum")
    fake_strenum.StrEnum = _FakeStrEnum

    fake_yaml = types.ModuleType("yaml")
    for attr in dir(real_yaml):
        if attr == "CSafeLoader":
            continue
        setattr(fake_yaml, attr, getattr(real_yaml, attr))

    module_path = Path(utils_module.__file__)
    temp_module_name = "kapitan.utils_test_import_fallbacks"

    monkeypatch.setitem(sys.modules, "enum", fake_enum)
    monkeypatch.setitem(sys.modules, "strenum", fake_strenum)
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)
    monkeypatch.delitem(sys.modules, temp_module_name, raising=False)

    spec = importlib.util.spec_from_file_location(temp_module_name, module_path)
    temp_module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(temp_module)

    assert temp_module.StrEnum is _FakeStrEnum
    assert temp_module.YamlLoader is real_yaml.SafeLoader


def test_null_presenter_defaults_when_flag_attribute_is_missing(monkeypatch):
    """Test null presenter defaults when flag attribute is missing.

    Exercises `kapitan/utils.py` for the branch where cached args do not define
    `yaml_dump_null_as_empty`, then validates the expected null serialization
    contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """

    class _DummyDumper:
        def represent_scalar(self, tag, data, style=None):
            return {"tag": tag, "data": data, "style": style}

    monkeypatch.setattr(cached, "args", SimpleNamespace())
    result = null_presenter(_DummyDumper(), None)
    assert result["data"] == "null"


def test_deep_get_non_dict_and_check_version_keyerror_branch(monkeypatch):
    """Test deep get non dict and check version key error branch.

    Exercises `kapitan/utils.py` for the non-dict fallthrough in `deep_get` and
    the KeyError-swallowing branch in `check_version`, then validates the
    expected no-raise contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    from kapitan import utils

    assert deep_get([], ["a"]) is None

    monkeypatch.setattr(utils, "dot_kapitan_config", lambda: {"not_version": "1.0.0"})
    assert utils.check_version() is None


def test_unpack_downloaded_file_handles_missing_filetype_and_targz(
    tmp_path, monkeypatch
):
    """Test unpack downloaded file handles missing filetype and targz.

    Exercises `kapitan/utils.py` for filetype-guess fallthrough and `.tar.gz`
    extraction branches in `unpack_downloaded_file`, then validates the expected
    result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    plain_payload = tmp_path / "payload.bin"
    plain_payload.write_bytes(b"plain")
    monkeypatch.setattr(filetype, "guess", lambda _path: None)
    assert unpack_downloaded_file(str(plain_payload), str(output_dir), None) is False

    archive = tmp_path / "payload.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo(name="hello.txt")
        content = b"hello"
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))

    extracted_dir = tmp_path / "untarred"
    extracted_dir.mkdir()
    assert (
        unpack_downloaded_file(str(archive), str(extracted_dir), "application/gzip")
        is True
    )
    assert (extracted_dir / "hello.txt").read_text(encoding="utf-8") == "hello"


def test_compare_versions_covers_non_orderable_part_fallthrough():
    """Test compare versions covers non orderable part fallthrough.

    Exercises `kapitan/utils.py` for the loop-fallthrough branch in
    `compare_versions` where neither equality nor ordering checks match for a
    version segment, then validates the expected return contract.

    It targets shared filesystem/network/version helper utilities. This protects
    deterministic behavior for unusual comparable objects.
    """

    class _VersionPart:
        def __eq__(self, _other):
            return False

        def __gt__(self, _other):
            return False

        def __lt__(self, _other):
            return False

    class _VersionLike:
        @staticmethod
        def replace(_old, _new):
            return _VersionLike()

        @staticmethod
        def split(_sep):
            return [_VersionPart()]

    assert compare_versions(_VersionLike(), _VersionLike()) == "equal"


def test_check_version_covers_unexpected_compare_result_branch(monkeypatch):
    """Test check version covers unexpected compare result branch.

    Exercises `kapitan/utils.py` for the branch where `compare_versions` returns
    a non-standard value in `check_version`, then validates the expected
    error-handling contract.

    It targets shared filesystem/network/version helper utilities. This keeps
    branch behavior deterministic under monkeypatched or abnormal comparison
    behavior.
    """
    from kapitan import utils

    monkeypatch.setattr(utils, "dot_kapitan_config", lambda: {"version": "1.2.3"})
    monkeypatch.setattr(utils, "compare_versions", lambda *_args: "unexpected")

    with pytest.raises(SystemExit) as excinfo:
        utils.check_version()
    assert excinfo.value.code == 1


class _Response:
    def __init__(self, ok=True, content=b"", headers=None):
        self.ok = ok
        self.content = content
        self.headers = headers or {"Content-Type": "text/plain"}

    def raise_for_status(self):
        raise RuntimeError("bad status")


def test_make_request_ok(monkeypatch):
    """Test make request ok.

    Exercises `kapitan/utils.py` for the "make request ok" path using mocked
    dependency boundaries, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    response = _Response(
        ok=True, content=b"data", headers={"Content-Type": "text/plain"}
    )
    monkeypatch.setattr("kapitan.utils.requests.get", lambda _url: response)

    content, content_type = make_request("http://example")
    assert content == b"data"
    assert content_type == "text/plain"


def test_make_request_error(monkeypatch):
    """Test make request error.

    Exercises `kapitan/utils.py` for the "make request error" path using mocked
    dependency boundaries, then validates the expected error-handling contract.

    It targets shared filesystem/network/version helper utilities. This prevents
    invalid input or dependency failures from being silently accepted and keeps
    failures deterministic.
    """
    response = _Response(ok=False)
    monkeypatch.setattr("kapitan.utils.requests.get", lambda _url: response)

    with pytest.raises(RuntimeError):
        make_request("http://example")


def _write_zip(path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("file.txt", "hello")
    path.write_bytes(buffer.getvalue())


def _write_tar(path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        info = tarfile.TarInfo(name="file.txt")
        data = b"hello"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    path.write_bytes(buffer.getvalue())


def test_unpack_zip(tmp_path):
    """Test unpack zip.

    Exercises `kapitan/utils.py` for the "unpack zip" path using temporary
    filesystem fixtures, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    archive = tmp_path / "archive.zip"
    _write_zip(archive)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(archive), str(output_dir), "application/zip")
    assert (output_dir / "file.txt").read_text(encoding="utf-8") == "hello"


def test_unpack_tar(tmp_path):
    """Test unpack tar.

    Exercises `kapitan/utils.py` for the "unpack tar" path using temporary
    filesystem fixtures, then validates the expected result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    archive = tmp_path / "archive.tar"
    _write_tar(archive)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(archive), str(output_dir), "application/x-tar")
    assert (output_dir / "file.txt").read_text(encoding="utf-8") == "hello"


def test_unpack_unknown_type_returns_false(tmp_path):
    """Test unpack unknown type returns false.

    Exercises `kapitan/utils.py` for the "unpack unknown type returns false"
    path using temporary filesystem fixtures, then validates the expected
    result/output contract.

    It targets shared filesystem/network/version helper utilities. This protects
    stable behavior for downstream callers and guards normal execution paths
    from regressions.
    """
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"data")

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(payload), str(output_dir), "text/plain") is False
