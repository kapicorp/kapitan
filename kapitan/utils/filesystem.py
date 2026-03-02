"""Filesystem and archive utility helpers."""

import glob
import logging
import os
import re
import shutil
import stat
import tarfile
import tempfile
from functools import wraps
from zipfile import ZipFile

import filetype


logger = logging.getLogger(__name__)


def normalise_join_path(dirname, path):
    """Join dirname with path and return in normalised form."""
    logger.debug(os.path.normpath(os.path.join(dirname, path)))
    return os.path.normpath(os.path.join(dirname, path))


def list_all_paths(folder):
    """Yield the full paths of every sub-folder and file under folder."""
    for root, folders, files in os.walk(folder):
        for filename in folders + files:
            yield os.path.join(root, filename)


class SafeCopyError(Exception):
    """Raised when a file or directory cannot be safely copied."""


def safe_copy_file(src, dst):
    """Copy a file from `src` to `dst` without overwriting an existing destination file."""
    if not os.path.isfile(src):
        raise SafeCopyError(f"Can't copy {src}: doesn't exist or is not a regular file")

    if os.path.isdir(dst):
        directory = dst
        dst = os.path.join(dst, os.path.basename(src))
    else:
        directory = os.path.dirname(dst)

    if os.path.isfile(dst):
        logger.debug("Not updating %s (file already exists)", dst)
        return (dst, 0)

    shutil.copyfile(src, dst)
    logger.debug("Copied %s to %s", src, directory)
    return (dst, 1)


def safe_copy_tree(src, dst):
    """Recursively copy `src` to `dst` without overwriting files or copying dotfiles."""
    if not os.path.isdir(src):
        raise SafeCopyError(f"Cannot copy tree {src}: not a directory")
    try:
        names = os.listdir(src)
    except OSError as exc:
        raise SafeCopyError(f"Error listing files in {src}: {exc.strerror}")

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
            _, copied = safe_copy_file(src_name, dst_name)
            if copied:
                outputs.append(dst_name)

    return outputs


def force_copy_file(src: str, dst: str, *args, **kwargs):
    """Copy file from `src` to `dst`, forcibly replacing `dst` if it is a file."""
    if os.path.isfile(dst):
        os.unlink(dst)
    shutil.copy2(src, dst, *args, **kwargs)


def copy_tree(src: str, dst: str, clobber_files=False) -> list:
    """Recursively copy a given directory from `src` to `dst`."""
    if not os.path.isdir(src):
        raise SafeCopyError(f"Cannot copy tree {src}: not a directory")

    if os.path.exists(dst) and not os.path.isdir(dst):
        raise SafeCopyError(
            f"Cannot copy tree to {dst}: destination exists but not a directory"
        )

    before = set(glob.iglob(f"{dst}/*", recursive=True))
    copy_function = force_copy_file if clobber_files else shutil.copy2
    shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=copy_function)
    after = set(glob.iglob(f"{dst}/*", recursive=True))
    return list(after - before)


def unpack_downloaded_file(file_path, output_path, content_type):
    """Unpack files of various MIME types and store them in output_path."""
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


def file_mode(name):
    """Return mode for file name."""
    st = os.stat(name)
    return stat.S_IMODE(st.st_mode)


def with_temp_dir(suffix: str | None = None):
    """
    Execute the wrapped function within a temporary directory context.
    Pass the path as the `temp_path` kwarg.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tempfile.TemporaryDirectory(suffix=suffix) as temp_path:
                kwargs["temp_path"] = temp_path
                return func(*args, **kwargs)

        return wrapper

    return decorator
