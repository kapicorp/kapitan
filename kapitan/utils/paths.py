#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Path and filesystem utilities for Kapitan."""

import logging
import os
import stat


logger = logging.getLogger(__name__)


def normalise_join_path(dirname, path):
    """Join dirname with path and return in normalised form"""
    logger.debug(os.path.normpath(os.path.join(dirname, path)))
    return os.path.normpath(os.path.join(dirname, path))


def list_all_paths(folder):
    """Given a folder (string), returns a list with the full paths
    of every sub-folder/file.
    """
    for root, folders, files in os.walk(folder):
        for filename in folders + files:
            yield os.path.join(root, filename)


def file_mode(name):
    """Returns mode for file name"""
    st = os.stat(name)
    return stat.S_IMODE(st.st_mode)


def search_target_token_paths(target_secrets_path, targets):
    """
    returns dict of target and their secret token paths in target_secrets_path
    targets is a set of target names used to lookup targets in target_secrets_path
    directory should be structured as follow ./refs/${target_name}/file
    """
    from collections import defaultdict

    import yaml

    try:
        from yaml import CSafeLoader as YamlLoader
    except ImportError:
        from yaml import SafeLoader as YamlLoader

    target_files = defaultdict(list)
    for full_path in list_all_paths(target_secrets_path):
        secret_path = full_path[len(target_secrets_path) + 1 :]
        target_name = secret_path.split("/")[0]
        if target_name in targets and os.path.isfile(full_path):
            with open(full_path) as fp:
                obj = yaml.load(fp, Loader=YamlLoader)
                try:
                    secret_type = obj["type"]
                except KeyError:
                    secret_type = "gpg"
                secret_path = f"?{{{secret_type}:{secret_path}}}"
            logger.debug("search_target_token_paths: found %s", secret_path)
            target_files[target_name].append(secret_path)
    return target_files
