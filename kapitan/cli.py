#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"command line module"

from __future__ import print_function

import argparse
import ujson as json
import logging
import os
import sys
import traceback
import yaml

from kapitan.utils import jsonnet_file, PrettyDumper, flatten_dict, searchvar, deep_get, from_dot_kapitan, check_version
from kapitan.targets import compile_targets
from kapitan.resources import search_imports, resource_callbacks, inventory_reclass
from kapitan.version import PROJECT_NAME, DESCRIPTION, VERSION
from kapitan.secrets import secret_gpg_write, secret_gpg_reveal_file
from kapitan.secrets import secret_gpg_reveal_dir, secret_gpg_reveal_raw, secret_gpg_update_recipients
from kapitan.secrets import search_target_token_paths, secret_gpg_raw_read_fingerprints
from kapitan.secrets import lookup_fingerprints
from kapitan.errors import KapitanError

logger = logging.getLogger(__name__)


def main():
    """main function for command line usage"""
    parser = argparse.ArgumentParser(prog=PROJECT_NAME,
                                     description=DESCRIPTION)
    parser.add_argument('--version', action='version', version=VERSION)
    subparser = parser.add_subparsers(help="commands")

    eval_parser = subparser.add_parser('eval', help='evaluate jsonnet file')
    eval_parser.add_argument('jsonnet_file', type=str)
    eval_parser.add_argument('--output', type=str,
                             choices=('yaml', 'json'),
                             default=from_dot_kapitan('eval', 'output', 'yaml'),
                             help='set output format, default is "yaml"')
    eval_parser.add_argument('--vars', type=str,
                             default=from_dot_kapitan('eval', 'vars', []),
                             nargs='*',
                             metavar='VAR',
                             help='set variables')
    eval_parser.add_argument('--search-paths', '-J', type=str, nargs='+',
                             default=from_dot_kapitan('eval', 'search-paths', ['.']),
                             metavar='JPATH',
                             help='set search paths, default is ["."]')

    compile_parser = subparser.add_parser('compile', help='compile targets')
    compile_parser.add_argument('--search-paths', '-J', type=str, nargs='+',
                                default=from_dot_kapitan('compile', 'search-paths', ['.']),
                                metavar='JPATH',
                                help='set search paths, default is ["."]')
    compile_parser.add_argument('--verbose', '-v', help='set verbose mode',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'verbose', False))
    compile_parser.add_argument('--prune', help='prune jsonnet output',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'prune', False))
    compile_parser.add_argument('--quiet', help='set quiet mode, only critical output',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'quiet', False))
    compile_parser.add_argument('--output-path', type=str,
                                default=from_dot_kapitan('compile', 'output-path', '.'),
                                metavar='PATH',
                                help='set output path, default is "."')
    compile_parser.add_argument('--targets', '-t', help='targets to compile, default is all',
                                type=str, nargs='+',
                                default=from_dot_kapitan('compile', 'targets', []),
                                metavar='TARGET')
    compile_parser.add_argument('--parallelism', '-p', type=int,
                                default=from_dot_kapitan('compile', 'parallelism', 4),
                                metavar='INT',
                                help='Number of concurrent compile processes, default is 4')
    compile_parser.add_argument('--indent', '-i', type=int,
                                default=from_dot_kapitan('compile', 'indent', 2),
                                metavar='INT',
                                help='Indentation spaces for YAML/JSON, default is 2')
    compile_parser.add_argument('--secrets-path', help='set secrets path, default is "./secrets"',
                                default=from_dot_kapitan('compile', 'secrets-path', './secrets'))
    compile_parser.add_argument('--reveal',
                                help='reveal secrets (warning: this will write sensitive data)',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'reveal', False))
    compile_parser.add_argument('--inventory-path',
                                default=from_dot_kapitan('compile', 'inventory-path', './inventory'),
                                help='set inventory path, default is "./inventory"')
    compile_parser.add_argument('--ignore-version-check',
                                help='ignore the version from .kapitan',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'ignore-version-check', False))
    compile_parser.add_argument('--force-recompile', '-f',
                                help='force recompilation of all targets, ignores .kapitan_cache',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'force-recompile', False))

    inventory_parser = subparser.add_parser('inventory', help='show inventory')
    inventory_parser.add_argument('--target-name', '-t',
                                  default=from_dot_kapitan('inventory', 'target-name', ''),
                                  help='set target name, default is all targets')
    inventory_parser.add_argument('--inventory-path',
                                  default=from_dot_kapitan('inventory', 'inventory-path', './inventory'),
                                  help='set inventory path, default is "./inventory"')
    inventory_parser.add_argument('--flat', '-F', help='flatten nested inventory variables',
                                  action='store_true',
                                  default=from_dot_kapitan('inventory', 'flat', False))
    inventory_parser.add_argument('--pattern', '-p',
                                  default=from_dot_kapitan('inventory', 'pattern', ''),
                                  help='filter pattern (e.g. parameters.mysql.storage_class, or storage_class,' +
                                  ' or storage_*), default is ""')
    inventory_parser.add_argument('--verbose', '-v', help='set verbose mode',
                                  action='store_true',
                                  default=from_dot_kapitan('inventory', 'verbose', False))

    searchvar_parser = subparser.add_parser('searchvar',
                                            help='show all inventory files where var is declared')
    searchvar_parser.add_argument('searchvar', type=str, metavar='VARNAME',
                                  help='e.g. parameters.mysql.storage_class, or storage_class, or storage_*')
    searchvar_parser.add_argument('--inventory-path',
                                  default=from_dot_kapitan('searchvar', 'inventory-path', './inventory'),
                                  help='set inventory path, default is "./inventory"')
    searchvar_parser.add_argument('--verbose', '-v', help='set verbose mode',
                                  action='store_true',
                                  default=from_dot_kapitan('searchvar', 'verbose', False))
    searchvar_parser.add_argument('--pretty-print', '-p', help='Pretty print content of var',
                                  action='store_true',
                                  default=from_dot_kapitan('searchvar', 'pretty-print', False))

    secrets_parser = subparser.add_parser('secrets', help='manage secrets')
    secrets_parser.add_argument('--write', '-w', help='write secret token',
                                metavar='TOKENNAME',)
    secrets_parser.add_argument('--update', help='update recipients for secret token',
                                metavar='TOKENNAME',)
    secrets_parser.add_argument('--update-targets', action='store_true',
                                default=from_dot_kapitan('secrets', 'update-targets', False),
                                help='update target secrets')
    secrets_parser.add_argument('--validate-targets', action='store_true',
                                default=from_dot_kapitan('secrets', 'validate-targets', False),
                                help='validate target secrets')
    secrets_parser.add_argument('--base64', '-b64', help='base64 encode file content',
                                action='store_true',
                                default=from_dot_kapitan('secrets', 'base64', False))
    secrets_parser.add_argument('--reveal', '-r', help='reveal secrets',
                                action='store_true',
                                default=from_dot_kapitan('secrets', 'reveal', False))
    secrets_parser.add_argument('--file', '-f', help='read file or directory, set "-" for stdin',
                                metavar='FILENAME')
    secrets_parser.add_argument('--target-name', '-t', help='grab recipients from target name')
    secrets_parser.add_argument('--inventory-path',
                                default=from_dot_kapitan('secrets', 'inventory-path', './inventory'),
                                help='set inventory path, default is "./inventory"')
    secrets_parser.add_argument('--recipients', '-R', help='set recipients',
                                type=str, nargs='+',
                                default=from_dot_kapitan('secrets', 'recipients', []),
                                metavar='RECIPIENT')
    secrets_parser.add_argument('--secrets-path', help='set secrets path, default is "./secrets"',
                                default=from_dot_kapitan('secrets', 'secrets-path', './secrets'))
    secrets_parser.add_argument('--backend', help='set secrets backend, default is "gpg"',
                                type=str, choices=('gpg',),
                                default=from_dot_kapitan('secrets', 'backend', 'gpg'))
    secrets_parser.add_argument('--verbose', '-v',
                                help='set verbose mode (warning: this will show sensitive data)',
                                action='store_true',
                                default=from_dot_kapitan('secrets', 'verbose', False))
    secrets_parser.add_argument('--no-verify', help='do not verify secret hashes on reveal',
                                action='store_true',
                                default=from_dot_kapitan('secrets', 'no-verify', False))

    args = parser.parse_args()

    logger.debug('Running with args: %s', args)

    try:
        cmd = sys.argv[1]
    except IndexError:
        parser.print_help()
        sys.exit(1)

    if cmd == 'eval':
        file_path = args.jsonnet_file
        search_paths = [os.path.abspath(path) for path in args.search_paths]
        ext_vars = {}
        if args.vars:
            ext_vars = dict(var.split('=') for var in args.vars)
        json_output = None
        _search_imports = lambda cwd, imp: search_imports(cwd, imp, search_paths)
        json_output = jsonnet_file(file_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks(search_paths),
                                   ext_vars=ext_vars)
        if args.output == 'yaml':
            json_obj = json.loads(json_output)
            yaml.safe_dump(json_obj, sys.stdout, default_flow_style=False)
        elif json_output:
            print(json_output)

    elif cmd == 'compile':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        elif args.quiet:
            logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        search_paths = [os.path.abspath(path) for path in args.search_paths]

        if not args.ignore_version_check:
            check_version()

        compile_targets(args.inventory_path, search_paths, args.output_path,
                        args.parallelism, args.targets,
                        prune=(args.prune), secrets_path=args.secrets_path,
                        secrets_reveal=args.reveal, indent=args.indent,
                        force_recompile=args.force_recompile)

    elif cmd == 'inventory':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        if args.pattern and args.target_name == '':
            parser.error("--pattern requires --target_name")
        try:
            inv = inventory_reclass(args.inventory_path)
            if args.target_name != '':
                inv = inv['nodes'][args.target_name]
                if args.pattern != '':
                    pattern = args.pattern.split(".")
                    inv = deep_get(inv, pattern)
            if args.flat:
                inv = flatten_dict(inv)
                yaml.dump(inv, sys.stdout, width=10000)
            else:
                yaml.dump(inv, sys.stdout, Dumper=PrettyDumper, default_flow_style=False)
        except Exception as e:
            if not isinstance(e, KapitanError):
                logger.error("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                traceback.print_exc()
            sys.exit(1)

    elif cmd == 'searchvar':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        searchvar(args.searchvar, args.inventory_path, args.pretty_print)

    elif cmd == 'secrets':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        if args.write is not None:
            if args.file is None:
                parser.error('--file is required with --write')
            data = None
            recipients = [dict((("name", name),)) for name in args.recipients]
            if args.target_name:
                inv = inventory_reclass(args.inventory_path)
                recipients = inv['nodes'][args.target_name]['parameters']['kapitan']['secrets']['recipients']
            if args.file == '-':
                data = ''
                for line in sys.stdin:
                    data += line
            else:
                with open(args.file) as fp:
                    data = fp.read()
            secret_gpg_write(args.secrets_path, args.write, data, args.base64, recipients)
        elif args.reveal:
            if args.file is None:
                parser.error('--file is required with --reveal')
            if args.file == '-':
                secret_gpg_reveal_raw(args.secrets_path, None, verify=(not args.no_verify))
            elif args.file:
                if os.path.isfile(args.file):
                    out = secret_gpg_reveal_file(args.secrets_path, args.file,
                                                 verify=(not args.no_verify))
                    sys.stdout.write(out)
                elif os.path.isdir(args.file):
                    secret_gpg_reveal_dir(args.secrets_path, args.file,
                                          verify=(not args.no_verify))
        elif args.update:
            # update recipients for secret tag
            recipients = [dict([("name", name), ]) for name in args.recipients]
            if args.target_name:
                inv = inventory_reclass(args.inventory_path)
                recipients = inv['nodes'][args.target_name]['parameters']['kapitan']['secrets']['recipients']
            secret_gpg_update_recipients(args.secrets_path, args.update, recipients)
        elif args.update_targets or args.validate_targets:
            # update recipients for all secrets in secrets_path
            # use --secrets-path to set scanning path
            inv = inventory_reclass(args.inventory_path)
            targets = set(inv['nodes'].keys())
            secrets_path = os.path.abspath(args.secrets_path)
            target_token_paths = search_target_token_paths(secrets_path, targets)
            ret_code = 0
            for target_name, token_paths in target_token_paths.items():
                try:
                    recipients = inv['nodes'][target_name]['parameters']['kapitan']['secrets']['recipients']
                    for token_path in token_paths:
                        target_fingerprints = set(lookup_fingerprints(recipients))
                        secret_fingerprints = set(secret_gpg_raw_read_fingerprints(secrets_path, token_path))
                        if target_fingerprints != secret_fingerprints:
                            if args.validate_targets:
                                logger.info("%s recipient mismatch", token_path)
                                ret_code = 1
                            else:
                                new_recipients = [dict([("fingerprint", f), ]) for f in target_fingerprints]
                                secret_gpg_update_recipients(secrets_path, token_path, new_recipients)
                except KeyError:
                    logger.debug("secret_gpg_update_target: target: %s has no inventory recipients, skipping",
                                 target_name)
            sys.exit(ret_code)
