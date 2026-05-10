#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Archive and file-copy utilities for Kapitan."""

import glob
import logging
import os
import re
import shutil
import tarfile
from zipfile import ZipFile

import filetype
import requests


logger = logging.getLogger(__name__)

# Default timeout for outbound HTTP requests.  Override via KAPITAN_FETCH_TIMEOUT (seconds).
_HTTP_TIMEOUT = int(os.environ.get("KAPITAN_FETCH_TIMEOUT", "30"))


class SafeCopyError(Exception):
    """Raised when a file or directory cannot be safely copied."""


def make_request(source, timeout=None):
    """downloads the http file at source and returns it's content"""
    r = requests.get(source, timeout=timeout if timeout is not None else _HTTP_TIMEOUT)
    if r.ok:
        return r.content, r.headers["Content-Type"]
    r.raise_for_status()
    return None, None


def unpack_downloaded_file(file_path, output_path, content_type):
    """unpacks files of various MIME type and stores it to the output_path"""
    is_unpacked = False

    if content_type is None or content_type == "application/octet-stream":
        kind = filetype.guess(file_path)
        if kind and kind.mime == "application/zip":
            content_type = "application/zip"

    if content_type == "application/x-tar":
        tar = tarfile.open(file_path)
        tar.extractall(path=output_path)
        tar.close()
        is_unpacked = True
    elif content_type == "application/zip":
        zfile = ZipFile(file_path)
        zfile.extractall(output_path)
        zfile.close()
        is_unpacked = True
    elif content_type in [
        "application/gzip",
        "application/octet-stream",
        "application/x-gzip",
        "application/x-compressed",
        "application/x-compressed-tar",
    ]:
        if re.search(r"(\.tar\.gz|\.tgz)$", file_path):
            tar = tarfile.open(file_path)
            tar.extractall(path=output_path)
            tar.close()
            is_unpacked = True
        else:
            extension = re.findall(r"\..*$", file_path)[0]
            logger.debug("File extension %s not supported", extension)
            is_unpacked = False
    else:
        logger.debug("Content type %s not supported", content_type)
        is_unpacked = False
    return is_unpacked


def safe_copy_file(src, dst):
    """Copy a file from 'src' to 'dst'.

    Similar to shutil.copyfile except if the file exists in 'dst' it's not
    clobbered or overwritten.

    returns a tuple (src, val)
    file not copied if val = 0 else 1
    """
    if not os.path.isfile(src):
        raise SafeCopyError(f"Can't copy {src}: doesn't exist or is not a regular file")

    if os.path.isdir(dst):
        dir = dst
        dst = os.path.join(dst, os.path.basename(src))
    else:
        dir = os.path.dirname(dst)

    if os.path.isfile(dst):
        logger.debug("Not updating %s (file already exists)", dst)
        return (dst, 0)
    shutil.copyfile(src, dst)
    logger.debug("Copied %s to %s", src, dir)
    return (dst, 1)


def safe_copy_tree(src, dst):
    """Recursively copies the 'src' directory tree to 'dst'

    Both 'src' and 'dst' must be directories. Similar to copy_tree except
    it doesn't overwrite an existing file and doesn't copy any file starting
    with ".".

    Returns a list of copied file paths.
    """
    if not os.path.isdir(src):
        raise SafeCopyError(f"Cannot copy tree {src}: not a directory")
    try:
        names = os.listdir(src)
    except OSError as e:
        raise SafeCopyError(f"Error listing files in {src}: {e.strerror}") from e

    try:
        os.makedirs(dst, exist_ok=True)
    except FileExistsError:
        pass
    outputs = []

    for name in names:
        src_name = os.path.join(src, name)
        dst_name = os.path.join(dst, name)

        if name.startswith("."):
            logger.debug("Not copying %s", src_name)
            continue
        if os.path.isdir(src_name):
            outputs.extend(safe_copy_tree(src_name, dst_name))
        else:
            _, value = safe_copy_file(src_name, dst_name)
            if value:
                outputs.append(dst_name)

    return outputs


def force_copy_file(src: str, dst: str, *args, **kwargs):
    """Copy file from `src` to `dst`, forcibly replacing `dst` if it's a file."""
    if os.path.isfile(dst):
        os.unlink(dst)
    shutil.copy2(src, dst, *args, **kwargs)


def copy_tree(src: str, dst: str, clobber_files=False) -> list:
    """Recursively copy a given directory from `src` to `dst`.

    If `dst` or a parent of `dst` doesn't exist, the missing directories are
    created. If `clobber_files` is set to true, existing files in the
    destination directory are completely clobbered.

    Returns a list of the copied files.
    """
    if not os.path.isdir(src):
        raise SafeCopyError(f"Cannot copy tree {src}: not a directory")

    if os.path.exists(dst) and not os.path.isdir(dst):
        raise SafeCopyError(
            f"Cannot copy tree to {dst}: destination exists but not a directory"
        )

    before = set(glob.iglob(f"{dst}/*", recursive=True))
    if clobber_files:
        copy_function = force_copy_file
    else:
        copy_function = shutil.copy2
    shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=copy_function)
    after = set(glob.iglob(f"{dst}/*", recursive=True))
    return list(after - before)
