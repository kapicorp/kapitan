#!/usr/bin/env python3
#
# Copyright 2019 The Kapitan Authors
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
import base64
import json
import logging
import os
import sys

import yaml
from kapitan.errors import KapitanError, RefHashMismatchError
from kapitan.initialiser import initialise_skeleton
from kapitan.lint import start_lint
from kapitan.refs.base import Ref, RefController, Revealer
from kapitan.refs.secrets.awskms import AWSKMSSecret
from kapitan.refs.secrets.gkms import GoogleKMSSecret
from kapitan.refs.secrets.gpg import GPGSecret, lookup_fingerprints
from kapitan.resources import (inventory_reclass, resource_callbacks,
                               search_imports)
from kapitan.targets import compile_targets
from kapitan.utils import (PrettyDumper, check_version, deep_get, fatal_error,
                           flatten_dict, from_dot_kapitan, jsonnet_file,
                           search_target_token_paths, searchvar)
from kapitan.version import DESCRIPTION, PROJECT_NAME, VERSION

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
                                default=from_dot_kapitan('compile', 'search-paths', ['.', 'lib']),
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
    compile_parser.add_argument('--cache', '-c',
                                help='enable compilation caching to .kapitan_cache, default is False',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'cache', False))
    compile_parser.add_argument('--cache-paths', type=str, nargs='+',
                                default=from_dot_kapitan('compile', 'cache-paths', []),
                                metavar='PATH',
                                help='cache additional paths to .kapitan_cache, default is []')
    compile_parser.add_argument('--ignore-version-check',
                                help='ignore the version from .kapitan',
                                action='store_true',
                                default=from_dot_kapitan('compile', 'ignore-version-check', False))

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
    secrets_parser.add_argument('--recipients', '-R', help='set GPG recipients',
                                type=str, nargs='+',
                                default=from_dot_kapitan('secrets', 'recipients', []),
                                metavar='RECIPIENT')
    secrets_parser.add_argument('--key', '-K', help='set KMS key',
                                default=from_dot_kapitan('secrets', 'key', ''),
                                metavar='KEY')
    secrets_parser.add_argument('--secrets-path', help='set secrets path, default is "./secrets"',
                                default=from_dot_kapitan('secrets', 'secrets-path', './secrets'))
    secrets_parser.add_argument('--verbose', '-v',
                                help='set verbose mode (warning: this will show sensitive data)',
                                action='store_true',
                                default=from_dot_kapitan('secrets', 'verbose', False))

    lint_parser = subparser.add_parser('lint', help='linter for inventory and secrets')
    lint_parser.add_argument('--fail-on-warning',
                             default=from_dot_kapitan('lint', 'fail-on-warning', False),
                             action='store_true',
                             help='exit with failure code if warnings exist, default is False')
    lint_parser.add_argument('--skip-class-checks',
                             action='store_true',
                             help='skip checking for unused classes, default is False',
                             default=from_dot_kapitan('lint', 'skip-class-checks', False))
    lint_parser.add_argument('--skip-yamllint',
                             action='store_true',
                             help='skip running yamllint on inventory, default is False',
                             default=from_dot_kapitan('lint', 'skip-yamllint', False))
    lint_parser.add_argument('--search-secrets',
                             default=from_dot_kapitan('lint', 'search-secrets', False),
                             action='store_true',
                             help='searches for plaintext secrets in inventory, default is False')
    lint_parser.add_argument('--secrets-path',
                             help='set secrets path, default is "./secrets"',
                             default=from_dot_kapitan('lint', 'secrets-path', './secrets'))
    lint_parser.add_argument('--compiled-path',
                             default=from_dot_kapitan('lint', 'compiled-path', './compiled'),
                             help='set compiled path, default is "./compiled"')
    lint_parser.add_argument('--inventory-path',
                             default=from_dot_kapitan('lint', 'inventory-path', './inventory'),
                             help='set inventory path, default is "./inventory"')

    init_parser = subparser.add_parser('init', help='initialize a directory with the recommended kapitan project skeleton.')
    init_parser.add_argument('--directory',
                             default=from_dot_kapitan('init', 'directory', '.'),
                             help='set path, in which to generate the project skeleton, assumes directory already exists. default is "./"')

    args = parser.parse_args()

    logger.debug('Running with args: %s', args)

    try:
        cmd = sys.argv[1]
    except IndexError:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, 'verbose') and args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    elif hasattr(args, 'quiet') and args.quiet:
        logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if cmd == 'eval':
        file_path = args.jsonnet_file
        search_paths = [os.path.abspath(path) for path in args.search_paths]
        ext_vars = {}
        if args.vars:
            ext_vars = dict(var.split('=') for var in args.vars)
        json_output = None

        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, search_paths)

        json_output = jsonnet_file(file_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks(search_paths),
                                   ext_vars=ext_vars)
        if args.output == 'yaml':
            json_obj = json.loads(json_output)
            yaml.safe_dump(json_obj, sys.stdout, default_flow_style=False)
        elif json_output:
            print(json_output)

    elif cmd == 'compile':
        search_paths = [os.path.abspath(path) for path in args.search_paths]

        if not args.ignore_version_check:
            check_version()

        ref_controller = RefController(args.secrets_path)

        compile_targets(args.inventory_path, search_paths, args.output_path,
                        args.parallelism, args.targets, ref_controller,
                        prune=(args.prune), indent=args.indent, reveal=args.reveal,
                        cache=args.cache, cache_paths=args.cache_paths)

    elif cmd == 'inventory':
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
                yaml.dump(inv, sys.stdout, width=10000, default_flow_style=False)
            else:
                yaml.dump(inv, sys.stdout, Dumper=PrettyDumper, default_flow_style=False)
        except Exception as e:
            if not isinstance(e, KapitanError):
                logger.exception("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            sys.exit(1)

    elif cmd == 'searchvar':
        searchvar(args.searchvar, args.inventory_path, args.pretty_print)

    elif cmd == 'lint':
        start_lint(args.fail_on_warning, args.skip_class_checks, args.skip_yamllint, args.inventory_path, args.search_secrets, args.secrets_path, args.compiled_path)

    elif cmd == 'init':
        initialise_skeleton(args.directory)

    elif cmd == 'secrets':
        ref_controller = RefController(args.secrets_path)

        if args.write is not None:
            secret_write(args, ref_controller)
        elif args.reveal:
            secret_reveal(args, ref_controller)
        elif args.update:
            secret_update(args, ref_controller)
        elif args.update_targets or args.validate_targets:
            secret_update_validate(args, ref_controller)


def secret_write(args, ref_controller):
    "Write secret to ref_controller based on cli args"
    token_name = args.write
    file_name = args.file
    data = None

    if file_name is None:
        fatal_error('--file is required with --write')
    if file_name == '-':
        data = ''
        for line in sys.stdin:
            data += line
    else:
        with open(file_name) as fp:
            data = fp.read()

    if token_name.startswith("gpg:"):
        type_name, token_path = token_name.split(":")
        recipients = [dict((("name", name),)) for name in args.recipients]
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            recipients = kap_inv_params['secrets']['gpg']['recipients']
        if not recipients:
            raise KapitanError("No GPG recipients specified. Use --recipients or specify them in " +
                               "parameters.kapitan.secrets.gpg.recipients and use --target")
        secret_obj = GPGSecret(data, recipients, encode_base64=args.base64)
        tag = '?{{gpg:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("gkms:"):
        type_name, token_path = token_name.split(":")
        key = args.key
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params['secrets']['gkms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target")
        secret_obj = GoogleKMSSecret(data, key, encode_base64=args.base64)
        tag = '?{{gkms:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        type_name, token_path = token_name.split(":")
        key = args.key
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params['secrets']['awskms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target")
        secret_obj = AWSKMSSecret(data, key, encode_base64=args.base64)
        tag = '?{{awskms:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("ref:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = 'original'
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = 'base64'
        ref_obj = Ref(_data, encoding=encoding)
        tag = '?{{ref:{}}}'.format(token_path)
        ref_controller[tag] = ref_obj

    else:
        fatal_error("Invalid token: {name}. Try using gpg/gkms/awskms/ref:{name}".format(name=token_name))


def secret_update(args, ref_controller):
    "Update secret gpg recipients/gkms/awskms key"
    # TODO --update *might* mean something else for other types
    token_name = args.update
    if token_name.startswith("gpg:"):
        # args.recipients is a list, convert to recipients dict
        recipients = [dict([("name", name), ]) for name in args.recipients]
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            recipients = kap_inv_params['secrets']['gpg']['recipients']
        if not recipients:
            raise KapitanError("No GPG recipients specified. Use --recipients or specify them in " +
                               "parameters.kapitan.secrets.gpg.recipients and use --target")
        type_name, token_path = token_name.split(":")
        tag = '?{{gpg:{}}}'.format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_recipients(recipients)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("gkms:"):
        key = args.key
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params['secrets']['gkms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target")
        type_name, token_path = token_name.split(":")
        tag = '?{{gkms:{}}}'.format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        key = args.key
        if args.target_name:
            inv = inventory_reclass(args.inventory_path)
            kap_inv_params = inv['nodes'][args.target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(args.target_name))

            key = kap_inv_params['secrets']['awskms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target")
        type_name, token_path = token_name.split(":")
        tag = '?{{awskms:{}}}'.format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    else:
        fatal_error("Invalid token: {name}. Try using gpg/gkms/awskms:{name}".format(name=token_name))


def secret_reveal(args, ref_controller):
    "Reveal secrets in file_name"
    revealer = Revealer(ref_controller)
    file_name = args.file
    if file_name is None:
        fatal_error('--file is required with --reveal')
    try:
        if file_name == '-':
            out = revealer.reveal_raw_file(None)
            sys.stdout.write(out)
        elif file_name:
            for rev_obj in revealer.reveal_path(file_name):
                sys.stdout.write(rev_obj.content)
    except (RefHashMismatchError, KeyError):
        raise KapitanError("Reveal failed for file {name}".format(name=file_name))


def secret_update_validate(args, ref_controller):
    "Validate and/or update target secrets"
    # update gpg recipients/gkms/awskms key for all secrets in secrets_path
    # use --secrets-path to set scanning path
    inv = inventory_reclass(args.inventory_path)
    targets = set(inv['nodes'].keys())
    secrets_path = os.path.abspath(args.secrets_path)
    target_token_paths = search_target_token_paths(secrets_path, targets)
    ret_code = 0

    for target_name, token_paths in target_token_paths.items():
        kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
        if 'secrets' not in kap_inv_params:
            raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

        try:
            recipients = kap_inv_params['secrets']['gpg']['recipients']
        except KeyError:
            recipients = None
        try:
            gkey = kap_inv_params['secrets']['gkms']['key']
        except KeyError:
            gkey = None
        try:
            awskey = kap_inv_params['secrets']['awskms']['key']
        except KeyError:
            awskey = None

        for token_path in token_paths:
            if token_path.startswith("?{gpg:"):
                if not recipients:
                    logger.debug("secret_update_validate: target: %s has no inventory gpg recipients, skipping %s", target_name, token_path)
                    continue
                secret_obj = ref_controller[token_path]
                target_fingerprints = set(lookup_fingerprints(recipients))
                secret_fingerprints = set(lookup_fingerprints(secret_obj.recipients))
                if target_fingerprints != secret_fingerprints:
                    if args.validate_targets:
                        logger.info("%s recipient mismatch", token_path)
                        to_remove = secret_fingerprints.difference(target_fingerprints)
                        to_add = target_fingerprints.difference(secret_fingerprints)
                        if to_remove:
                            logger.info("%s needs removal", to_remove)
                        if to_add:
                            logger.info("%s needs addition", to_add)
                        ret_code = 1
                    else:
                        new_recipients = [dict([("fingerprint", f), ]) for f in target_fingerprints]
                        secret_obj.update_recipients(new_recipients)
                        ref_controller[token_path] = secret_obj

            elif token_path.startswith("?{gkms:"):
                if not gkey:
                    logger.debug("secret_update_validate: target: %s has no inventory gkms key, skipping %s", target_name, token_path)
                    continue
                secret_obj = ref_controller[token_path]
                if gkey != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(gkey)
                        ref_controller[token_path] = secret_obj

            elif token_path.startswith("?{awskms:"):
                if not awskey:
                    logger.debug("secret_update_validate: target: %s has no inventory awskms key, skipping %s", target_name, token_path)
                    continue
                secret_obj = ref_controller[token_path]
                if awskey != secret_obj.key:
                    if args.validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(awskey)
                        ref_controller[token_path] = secret_obj

            else:
                logger.info("Invalid secret %s, could not get type, skipping", token_path)
                ret_code = 1

    sys.exit(ret_code)
