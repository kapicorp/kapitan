"""Hashing and entropy utility helpers."""

import json
import math
import os
from collections import Counter
from hashlib import sha256

from kapitan.errors import CompileError


def sha256_string(string):
    """Return the sha256 hex digest for a string."""
    return sha256(string.encode("UTF-8")).hexdigest()


def directory_hash(directory):
    """Return the sha256 hash for the file contents of a directory."""
    if not os.path.exists(directory):
        raise OSError(f"utils.directory_hash failed, {directory} dir doesn't exist")

    if not os.path.isdir(directory):
        raise OSError(f"utils.directory_hash failed, {directory} is not a directory")

    try:
        digest = sha256()
        for root, _, files in sorted(os.walk(directory)):
            for name in sorted(files):
                file_path = os.path.join(root, name)
                try:
                    with open(file_path) as handle:
                        file_hash = sha256(handle.read().encode("UTF-8"))
                        digest.update(file_hash.hexdigest().encode("UTF-8"))
                except Exception as exc:
                    if isinstance(exc, UnicodeDecodeError):
                        with open(file_path, "rb") as handle:
                            binary_file_hash = sha256(handle.read())
                            digest.update(binary_file_hash.hexdigest().encode("UTF-8"))
                    else:
                        raise CompileError(
                            f"utils.directory_hash failed to open {file_path}: {exc}"
                        )
    except Exception as exc:
        raise CompileError(f"utils.directory_hash failed: {exc}")

    return digest.hexdigest()


def dictionary_hash(data):
    """Return the sha256 hash for a dict."""
    return sha256(json.dumps(data, sort_keys=True).encode("UTF-8")).hexdigest()


def get_entropy(value):
    """Compute and return the Shannon entropy for a string."""
    length = float(len(value))
    entropy = -sum(
        count / length * math.log2(count / length) for count in Counter(value).values()
    )
    return round(entropy, 2)
