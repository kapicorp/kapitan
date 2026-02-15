# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import glob
import io
import os
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest
import yaml

from kapitan import cached
from kapitan.cached import reset_cache
from kapitan.inventory import InventoryBackends
from kapitan.utils import (
    SafeCopyError,
    compare_versions,
    copy_tree,
    deep_get,
    directory_hash,
    force_copy_file,
    from_dot_kapitan,
    make_request,
    normalise_join_path,
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


class _Response:
    def __init__(self, ok=True, content=b"", headers=None):
        self.ok = ok
        self.content = content
        self.headers = headers or {"Content-Type": "text/plain"}

    def raise_for_status(self):
        raise RuntimeError("bad status")


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
