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
import fire

import yaml

from collections import namedtuple
from kapitan import cached
from kapitan.errors import KapitanError, RefHashMismatchError
from kapitan.initialiser import initialise_skeleton
from kapitan.lint import start_lint
from kapitan.refs.base import PlainRef, RefController, Revealer
from kapitan.refs.base64 import Base64Ref
from kapitan.refs.secrets.awskms import AWSKMSSecret
from kapitan.refs.secrets.gkms import GoogleKMSSecret
from kapitan.refs.secrets.gpg import GPGSecret, lookup_fingerprints
from kapitan.resources import (inventory_reclass, resource_callbacks,
                               search_imports)
from kapitan.targets import compile_targets, schema_validate_compiled
from kapitan.inputs.jinja2_filters import DEFAULT_JINJA2_FILTERS_PATH
from kapitan.utils import (PrettyDumper, check_version, deep_get, fatal_error,
                           flatten_dict, from_dot_kapitan, jsonnet_file,
                           search_target_token_paths, searchvar as search_var,
                           parse_arg_delimiter)
from kapitan.version import DESCRIPTION, PROJECT_NAME, VERSION

logger = logging.getLogger(__name__)


class KapitanCLI():
    '''
    Generic templated configuration management for Kubernetes, Terraform and other things
    '''

    def __init__(self, version=False):
        if version:
            print(VERSION)
            sys.exit(0)
        try:
            cmd = sys.argv[1]
            logger.debug('Running with command: %s', cmd)
        except IndexError:
            sys.exit(1)

    def eval(self, jsonnet_file, search_paths=from_dot_kapitan('eval', 'search-paths', ['.']),
             vars=from_dot_kapitan('eval', 'vars', []),
             output=from_dot_kapitan('eval', 'output', 'yaml')):
        '''
        evaluate jsonnet file

        Attributes:
            jsonnet_file : str
                file to evaluate
            search_paths : str
                set search paths, default is ["."], use comma(,) separated paths like --search-paths=path1,path2,...
            vars : str
                set variables, use comma(,) separated values, eg. --vars var1=val1,var2=val2,...
            output : str
                set output format, default is "yaml"        
        '''

        cached.args[sys.argv[1]] = locals()
        if output not in ['yaml', 'json']:
            fatal_error('Only yaml and json are supported currently')

        if isinstance(search_paths, bool):
            fatal_error('expected at least one argument')

        file_path = jsonnet_file
        search_paths = parse_arg_delimiter(search_paths, ',', is_a_path=True)
        ext_vars = {}
        if vars:
            ext_vars = dict(var.split('=') for var in parse_arg_delimiter(vars, ','))
        json_output = None

        def _search_imports(cwd, imp):
            return search_imports(cwd, imp, search_paths)

        json_output = jsonnet_file(file_path, import_callback=_search_imports,
                                   native_callbacks=resource_callbacks(search_paths),
                                   ext_vars=ext_vars)
        if output == 'yaml':
            json_obj = json.loads(json_output)
            yaml.safe_dump(json_obj, sys.stdout, default_flow_style=False)
        elif json_output:
            print(json_output)

    def compile(self, search_paths=from_dot_kapitan('compile', 'search-paths', ['.', 'lib']),
                jinja2_filters=from_dot_kapitan('compile', 'jinja2-filters', DEFAULT_JINJA2_FILTERS_PATH),
                verbose=from_dot_kapitan('compile', 'verbose', False),
                prune=from_dot_kapitan('compile', 'prune', False),
                quiet=from_dot_kapitan('compile', 'quiet', False),
                output_path=from_dot_kapitan('compile', 'output-path', '.'),
                fetch=from_dot_kapitan('compile', 'fetch', False),
                validate=from_dot_kapitan('compile', 'validate', False),
                targets=from_dot_kapitan('compile', 'targets', []),
                parallelism=from_dot_kapitan('compile', 'parallelism', 4),
                indent=from_dot_kapitan('compile', 'indent', 2),
                refs_path=from_dot_kapitan('compile', 'refs-path', './refs'),
                reveal=from_dot_kapitan('compile', 'reveal', False),
                inventory_path=from_dot_kapitan('compile', 'inventory-path', './inventory'),
                cache=from_dot_kapitan('compile', 'cache', False),
                cache_paths=from_dot_kapitan('compile', 'cache-paths', []),
                ignore_version_check=from_dot_kapitan('compile', 'ignore-version-check', False),
                schemas_path=from_dot_kapitan('validate', 'schemas-path', './schemas')):
        '''
        compile targets

        Attributes:
            search_paths : str
                set search paths, default is ["."], use comma(,) separated paths like --search-paths=path1,path2,...
            jinja2_filters : str
                load custom jinja2 filters from any file, default is to put them inside lib/jinja2_filters.py
            verbose : bool
                set verbose mode
            prune : bool
                prune jsonnet output
            quiet : bool
                set quiet mode, only critical output
            output_path : str
                set output path, default is "."
            fetch : bool
                fetches external dependencies
            validate : bool
                validate compile output against schemas as specified in inventory
            targets : str
                targets to compile, default is all, use comma(,) separated targets like --targets=tar1,tar2...
            parallelism : int
                Number of concurrent compile processes, default is 4
            indent : int
                Indentation spaces for YAML/JSON, default is 2
            refs_path : str
                set refs path, default is "./refs"
            reveal : bool
                reveal refs (warning: this will potentially write sensitive data)
            inventory_path : bool
                set inventory path, default is "./inventory"
            cache : bool
                enable compilation caching to .kapitan_cache, default is False
            cache_paths : str
                cache additional paths to .kapitan_cache, default is [], use comma(,) separated paths like --cache-paths=path1,path2,...
            ignore_version_check : bool
                ignore the version from .kapitan
            schemas_path : str
                set schema cache path, default is "./schemas"
        '''

        cached.args[sys.argv[1]] = locals()
        if verbose:
            logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        elif quiet:
            logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        search_paths = parse_arg_delimiter(search_paths, ',', is_a_path=True)

        if not ignore_version_check:
            check_version()

        ref_controller = RefController(refs_path)
        # cache controller for use in reveal_maybe jinja2 filter
        cached.ref_controller_obj = ref_controller
        cached.revealer_obj = Revealer(ref_controller)

        compile_targets(inventory_path, search_paths, output_path,
                        parallelism, parse_arg_delimiter(targets, ','), ref_controller,
                        prune=(prune), indent=indent, reveal=reveal,
                        cache=cache, cache_paths=parse_arg_delimiter(cache_paths, ',', is_a_path=True),
                        fetch_dependencies=fetch, validate=validate,
                        schemas_path=schemas_path,
                        jinja2_filters=jinja2_filters)

    def inventory(self, target_name=from_dot_kapitan('inventory', 'target-name', ''),
                  inventory_path=from_dot_kapitan('inventory', 'inventory-path', './inventory'),
                  flat=from_dot_kapitan('inventory', 'flat', False),
                  pattern=from_dot_kapitan('inventory', 'pattern', ''),
                  verbose=from_dot_kapitan('inventory', 'verbose', False)):
        '''
        show inventory

        Attributes:
            target_name : str
                set target name, default is all targets
            inventory_path : str
                set inventory path, default is "./inventory"
            flat : bool
                flatten nested inventory variables
            pattern : str
                filter pattern (e.g. parameters.mysql.storage_class, or storage_class, or storage_*), default is ""
            verbose : bool
                set verbose mode
        '''

        cached.args[sys.argv[1]] = locals()
        if verbose:
            logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        if pattern and target_name == '':
            fatal_error("--pattern requires --target_name")

        try:
            inv = inventory_reclass(inventory_path)
            if target_name != '':
                inv = inv['nodes'][target_name]
                if pattern != '':
                    pattern = pattern.split(".")
                    inv = deep_get(inv, pattern)
            if flat:
                inv = flatten_dict(inv)
                yaml.dump(inv, sys.stdout, width=10000, default_flow_style=False)
            else:
                yaml.dump(inv, sys.stdout, Dumper=PrettyDumper, default_flow_style=False)
        except Exception as e:
            if not isinstance(e, KapitanError):
                logger.exception("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            sys.exit(1)

    def searchvar(self, searchvar, inventory_path=from_dot_kapitan('searchvar', 'inventory-path', './inventory'),
                  verbose=from_dot_kapitan('searchvar', 'verbose', False),
                  pretty_print=from_dot_kapitan('searchvar', 'pretty-print', False)):
        '''
        show all inventory files where var is declared
        
        Attributes:
            searchvar : str
                e.g. parameters.mysql.storage_class, or storage_class, or storage_*
            inventory_path : str
                set inventory path, default is "./inventory"
            verbose : bool
                set verbose mode
            pretty_print : bool
                Pretty print content of var
        '''
        
        cached.args[sys.argv[1]] = locals()
        if verbose:
            logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        search_var(searchvar, inventory_path, pretty_print)

    def secrets(self):
        '''
        (DEPRECATED) please use refs

        '''
        
        cached.args[sys.argv[1]] = locals()
        logger.error("Secrets have been renamed to refs, please refer to: '$ kapitan refs --help'")
        sys.exit(1)
    
    def refs(self, write=None, update=None, file=None, target_name=None,
             update_targets=from_dot_kapitan('refs', 'update-targets', False),
             validate_targets=from_dot_kapitan('refs', 'validate-targets', False),
             base64=from_dot_kapitan('refs', 'base64', False),
             reveal=from_dot_kapitan('refs', 'reveal', False),
             inventory_path=from_dot_kapitan('refs', 'inventory-path', './inventory'),
             recipients=from_dot_kapitan('refs', 'recipients', []),
             key=from_dot_kapitan('refs', 'key', ''),
             refs_path=from_dot_kapitan('refs', 'refs-path', './refs'),
             verbose=from_dot_kapitan('refs', 'verbose', False)):
        '''
        manage refs

        Attributes:
            write : str
                write ref token
            update : str
                update GPG recipients for ref token
            update_targets : bool
                update target secret refs
            validate_targets : bool
                validate target secret refs
            base64 : bool
                base64 encode file content
            reveal : bool
                reveal refs
            file : str
                read file or directory, set "-" for stdin
            target_name : str
                grab recipients from target name
            inventory_path : str
                set inventory path, default is "./inventory"
            recipients : str
                set GPG recipients, use comma(,) seperated values like --recipients=rep1,rep2,...
            key : str
                set KMS key
            refs_path : str
                set refs path, default is "./refs"
            verbose : bool
                set verbose mode (warning: this will potentially show sensitive data)
        '''

        cached.args[sys.argv[1]] = locals()
        if verbose:
            logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

        args_holder = namedtuple('args_holder', ['write', 'update', 'update_targets', 'validate_targets',
                                    'base64', 'reveal', 'file', 'target_name',
                                    'inventory_path', 'recipients', 'key', 'refs_path',
                                    'verbose'])
        args = args_holder(write=write, update=update, update_targets=update_targets,
                            validate_targets=validate_targets, base64=base64, reveal=reveal,
                            file=file, target_name=target_name, inventory_path=inventory_path,
                            recipients=parse_arg_delimiter(recipients, ','),
                            key=key, refs_path=refs_path,verbose=verbose)
        
        ref_controller = RefController(args.refs_path)

        if args.write is not None:
            ref_write(args, ref_controller)
        elif args.reveal:
            ref_reveal(args, ref_controller)
        elif args.update:
            secret_update(args, ref_controller)
        elif args.update_targets or args.validate_targets:
            secret_update_validate(args, ref_controller)

    def lint(self, fail_on_warning=from_dot_kapitan('lint', 'fail-on-warning', False),
             skip_class_checks=from_dot_kapitan('lint', 'skip-class-checks', False),
             skip_yamllint=from_dot_kapitan('lint', 'skip-yamllint', False),
             search_secrets=from_dot_kapitan('lint', 'search-secrets', False),
             refs_path=from_dot_kapitan('lint', 'refs-path', './refs'),
             compiled_path=from_dot_kapitan('lint', 'compiled-path', './compiled'),
             inventory_path=from_dot_kapitan('lint', 'inventory-path', './inventory')):
        '''
        linter for inventory and refs
        
        Attributes:
            fail_on_warning : bool
                exit with failure code if warnings exist, default is False
            skip_class_checks : bool
                skip checking for unused classes, default is False
            skip_yamllint : bool
                skip running yamllint on inventory, default is False
            search_secrets : 
                searches for plaintext secrets in inventory, default is False
            refs_path : str
                set refs path, default is "./refs"
            compiled_path : str
                set compiled path, default is "./compiled"
            inventory_path : str
                set inventory path, default is "./inventory"
        '''

        cached.args[sys.argv[1]] = locals()
        start_lint(fail_on_warning, skip_class_checks, skip_yamllint, inventory_path,
                   search_secrets, refs_path, compiled_path) 

    def init(self, directory=from_dot_kapitan('init', 'directory', '.')):
        '''
        initialize a directory with the recommended kapitan project skeleton.
        
        Attributes:
            directory : str
                set path, in which to generate the project skeleton, assumes directory already exists. default is "./"
        '''

        cached.args[sys.argv[1]] = locals()
        initialise_skeleton(directory)

    def validate(self, compiled_path=from_dot_kapitan('compile', 'compiled-path', './compiled'),
                 inventory_path=from_dot_kapitan('compile', 'inventory-path', './inventory'),
                 targets=from_dot_kapitan('compile', 'targets', []),
                 schemas_path=from_dot_kapitan('validate', 'schemas-path', './schemas'),
                 parallelism=from_dot_kapitan('validate', 'parallelism', 4)):
        '''
        validates the compile output against schemas as specified in inventory

        Attributes:
            compiled_path : str
                set compiled path, default is "./compiled
            inventory_path : str
                set inventory path, default is "./inventory"
            targets : str
                targets to validate, default is all, use comma(,) separated targets like --targets=tar1,tar2,...
            schemas_path : str
                set schema cache path, default is "./schemas"
            parallelism : int
                Number of concurrent validate processes, default is 4
        '''

        cached.args[sys.argv[1]] = locals()
        schema_validate_compiled(targets, inventory_path=inventory_path, compiled_path=compiled_path,
                                 schema_cache_path=schemas_path, parallel=parallelism)


def main():
    """main function for command line usage"""
    fire.Fire(KapitanCLI)


def ref_write(args, ref_controller):
    "Write ref to ref_controller based on cli args"
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

    elif token_name.startswith("base64:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = 'original'
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = 'base64'
        ref_obj = Base64Ref(_data, encoding=encoding)
        tag = '?{{base64:{}}}'.format(token_path)
        ref_controller[tag] = ref_obj

    elif token_name.startswith("plain:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = 'original'
        if args.base64:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = 'base64'
        ref_obj = PlainRef(_data, encoding=encoding)
        tag = '?{{plain:{}}}'.format(token_path)
        ref_controller[tag] = ref_obj

    else:
        fatal_error("Invalid token: {name}. Try using gpg/gkms/awskms/base64/plain:{name}".format(name=token_name))


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


def ref_reveal(args, ref_controller):
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
    # use --refs-path to set scanning path
    inv = inventory_reclass(args.inventory_path)
    targets = set(inv['nodes'].keys())
    secrets_path = os.path.abspath(args.refs_path)
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
