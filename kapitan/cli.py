#!/usr/bin/python
#
# Copyright 2017 The Kapitan Authors
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

import argparse
import json
import logging
import os
import sys
from functools import partial
import multiprocessing
import yaml

from kapitan.utils import jsonnet_file, PrettyDumper, flatten_dict, searchvar
from kapitan.targets import compile_target_file
from kapitan.resources import search_imports, resource_callbacks, inventory_reclass
from kapitan.version import PROJECT_NAME, DESCRIPTION, VERSION
from kapitan.secrets import secret_gpg_backend, secret_gpg_write, secret_gpg_reveal

logger = logging.getLogger(__name__)


def main():
    "main function for command line usage"
    parser = argparse.ArgumentParser(prog=PROJECT_NAME,
                                     description=DESCRIPTION)
    parser.add_argument('--version', action='version', version=VERSION)
    subparser = parser.add_subparsers(help="commands")

    eval_parser = subparser.add_parser('eval', help='evaluate jsonnet file')
    eval_parser.add_argument('jsonnet_file', type=str)
    eval_parser.add_argument('--output', type=str,
                             choices=('yaml', 'json'), default='yaml',
                             help='set output format, default is "yaml"')
    eval_parser.add_argument('--vars', type=str, default=[], nargs='*',
                             metavar='VAR',
                             help='set variables')
    eval_parser.add_argument('--search-path', '-J', type=str, default='.',
                             metavar='JPATH',
                             help='set search path, default is "."')

    compile_parser = subparser.add_parser('compile', help='compile target files')
    compile_parser.add_argument('--target-file', '-f', type=str, nargs='+', default=[],
                                metavar='TARGET', help='target files')
    compile_parser.add_argument('--search-path', '-J', type=str, default='.',
                                metavar='JPATH',
                                help='set search path, default is "."')
    compile_parser.add_argument('--verbose', '-v', help='set verbose mode',
                                action='store_true', default=False)
    compile_parser.add_argument('--no-prune', help='do not prune jsonnet output',
                                action='store_true', default=False)
    compile_parser.add_argument('--quiet', help='set quiet mode, only critical output',
                                action='store_true', default=False)
    compile_parser.add_argument('--output-path', type=str, default='compiled',
                                metavar='PATH',
                                help='set output path, default is "./compiled"')
    compile_parser.add_argument('--parallelism', '-p', type=int,
                                default=4, metavar='INT',
                                help='Number of concurrent compile processes, default is 4')
    compile_parser.add_argument('--secrets-path', help='set secrets path, default is "./secrets"',
                                default='./secrets',)

    inventory_parser = subparser.add_parser('inventory', help='show inventory')
    inventory_parser.add_argument('--target-name', '-t', default='',
                                  help='set target name, default is all targets')
    inventory_parser.add_argument('--inventory-path', default='./inventory',
                                  help='set inventory path, default is "./inventory"')
    inventory_parser.add_argument('--flat', '-F', help='flatten nested inventory variables',
                                  action='store_true', default=False)

    searchvar_parser = subparser.add_parser('searchvar',
                                            help='show all inventory files where var is declared')
    searchvar_parser.add_argument('searchvar', type=str, metavar='VARNAME',
                                  help='flattened full variable name. Example: ' +
                                  'parameters.cluster.type')
    searchvar_parser.add_argument('--inventory-path', default='./inventory',
                                  help='set inventory path, default is "./inventory"')

    secrets_parser = subparser.add_parser('secrets', help='manage secrets')
    secrets_parser.add_argument('--write', '-w', help='write secret token',
                                metavar='TOKENNAME',)
    secrets_parser.add_argument('--reveal', '-r', help='reveal secrets',
                                action='store_true', default=False)
    secrets_parser.add_argument('--file', '-f', help='read file, set "-" for stdin',
                                required=True, metavar='FILENAME')
    secrets_parser.add_argument('--target-name', '-t', help='grab recipients from target name')
    secrets_parser.add_argument('--inventory-path', default='./inventory',
                                help='set inventory path, default is "./inventory"')
    secrets_parser.add_argument('--recipients', '-R', help='set recipients',
                                type=str, nargs='+', default=[], metavar='RECIPIENT')
    secrets_parser.add_argument('--secrets-path', help='set secrets path, default is "./secrets"',
                                default='./secrets',)
    secrets_parser.add_argument('--backend', help='set secrets backend, default is "gpg"',
                                type=str, choices=('gpg',), default='gpg')
    secrets_parser.add_argument('--verbose', '-v',
                                help='set verbose mode (warning: this will show sensitive data)',
                                action='store_true', default=False)

    args = parser.parse_args()

    logger.debug('Running with args: %s', args)

    cmd = sys.argv[1]
    if cmd == 'eval':
        file_path = args.jsonnet_file
        search_path = os.path.abspath(args.search_path)
        ext_vars = {}
        if args.vars:
            ext_vars = dict(var.split('=') for var in args.vars)
        json_output = None
        _search_imports = lambda cwd, imp: search_imports(cwd, imp, search_path)
        json_output = jsonnet_file(file_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks(search_path),
                                   ext_vars=ext_vars)
        if args.output == 'yaml':
            json_obj = json.loads(json_output)
            yaml_output = yaml.safe_dump(json_obj, default_flow_style=False)
            print yaml_output
        elif json_output:
            print json_output
    elif cmd == 'compile':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        elif args.quiet:
            logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")
        search_path = os.path.abspath(args.search_path)
        if args.target_file:
            pool = multiprocessing.Pool(args.parallelism)
            worker = partial(compile_target_file,
                             search_path=search_path,
                             output_path=args.output_path,
                             prune=(not args.no_prune),
                             secrets_path=args.secrets_path)
            try:
                pool.map(worker, args.target_file)
            except RuntimeError:
                # if compile worker fails, terminate immediately
                pool.terminate()
                raise
        else:
            logger.error("Nothing to compile")
    elif cmd == 'inventory':
        inv = inventory_reclass(args.inventory_path)
        if args.target_name != '':
            inv = inv['nodes'][args.target_name]
        if args.flat:
            inv = flatten_dict(inv)
            print yaml.dump(inv, width=10000)
        else:
            print yaml.dump(inv, Dumper=PrettyDumper, default_flow_style=False)
    elif cmd == 'searchvar':
        searchvar(args.searchvar, args.inventory_path)
    elif cmd == 'secrets':
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")
        gpg_obj = secret_gpg_backend()
        if args.write is not None:
            data = None
            recipients = args.recipients
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
            secret_gpg_write(gpg_obj, args.secrets_path, args.write, data, recipients)
        elif args.reveal:
            if args.file == '-':
                secret_gpg_reveal(gpg_obj, args.secrets_path, None)
            elif args.file:
                # TODO if it is a directory, reveal every file there
                with open(args.file) as fp:
                    secret_gpg_reveal(gpg_obj, args.secrets_path, args.file)
