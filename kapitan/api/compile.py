#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Library-mode compile entry point.

:func:`compile` is the public API surface for programmatic compilation.  It
never calls ``sys.exit`` and never reads ``sys.argv``; all behaviour is
controlled by its keyword arguments.  Errors are surfaced as exceptions.
"""

import os
from argparse import Namespace
from typing import Optional

from kapitan import cached, defaults
from kapitan.inventory import InventoryBackends
from kapitan.refs.base import RefController, Revealer
from kapitan.targets import compile_targets


def compile(
    inventory_path: str = "./inventory",
    search_paths: Optional[list[str]] = None,
    refs_path: str = "./refs",
    output_path: str = ".",
    targets: Optional[list[str]] = None,
    labels: Optional[list[str]] = None,
    parallelism: Optional[int] = None,
    fetch: bool = False,
    force_fetch: bool = False,
    force: bool = False,
    validate: bool = False,
    reveal: bool = False,
    embed_refs: bool = False,
    prune: bool = False,
    indent: int = 2,
    cache: bool = False,
    ignore_version_check: bool = True,
    use_go_jsonnet: bool = False,
    yaml_multiline_string_style: str = "literal",
    yaml_dump_null_as_empty: bool = False,
    schemas_path: str = "./schemas",
    jinja2_filters: str = defaults.DEFAULT_JINJA2_FILTERS_PATH,
    inventory_backend: str = InventoryBackends.RECLASS,
    compose_target_name: bool = False,
    inventory_pool_cache: bool = True,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Compile Kapitan targets without touching ``sys.argv`` or ``sys.exit``.

    Raises exceptions (never ``SystemExit``) on error so callers can handle
    failures programmatically.
    """
    if search_paths is None:
        search_paths = [".", "lib"]
    if targets is None:
        targets = []
    if labels is None:
        labels = []

    args = Namespace(
        inventory_path=inventory_path,
        search_paths=search_paths,
        refs_path=refs_path,
        output_path=output_path,
        targets=targets,
        labels=labels,
        parallelism=parallelism,
        fetch=fetch,
        force_fetch=force_fetch,
        force=force,
        validate=validate,
        reveal=reveal,
        embed_refs=embed_refs,
        prune=prune,
        indent=indent,
        cache=cache,
        ignore_version_check=ignore_version_check,
        use_go_jsonnet=use_go_jsonnet,
        yaml_multiline_string_style=yaml_multiline_string_style,
        yaml_dump_null_as_empty=yaml_dump_null_as_empty,
        schemas_path=schemas_path,
        jinja2_filters=jinja2_filters,
        inventory_backend=inventory_backend,
        compose_target_name=compose_target_name,
        inventory_pool_cache=inventory_pool_cache,
        verbose=verbose,
        quiet=quiet,
    )

    search_paths_abs = [os.path.abspath(path) for path in search_paths]

    ref_controller = RefController(refs_path, embed_refs=embed_refs)
    # Populate the cached shim so that jinja2 filters and other consumers that
    # still read ``cached.args`` / ``cached.ref_controller_obj`` get consistent
    # values.  These assignments will route through the active CompileContext if
    # one is set (FR-004 shim), otherwise they go into the fallback store.
    cached.args = args
    cached.ref_controller_obj = ref_controller
    cached.revealer_obj = Revealer(ref_controller)

    # compile_targets raises on error — no sys.exit here
    compile_targets(
        inventory_path=inventory_path,
        search_paths=search_paths_abs,
        ref_controller=ref_controller,
        args=args,
    )
