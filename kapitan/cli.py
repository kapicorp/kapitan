#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"command line module"

from __future__ import print_function

import argparse
import json
import logging
import multiprocessing
import os
import sys

import yaml

from kapitan import cached, defaults, setup_logging
from kapitan.initialiser import initialise_skeleton
from kapitan.inputs.jsonnet import jsonnet_file
from kapitan.lint import start_lint
from kapitan.refs.base import RefController, Revealer
from kapitan.refs.cmd_parser import handle_refs_command
from kapitan.resources import generate_inventory, resource_callbacks, search_imports
from kapitan.targets import compile_targets, schema_validate_compiled
from kapitan.utils import check_version, from_dot_kapitan, searchvar
from kapitan.version import DESCRIPTION, PROJECT_NAME, VERSION

logger = logging.getLogger(__name__)


def print_deprecated_secrets_msg(args):
    logger.error("Secrets have been renamed to refs, please refer to: '$ kapitan refs --help'")
    sys.exit(1)


def trigger_eval(args):
    file_path = args.jsonnet_file
    search_paths = [os.path.abspath(path) for path in args.search_paths]
    ext_vars = {}
    if args.vars:
        ext_vars = dict(var.split("=") for var in args.vars)
    json_output = None

    def _search_imports(cwd, imp):
        return search_imports(cwd, imp, search_paths)

    json_output = jsonnet_file(
        file_path,
        import_callback=_search_imports,
        native_callbacks=resource_callbacks(search_paths),
        ext_vars=ext_vars,
    )
    if args.output == "yaml":
        json_obj = json.loads(json_output)
        yaml.safe_dump(json_obj, sys.stdout, default_flow_style=False)
    elif json_output:
        print(json_output)


def trigger_compile(args):
    search_paths = [os.path.abspath(path) for path in args.search_paths]

    if not args.ignore_version_check:
        check_version()

    ref_controller = RefController(args.refs_path, embed_refs=args.embed_refs)
    # cache controller for use in reveal_maybe jinja2 filter
    cached.ref_controller_obj = ref_controller
    cached.revealer_obj = Revealer(ref_controller)

    compile_targets(
        args.inventory_path,
        search_paths,
        args.output_path,
        args.parallelism,
        args.targets,
        args.labels,
        ref_controller,
        prune=(args.prune),
        indent=args.indent,
        reveal=args.reveal,
        cache=args.cache,
        cache_paths=args.cache_paths,
        fetch=args.fetch,
        force_fetch=args.force_fetch,
        force=args.force,  # deprecated
        validate=args.validate,
        schemas_path=args.schemas_path,
        jinja2_filters=args.jinja2_filters,
        verbose=hasattr(args, "verbose") and args.verbose,
        use_go_jsonnet=args.use_go_jsonnet,
        compose_node_name=args.compose_node_name,
    )


def build_parser():
    parser = argparse.ArgumentParser(prog=PROJECT_NAME, description=DESCRIPTION)
    parser.add_argument("--version", action="version", version=VERSION)
    subparser = parser.add_subparsers(help="commands", dest="subparser_name")

    eval_parser = subparser.add_parser("eval", aliases=["e"], help="evaluate jsonnet file")
    eval_parser.add_argument("jsonnet_file", type=str)
    eval_parser.set_defaults(func=trigger_eval, name="eval")

    eval_parser.add_argument(
        "--output",
        type=str,
        choices=("yaml", "json"),
        default=from_dot_kapitan("eval", "output", "yaml"),
        help='set output format, default is "yaml"',
    )
    eval_parser.add_argument(
        "--vars",
        type=str,
        default=from_dot_kapitan("eval", "vars", []),
        nargs="*",
        metavar="VAR",
        help="set variables",
    )
    eval_parser.add_argument(
        "--search-paths",
        "-J",
        type=str,
        nargs="+",
        default=from_dot_kapitan("eval", "search-paths", ["."]),
        metavar="JPATH",
        help='set search paths, default is ["."]',
    )

    compile_parser = subparser.add_parser("compile", aliases=["c"], help="compile targets")
    compile_parser.set_defaults(func=trigger_compile, name="compile")

    compile_parser.add_argument(
        "--search-paths",
        "-J",
        type=str,
        nargs="+",
        default=from_dot_kapitan("compile", "search-paths", [".", "lib"]),
        metavar="JPATH",
        help='set search paths, default is ["."]',
    )
    compile_parser.add_argument(
        "--jinja2-filters",
        "-J2F",
        type=str,
        default=from_dot_kapitan("compile", "jinja2-filters", defaults.DEFAULT_JINJA2_FILTERS_PATH),
        metavar="FPATH",
        help="load custom jinja2 filters from any file, default is to put\
                                them inside lib/jinja2_filters.py",
    )
    compile_parser.add_argument(
        "--verbose",
        "-v",
        help="set verbose mode",
        action="store_true",
        default=from_dot_kapitan("compile", "verbose", False),
    )
    compile_parser.add_argument(
        "--prune",
        help="prune jsonnet output",
        action="store_true",
        default=from_dot_kapitan("compile", "prune", False),
    )
    compile_parser.add_argument(
        "--quiet",
        help="set quiet mode, only critical output",
        action="store_true",
        default=from_dot_kapitan("compile", "quiet", False),
    )
    compile_parser.add_argument(
        "--output-path",
        type=str,
        default=from_dot_kapitan("compile", "output-path", "."),
        metavar="PATH",
        help='set output path, default is "."',
    )
    compile_parser.add_argument(
        "--fetch",
        help="fetch remote inventories and/or external dependencies",
        action="store_true",
        default=from_dot_kapitan("compile", "fetch", False),
    )
    compile_parser.add_argument(
        "--force-fetch",
        help="overwrite existing inventory and/or dependency item",
        action="store_true",
        default=from_dot_kapitan("compile", "force-fetch", False),
    )
    compile_parser.add_argument(  # deprecated
        "--force",
        help="overwrite existing inventory and/or dependency item",
        action="store_true",
        default=from_dot_kapitan("compile", "force", False),
    )
    compile_parser.add_argument(
        "--validate",
        help="validate compile output against schemas as specified in inventory",
        action="store_true",
        default=from_dot_kapitan("compile", "validate", False),
    )
    compile_parser.add_argument(
        "--parallelism",
        "-p",
        type=int,
        default=from_dot_kapitan("compile", "parallelism", 4),
        metavar="INT",
        help="Number of concurrent compile processes, default is 4",
    )
    compile_parser.add_argument(
        "--indent",
        "-i",
        type=int,
        default=from_dot_kapitan("compile", "indent", 2),
        metavar="INT",
        help="Indentation spaces for YAML/JSON, default is 2",
    )
    compile_parser.add_argument(
        "--refs-path",
        help='set refs path, default is "./refs"',
        default=from_dot_kapitan("compile", "refs-path", "./refs"),
    )
    compile_parser.add_argument(
        "--reveal",
        help="reveal refs (warning: this will potentially write sensitive data)",
        action="store_true",
        default=from_dot_kapitan("compile", "reveal", False),
    )
    compile_parser.add_argument(
        "--embed-refs",
        help="embed ref contents",
        action="store_true",
        default=from_dot_kapitan("compile", "embed-refs", False),
    )

    compile_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("compile", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )
    compile_parser.add_argument(
        "--cache",
        "-c",
        help="enable compilation caching to .kapitan_cache\
        and dependency caching to .dependency_cache, default is False",
        action="store_true",
        default=from_dot_kapitan("compile", "cache", False),
    )
    compile_parser.add_argument(
        "--cache-paths",
        type=str,
        nargs="+",
        default=from_dot_kapitan("compile", "cache-paths", []),
        metavar="PATH",
        help="cache additional paths to .kapitan_cache, default is []",
    )
    compile_parser.add_argument(
        "--ignore-version-check",
        help="ignore the version from .kapitan",
        action="store_true",
        default=from_dot_kapitan("compile", "ignore-version-check", False),
    )

    compile_parser.add_argument(
        "--use-go-jsonnet",
        help="use go-jsonnet",
        action="store_true",
        default=from_dot_kapitan("compile", "use-go-jsonnet", False),
    )

    # compose-node-name should be used in conjunction with reclass
    # config "compose_node_name: true". This allows us to make the same subfolder
    # structure in the inventory folder inside the compiled folder
    # https://github.com/kapicorp/kapitan/issues/932
    compile_parser.add_argument(
        "--compose-node-name",
        help="Create same subfolder structure from inventory/targets inside compiled folder",
        action="store_true",
        default=from_dot_kapitan("compile", "compose-node-name", False),
    )

    compile_parser.add_argument(
        "--schemas-path",
        default=from_dot_kapitan("validate", "schemas-path", "./schemas"),
        help='set schema cache path, default is "./schemas"',
    )

    compile_parser.add_argument(
        "--yaml-multiline-string-style",
        "-L",
        type=str,
        choices=["literal", "folded", "double-quotes"],
        metavar="STYLE",
        action="store",
        default=from_dot_kapitan("compile", "yaml-multiline-string-style", "double-quotes"),
        help="set multiline string style to STYLE, default is 'double-quotes'",
    )

    compile_parser.add_argument(
        "--yaml-dump-null-as-empty",
        default=from_dot_kapitan("compile", "yaml-dump-null-as-empty", False),
        action="store_true",
        help="dumps all none-type entries as empty, default is dumping as 'null'",
    )

    compile_selector_parser = compile_parser.add_mutually_exclusive_group()
    compile_selector_parser.add_argument(
        "--targets",
        "-t",
        help="targets to compile, default is all",
        type=str,
        nargs="+",
        default=from_dot_kapitan("compile", "targets", []),
        metavar="TARGET",
    )
    compile_selector_parser.add_argument(
        "--labels",
        "-l",
        help="compile targets matching the labels, default is all",
        type=str,
        nargs="*",
        default=from_dot_kapitan("compile", "labels", []),
        metavar="key=value",
    )

    inventory_parser = subparser.add_parser("inventory", aliases=["i"], help="show inventory")
    inventory_parser.set_defaults(func=generate_inventory, name="inventory")

    inventory_parser.add_argument(
        "--target-name",
        "-t",
        default=from_dot_kapitan("inventory", "target-name", ""),
        help="set target name, default is all targets",
    )
    inventory_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("inventory", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )
    inventory_parser.add_argument(
        "--flat",
        "-F",
        help="flatten nested inventory variables",
        action="store_true",
        default=from_dot_kapitan("inventory", "flat", False),
    )
    inventory_parser.add_argument(
        "--pattern",
        "-p",
        default=from_dot_kapitan("inventory", "pattern", ""),
        help="filter pattern (e.g. parameters.mysql.storage_class, or storage_class,"
        + ' or storage_*), default is ""',
    )
    inventory_parser.add_argument(
        "--verbose",
        "-v",
        help="set verbose mode",
        action="store_true",
        default=from_dot_kapitan("inventory", "verbose", False),
    )
    inventory_parser.add_argument(
        "--indent",
        "-i",
        type=int,
        default=from_dot_kapitan("inventory", "indent", 2),
        metavar="INT",
        help="Indentation spaces for inventory output, default is 2",
    )
    inventory_parser.add_argument(
        "--multiline-string-style",
        "-L",
        type=str,
        choices=["literal", "folded", "double-quotes"],
        metavar="STYLE",
        action="store",
        default=from_dot_kapitan("inventory", "multiline-string-style", "double-quotes"),
        help="set multiline string style to STYLE, default is 'double-quotes'",
    )

    searchvar_parser = subparser.add_parser(
        "searchvar", aliases=["sv"], help="show all inventory files where var is declared"
    )
    searchvar_parser.set_defaults(func=searchvar, name="searchvar")

    searchvar_parser.add_argument(
        "searchvar",
        type=str,
        metavar="VARNAME",
        help="e.g. parameters.mysql.storage_class, or storage_class, or storage_*",
    )
    searchvar_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("searchvar", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )
    searchvar_parser.add_argument(
        "--verbose",
        "-v",
        help="set verbose mode",
        action="store_true",
        default=from_dot_kapitan("searchvar", "verbose", False),
    )
    searchvar_parser.add_argument(
        "--pretty-print",
        "-p",
        help="Pretty print content of var",
        action="store_true",
        default=from_dot_kapitan("searchvar", "pretty-print", False),
    )

    secrets_parser = subparser.add_parser("secrets", aliases=["s"], help="(DEPRECATED) please use refs")
    secrets_parser.set_defaults(func=print_deprecated_secrets_msg, name="secrets")

    refs_parser = subparser.add_parser("refs", aliases=["r"], help="manage refs")
    refs_parser.set_defaults(func=handle_refs_command, name="refs")

    refs_parser.add_argument(
        "--write",
        "-w",
        help="write ref token",
        metavar="TOKENNAME",
    )
    refs_parser.add_argument(
        "--update",
        help="update GPG recipients for ref token",
        metavar="TOKENNAME",
    )
    refs_parser.add_argument(
        "--update-targets",
        action="store_true",
        default=from_dot_kapitan("refs", "update-targets", False),
        help="update target secret refs",
    )
    refs_parser.add_argument(
        "--validate-targets",
        action="store_true",
        default=from_dot_kapitan("refs", "validate-targets", False),
        help="validate target secret refs",
    )
    refs_parser.add_argument(
        "--base64",
        "-b64",
        help="base64 encode file content",
        action="store_true",
        default=from_dot_kapitan("refs", "base64", False),
    )
    refs_parser.add_argument(
        "--binary",
        help="file content should be handled as binary data",
        action="store_true",
        default=from_dot_kapitan("refs", "binary", False),
    )
    refs_parser.add_argument(
        "--reveal",
        "-r",
        help="reveal refs",
        action="store_true",
        default=from_dot_kapitan("refs", "reveal", False),
    )
    refs_parser.add_argument(
        "--tag", help='specify ref tag to reveal, e.g. "?{gkms:my/ref:123456}" ', metavar="REFTAG"
    )
    refs_parser.add_argument(
        "--ref-file", "-rf", help='read ref file, set "-" for stdin', metavar="REFFILENAME"
    )
    refs_parser.add_argument(
        "--file", "-f", help='read file or directory, set "-" for stdin', metavar="FILENAME"
    )
    refs_parser.add_argument("--target-name", "-t", help="grab recipients from target name")
    refs_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("refs", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )
    refs_parser.add_argument(
        "--recipients",
        "-R",
        help="set GPG recipients",
        type=str,
        nargs="+",
        default=from_dot_kapitan("refs", "recipients", []),
        metavar="RECIPIENT",
    )
    refs_parser.add_argument(
        "--key", "-K", help="set KMS key", default=from_dot_kapitan("refs", "key", ""), metavar="KEY"
    )
    refs_parser.add_argument(
        "--vault-auth",
        help="set authentication type for vault secrets",
        default=from_dot_kapitan("refs", "vault-auth", ""),
        metavar="AUTH",
    )
    refs_parser.add_argument(
        "--refs-path",
        help='set refs path, default is "./refs"',
        default=from_dot_kapitan("refs", "refs-path", "./refs"),
    )
    refs_parser.add_argument(
        "--verbose",
        "-v",
        help="set verbose mode (warning: this will potentially show sensitive data)",
        action="store_true",
        default=from_dot_kapitan("refs", "verbose", False),
    )

    lint_parser = subparser.add_parser("lint", aliases=["l"], help="linter for inventory and refs")
    lint_parser.set_defaults(func=start_lint, name="lint")

    lint_parser.add_argument(
        "--fail-on-warning",
        default=from_dot_kapitan("lint", "fail-on-warning", False),
        action="store_true",
        help="exit with failure code if warnings exist, default is False",
    )
    lint_parser.add_argument(
        "--skip-class-checks",
        action="store_true",
        help="skip checking for unused classes, default is False",
        default=from_dot_kapitan("lint", "skip-class-checks", False),
    )
    lint_parser.add_argument(
        "--skip-yamllint",
        action="store_true",
        help="skip running yamllint on inventory, default is False",
        default=from_dot_kapitan("lint", "skip-yamllint", False),
    )
    lint_parser.add_argument(
        "--search-secrets",
        default=from_dot_kapitan("lint", "search-secrets", False),
        action="store_true",
        help="searches for plaintext secrets in inventory, default is False",
    )
    lint_parser.add_argument(
        "--refs-path",
        help='set refs path, default is "./refs"',
        default=from_dot_kapitan("lint", "refs-path", "./refs"),
    )
    lint_parser.add_argument(
        "--compiled-path",
        default=from_dot_kapitan("lint", "compiled-path", "./compiled"),
        help='set compiled path, default is "./compiled"',
    )
    lint_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("lint", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )

    init_parser = subparser.add_parser(
        "init", help="initialize a directory with the recommended kapitan project skeleton."
    )
    init_parser.set_defaults(func=initialise_skeleton, name="init")

    init_parser.add_argument(
        "--directory",
        default=from_dot_kapitan("init", "directory", "."),
        help="set path, in which to generate the project skeleton,"
        'assumes directory already exists. default is "./"',
    )

    validate_parser = subparser.add_parser(
        "validate",
        aliases=["v"],
        help="validates the compile output against schemas as specified in inventory",
    )
    validate_parser.set_defaults(func=schema_validate_compiled, name="validate")

    validate_parser.add_argument(
        "--compiled-path",
        default=from_dot_kapitan("compile", "compiled-path", "./compiled"),
        help='set compiled path, default is "./compiled',
    )
    validate_parser.add_argument(
        "--inventory-path",
        default=from_dot_kapitan("compile", "inventory-path", "./inventory"),
        help='set inventory path, default is "./inventory"',
    )
    validate_parser.add_argument(
        "--targets",
        "-t",
        help="targets to validate, default is all",
        type=str,
        nargs="+",
        default=from_dot_kapitan("compile", "targets", []),
        metavar="TARGET",
    ),
    validate_parser.add_argument(
        "--schemas-path",
        default=from_dot_kapitan("validate", "schemas-path", "./schemas"),
        help='set schema cache path, default is "./schemas"',
    )
    validate_parser.add_argument(
        "--parallelism",
        "-p",
        type=int,
        default=from_dot_kapitan("validate", "parallelism", 4),
        metavar="INT",
        help="Number of concurrent validate processes, default is 4",
    )

    return parser


def main():
    """main function for command line usage"""
    try:
        multiprocessing.set_start_method("spawn")
    # main() is explicitly multiple times in tests
    # and will raise RuntimeError
    except RuntimeError:
        pass

    parser = build_parser()
    args = parser.parse_args()

    if getattr(args, "func", None) == generate_inventory and args.pattern and args.target_name == "":
        parser.error("--pattern requires --target_name")

    logger.debug("Running with args: %s", args)

    try:
        cmd = sys.argv[1]
    except IndexError:
        parser.print_help()
        sys.exit(1)

    # cache args where key is subcommand
    assert "name" in args, "All cli commands must have provided default name"
    cached.args[args.name] = args

    if hasattr(args, "verbose") and args.verbose:
        setup_logging(level=logging.DEBUG, force=True)
    elif hasattr(args, "quiet") and args.quiet:
        setup_logging(level=logging.CRITICAL, force=True)

    # call chosen command
    args.func(args)

    return 0
