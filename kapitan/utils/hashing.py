#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Hashing utilities for Kapitan."""

import json
import math
from collections import Counter
from functools import lru_cache
from hashlib import sha256

from kapitan.errors import CompileError


@lru_cache(maxsize=256)
def sha256_string(string):
    """Returns sha256 hex digest for string"""
    return sha256(string.encode("UTF-8")).hexdigest()


def directory_hash(directory):
    """Return the sha256 hash for the file contents of a directory"""
    import os

    if not os.path.exists(directory):
        raise OSError(f"utils.directory_hash failed, {directory} dir doesn't exist")

    if not os.path.isdir(directory):
        raise OSError(f"utils.directory_hash failed, {directory} is not a directory")

    try:
        hash = sha256()
        for root, _, files in sorted(os.walk(directory)):
            for names in sorted(files):
                file_path = os.path.join(root, names)
                try:
                    with open(file_path) as f:
                        file_hash = sha256(f.read().encode("UTF-8"))
                        hash.update(file_hash.hexdigest().encode("UTF-8"))
                except Exception as e:
                    if isinstance(e, UnicodeDecodeError):
                        with open(file_path, "rb") as f:
                            binary_file_hash = sha256(f.read())
                            hash.update(binary_file_hash.hexdigest().encode("UTF-8"))
                    else:
                        raise CompileError(
                            f"utils.directory_hash failed to open {file_path}: {e}"
                        ) from e
    except Exception as e:
        raise CompileError(f"utils.directory_hash failed: {e}") from e

    return hash.hexdigest()


def dictionary_hash(dict):
    """Return the sha256 hash for dict"""
    return sha256(json.dumps(dict, sort_keys=True).encode("UTF-8")).hexdigest()


def get_entropy(s):
    """Computes and returns the Shannon Entropy for string 's'"""
    length = float(len(s))
    entropy = -sum(
        count / length * math.log2(count / length) for count in Counter(s).values()
    )
    return round(entropy, 2)
