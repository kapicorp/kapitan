#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Public library API for Kapitan.

Provides callable entry points that work without touching ``sys.argv`` or
relying on ``sys.exit``.  Callers get exceptions, not process termination.

Example::

    from kapitan.api import compile

    compile(
        inventory_path="./inventory",
        search_paths=[".", "lib"],
        targets=["myapp"],
    )
"""

from kapitan.api.compile import compile


__all__ = ["compile"]
