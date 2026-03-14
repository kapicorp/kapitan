# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from argparse import Namespace


def cached_args_defaults(**overrides):
    args = {"cache": False}
    args.update(overrides)
    return Namespace(**args)
