#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"kapitan targets"

import logging
import multiprocessing
import os
import shutil
import tempfile
import time
from functools import partial

from reclass.errors import NotFoundError, ReclassException

from kapitan import cached
from kapitan.dependency_manager.base import fetch_dependencies
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.inputs import get_compiler
from kapitan.profiling import worker_profile
from kapitan.resources import get_inventory


logger = logging.getLogger(__name__)


def _pool_init(globals_cached):
    """Pool initializer: seed each worker's `cached` module from the parent.

    Called once per worker after fork/spawn. ``initargs`` is pickled once per
    worker process, so the inventory snapshot is paid for at most once per
    worker rather than once per task.

    On fork the parent's state is already inherited via copy-on-write so the
    restore is skipped; on spawn the worker's `cached` is empty and gets
    populated from the snapshot. When ``--inventory-pool-cache=False``
    (``globals_cached is None``), workers keep whatever state they inherited
    (the full cache on fork, an empty module on spawn).
    """
    if globals_cached and not cached.inv:
        cached.from_dict(globals_cached)


def compile_targets(inventory_path, search_paths, ref_controller, args):
    """
    Searches and loads target files, and runs compile_target() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix=".kapitan")
    # enable previously compiled items to be reference in other compile inputs
    search_paths.append(temp_path)
    temp_compile_path = os.path.join(temp_path, "compiled")
    dep_cache_dir = temp_path

    rendering_start = time.time()
    inventory = get_inventory(inventory_path)
    discovered_targets = inventory.targets.keys()

    logger.info(
        f"Rendered inventory (%.2fs): discovered {len(discovered_targets)} targets.",
        time.time() - rendering_start,
    )

    if discovered_targets == 0:
        raise CompileError("No inventory targets discovered at path: {inventory_path}")

    targets = args.targets or discovered_targets
    labels = args.labels

    # fail fast on explicitly requested targets that don't exist (e.g. typos),
    # rather than silently skipping them later
    if args.targets:
        unknown_targets = [t for t in args.targets if t not in discovered_targets]
        if unknown_targets:
            raise CompileError(
                f"Targets not found in inventory: {', '.join(sorted(unknown_targets))}"
            )

    try:
        targets = search_targets(inventory, targets, labels)

    except CompileError as e:
        raise CompileError(f"Error searching targets: {e}") from e

    if len(targets) == 0:
        raise CompileError(
            f"No matching targets found in inventory: {labels if labels else args.targets}"
        )

    parallelism = args.parallelism or min(len(targets), os.cpu_count())

    logger.info(
        f"Compiling {len(targets)}/{len(discovered_targets)} targets using {parallelism} concurrent processes: ({os.cpu_count()} CPU detected)"
    )

    # check if --fetch or --force-fetch is enabled
    force_fetch = args.force_fetch
    fetch = args.fetch or force_fetch

    # deprecated --force flag
    if args.force:
        logger.info(
            "DeprecationWarning: --force is deprecated. Use --force-fetch instead of --force --fetch"
        )
        force_fetch = True

    if fetch:
        # skip classes that are not yet available
        target_objs = load_target_inventory(
            inventory, targets, ignore_class_not_found=True
        )
    else:
        # ignore_class_not_found = False by default
        target_objs = load_target_inventory(inventory, targets)

    if not target_objs:
        logger.info(
            "No targets with compile configuration found. Skipping compilation."
        )
        return

    # append "compiled" to output_path so we can safely overwrite it
    output_path = args.output_path
    compile_path = os.path.join(output_path, "compiled")

    try:
        fetching_start = time.time()

        # fetch dependencies on a short-lived pool: it doesn't read worker-side
        # `cached` state, so it doesn't need the inventory snapshot
        fetch_targets = None
        if fetch:
            fetch_targets = (target_objs, force_fetch)
        elif not force_fetch:
            fetch_objs = [
                target
                for target in target_objs
                for entry in target.dependencies
                if entry.force_fetch
            ]
            if fetch_objs:
                fetch_targets = (fetch_objs, True)

        if fetch_targets is not None:
            with multiprocessing.Pool(parallelism) as fetch_pool:
                fetch_dependencies(
                    output_path,
                    fetch_targets[0],
                    dep_cache_dir,
                    fetch_targets[1],
                    fetch_pool,
                )
            logger.info("Fetched dependencies (%.2fs)", time.time() - fetching_start)

        # snapshot `cached` once and pass it to the compile pool via
        # initargs so each worker is seeded a single time. Per-target
        # mutations (e.g. target_full_path) travel with the target object
        # itself via imap_unordered.
        pool_initargs = (cached.as_dict() if args.inventory_pool_cache else None,)

        with multiprocessing.Pool(
            parallelism, initializer=_pool_init, initargs=pool_initargs
        ) as pool:
            compile_start = time.time()
            worker = partial(
                compile_target,
                search_paths=search_paths,
                compile_path=temp_compile_path,
                ref_controller=ref_controller,
                args=args,
            )

            # compile_target() returns None on success
            # so p is only not None when raising an exception
            if getattr(args, "profile_serial", False):
                # Serial in-process mode: bypass the Pool so a single
                # pyinstrument profile in the parent contains the full
                # call tree (kadet/jinja/jsonnet internals included).
                # Wall-clock is slower but visibility is complete.
                logger.info(
                    "--profile-serial: compiling %d targets serially in the parent process",
                    len(target_objs),
                )
                for target_obj in target_objs:
                    worker(target_obj)
            else:
                [p.get() for p in pool.imap_unordered(worker, target_objs) if p]

            # Only copy compiled outputs if anything was actually compiled
            if os.path.exists(temp_compile_path):
                os.makedirs(compile_path, exist_ok=True)

                # if '-t' is set on compile or only a few changed, only override selected targets
                if len(target_objs) < len(discovered_targets):
                    for target in target_objs:
                        path = target.target_full_path
                        compile_path_target = os.path.join(compile_path, path)
                        temp_path_target = os.path.join(temp_compile_path, path)

                        os.makedirs(compile_path_target, exist_ok=True)

                        shutil.rmtree(compile_path_target)
                        shutil.copytree(temp_path_target, compile_path_target)
                        logger.debug(
                            "Copied %s into %s", temp_path_target, compile_path_target
                        )
                # otherwise override all targets
                else:
                    shutil.rmtree(compile_path)
                    shutil.copytree(temp_compile_path, compile_path)
                    logger.debug("Copied %s into %s", temp_compile_path, compile_path)

            logger.info(
                f"Compiled {len(target_objs)} targets in %.2fs",
                time.time() - compile_start,
            )
    except ReclassException as e:
        if isinstance(e, NotFoundError):
            logger.error("Inventory reclass error: inventory not found")
        else:
            logger.error("Inventory reclass error: %s", e.message)
        raise InventoryError(e.message) from e
    except Exception as e:
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.exception("\nUnknown (Non-Kapitan) error occurred:\n")

        logger.error("\n")
        if args.verbose:
            logger.exception(e)
        else:
            logger.error(e)
        raise CompileError(f"Error compiling targets: {e}") from e

    finally:
        shutil.rmtree(temp_path)
        logger.debug("Removed %s", temp_path)


def load_target_inventory(inventory, requested_targets, ignore_class_not_found=False):
    """returns a list of target objects from the inventory"""
    target_objs = []

    # if '-t' is set on compile, only loop through selected targets
    if requested_targets:
        targets = inventory.get_targets(requested_targets)
    else:
        targets = inventory.targets

    for target_name, target in targets.items():
        try:
            if not target.parameters:
                if ignore_class_not_found:
                    continue
                raise InventoryError(
                    f"InventoryError: {target_name}: parameters is empty"
                )

            kapitan_target_configs = target.parameters.kapitan
            # check if parameters.kapitan is empty
            if not kapitan_target_configs:
                logger.info(
                    f"Skipping target {target_name}: no kapitan configuration (parameters.kapitan is empty)"
                )
                continue

            # check if parameters.kapitan.compile is empty
            if not kapitan_target_configs.compile:
                logger.info(
                    f"Skipping target {target_name}: no kapitan.compile configuration"
                )
                continue

            kapitan_target_configs.target_full_path = inventory.targets[
                target_name
            ].name.replace(".", "/")
            logger.debug(
                f"load_target_inventory: found valid kapitan target {target_name}"
            )
            target_objs.append(kapitan_target_configs)
        except KeyError:
            logger.debug(
                f"load_target_inventory: target {target_name} has no kapitan compile obj"
            )

    return target_objs


def search_targets(inventory, targets, labels):
    """returns a list of targets where the labels match, otherwise just return the original targets"""
    if not labels:
        return targets

    try:
        labels_dict = dict(label.split("=") for label in labels)
    except ValueError as e:
        raise CompileError(
            "Compile error: Failed to parse labels, should be formatted like: kapitan compile -l env=prod app=example"
        ) from e

    targets_found = []
    # It should come back already rendered

    for target in inventory.targets.values():
        target_labels = target.parameters.kapitan.labels
        matched_all_labels = False
        for label, value in labels_dict.items():
            try:
                if target_labels[label] == value:
                    matched_all_labels = True
                    continue
            except KeyError:
                logger.debug(
                    f"search_targets: label {label}={value} didn't match target {target.name} {target_labels}"
                )

            matched_all_labels = False
            break

        if matched_all_labels:
            targets_found.append(target.name)

    if len(targets_found) == 0:
        raise CompileError(f"No targets found with labels: {labels}")

    return targets_found


def compile_target(target_config, search_paths, compile_path, ref_controller, args):
    """Compiles target_obj and writes to compile_path"""
    # worker_profile() is a no-op unless the parent set the
    # KAPITAN_PROFILE_WORKERS_DIR env var (i.e. user passed --profile-workers).
    with worker_profile():
        return _compile_target_impl(
            target_config,
            search_paths,
            compile_path,
            ref_controller,
            args,
        )


def _compile_target_impl(
    target_config, search_paths, compile_path, ref_controller, args
):
    start = time.time()
    compile_configs = target_config.compile
    target_name = target_config.vars.target

    for compile_config in compile_configs:
        try:
            input_type = compile_config.input_type
            input_compiler = get_compiler(input_type)(
                compile_path, search_paths, ref_controller, target_name, args
            )
            input_compiler.compile_obj(compile_config)
        except AttributeError as e:
            import traceback

            traceback.print_exception(type(e), e, e.__traceback__)
            raise CompileError(
                f'Invalid input_type: "{compile_config.input_type}" {e}'
            ) from e

        except Exception as e:
            if compile_config.continue_on_compile_error:
                logger.error("Error compiling %s: %s", target_name, e)
                continue
            import traceback

            traceback.print_exception(type(e), e, e.__traceback__)
            raise CompileError(f"Error compiling {target_name}: {e}") from e

    logger.info(
        "Compiled %s (%.2fs)", target_config.target_full_path, time.time() - start
    )
