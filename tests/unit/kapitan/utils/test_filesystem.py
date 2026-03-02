# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import io
import os
import stat
import tarfile
import zipfile
from pathlib import Path

import filetype
import pytest

import kapitan.utils.filesystem as utils_filesystem
from kapitan.utils.filesystem import (
    SafeCopyError,
    copy_tree,
    force_copy_file,
    normalise_join_path,
    safe_copy_file,
    safe_copy_tree,
    unpack_downloaded_file,
)
from kapitan.utils.hashing import directory_hash


REPO_ROOT = Path(__file__).resolve().parents[4]
TEST_KUBERNETES_PATH = REPO_ROOT / "examples/kubernetes"


def test_copy_tree_copies_directory_and_preserves_content_hash(tmp_path):
    dst = tmp_path / "copied"
    original = set(TEST_KUBERNETES_PATH.glob("*"))
    copied = copy_tree(str(TEST_KUBERNETES_PATH), str(dst))
    assert len(copied) == len(original)

    original_hash = directory_hash(str(TEST_KUBERNETES_PATH))
    copied_hash = directory_hash(str(dst))
    assert copied_hash == original_hash


def test_validate_copy_dir(tmp_path):
    with pytest.raises(SafeCopyError):
        copy_tree("non_existent_dir", str(tmp_path))

    dst = tmp_path / "test"
    dst.write_text("Hello\n", encoding="utf-8")
    with pytest.raises(SafeCopyError):
        copy_tree(str(TEST_KUBERNETES_PATH), str(dst))


def test_copy_dir_missing_dst(tmp_path):
    dst = tmp_path / "subdir"
    original = set(TEST_KUBERNETES_PATH.glob("*"))
    copied = copy_tree(str(TEST_KUBERNETES_PATH), str(dst))
    assert len(copied) == len(original)

    original_hash = directory_hash(str(TEST_KUBERNETES_PATH))
    copied_hash = directory_hash(str(dst))
    assert copied_hash == original_hash


def test_copy_dir_overwrite_readonly_file(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    file_path = src / "ro.txt"
    file_path.write_text("Hello!\n", encoding="utf-8")
    os.chmod(file_path, 0o444)

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


def test_safe_copy_file_rejects_missing_source(tmp_path):
    with pytest.raises(SafeCopyError):
        safe_copy_file(str(tmp_path / "missing.txt"), str(tmp_path / "out.txt"))


def test_normalise_join_path():
    assert normalise_join_path("root", "child") == os.path.join("root", "child")
    assert normalise_join_path("/root", "/child") == "/child"


def test_safe_copy_file_and_tree(tmp_path):
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


def test_safe_copy_file_and_tree_cover_copy_paths(tmp_path):
    src = tmp_path / "src"
    nested = src / "nested"
    nested.mkdir(parents=True)
    (src / "root.txt").write_text("root", encoding="utf-8")
    (nested / "child.txt").write_text("child", encoding="utf-8")

    copied_path, copied = safe_copy_file(
        str(src / "root.txt"), str(tmp_path / "copied-root.txt")
    )
    assert copied_path == str(tmp_path / "copied-root.txt")
    assert copied == 1

    dst = tmp_path / "tree"
    outputs = safe_copy_tree(str(src), str(dst))
    assert sorted(Path(path).relative_to(dst).as_posix() for path in outputs) == [
        "nested/child.txt",
        "root.txt",
    ]


def test_unpack_downloaded_file_detects_zip_and_rejects_plain_gzip(
    tmp_path, monkeypatch
):
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
    not_dir = tmp_path / "not_dir.txt"
    not_dir.write_text("nope", encoding="utf-8")

    with pytest.raises(SafeCopyError):
        safe_copy_tree(str(not_dir), str(tmp_path / "dst"))

    src_dir = tmp_path / "src"
    src_dir.mkdir()

    monkeypatch.setattr(
        utils_filesystem.os,
        "listdir",
        lambda _src: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(SafeCopyError):
        safe_copy_tree(str(src_dir), str(tmp_path / "dst2"))

    monkeypatch.setattr(utils_filesystem.os, "listdir", lambda _src: [])
    monkeypatch.setattr(
        utils_filesystem.os,
        "makedirs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    assert safe_copy_tree(str(src_dir), str(tmp_path / "dst3")) == []


def test_unpack_downloaded_file_handles_missing_filetype_and_targz(
    tmp_path, monkeypatch
):
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
    archive = tmp_path / "archive.zip"
    _write_zip(archive)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(archive), str(output_dir), "application/zip")
    assert (output_dir / "file.txt").read_text(encoding="utf-8") == "hello"


def test_unpack_tar(tmp_path):
    archive = tmp_path / "archive.tar"
    _write_tar(archive)

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(archive), str(output_dir), "application/x-tar")
    assert (output_dir / "file.txt").read_text(encoding="utf-8") == "hello"


def test_unpack_unknown_type_returns_false(tmp_path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"data")

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert unpack_downloaded_file(str(payload), str(output_dir), "text/plain") is False


def test_with_temp_dir_passes_temp_path():
    captured = {}

    @utils_filesystem.with_temp_dir(suffix="-kapitan")
    def _build_file(*, temp_path):
        temp_dir = Path(temp_path)
        captured["suffix"] = temp_dir.name.endswith("-kapitan")
        marker = temp_dir / "marker.txt"
        marker.write_text("ok", encoding="utf-8")
        return marker.read_text(encoding="utf-8")

    assert _build_file() == "ok"
    assert captured["suffix"] is True
