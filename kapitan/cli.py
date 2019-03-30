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
                           search_target_token_paths, searchvars, parse_arg_delimiter)
from kapitan.version import DESCRIPTION, PROJECT_NAME, VERSION

logger = logging.getLogger(__name__)

class KapitanCLI():
    """
    Kapitan : Generic templated configuration management for Kubernetes, Terraform and other things
    """
    def __init__(self, version=False):
        if version:
            print(VERSION)
            sys.exit(1)

        logging.basicConfig(level=logging.INFO, format="%(message)s")
        
        try:
            cmd = sys.argv[1]
        except IndexError:
            print("Usage Options:")
            print("kapitan -- --help")
            print("kapitan x -- --help where x = {init, eval, compile, inventory, lint, secrets, searchvar} for help on specific option")
            sys.exit(1)

    def eval(self, jsonnet_file, output=from_dot_kapitan('eval', 'output', 'yaml'),
            vars=from_dot_kapitan('eval', 'vars', []), 
            search_paths=from_dot_kapitan('eval', 'search-paths', '.')):
        '''
        evaluate jsonnet file

        jsonnet_file : str
            file to eval
        output : str
            set output format, default is "yaml", only ["yaml", "json"] supported
        vars : str
            set variables, use comma(,) separated values, eg. --vars var1=val1,var2=val2,...
        search_paths : str
            set search paths, use comma(,) separated paths like --search-paths=path1,path2,...
        '''
        if output not in ['yaml', 'json']:
            fatal_error('Only yaml and json are supported currently')
        
        if isinstance(search_paths, bool):
            fatal_error("expected at least one argument")
        
        file_path = jsonnet_file
        search_paths = parse_arg_delimiter(search_paths, ',', is_a_path=True)
        ext_vars = {}
        if vars:
            ext_vars = dict(var.split('=') for var in vars.split(','))
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
                verbose=from_dot_kapitan('compile', 'verbose', False),
                prune=from_dot_kapitan('compile', 'prune', False),
                quiet=from_dot_kapitan('compile', 'quiet', False),
                output_path=from_dot_kapitan('compile', 'output-path', '.'),
                targets=from_dot_kapitan('compile', 'targets', []),
                parallelism=from_dot_kapitan('compile', 'parallelism', 4),
                indent=from_dot_kapitan('compile', 'indent', 2),
                secrets_path=from_dot_kapitan('compile', 'secrets-path', './secrets'),
                reveal=from_dot_kapitan('compile', 'reveal', False),
                inventory_path=from_dot_kapitan('compile', 'inventory-path', './inventory'),
                cache=from_dot_kapitan('compile', 'cache', False),
                cache_paths=from_dot_kapitan('compile', 'cache-paths', []),
                ignore_version_check=from_dot_kapitan('compile', 'ignore-version-check', False)):
        '''
        compile targets
        
        Args:
            search_paths: str
                set search paths, comma separated values like --search-paths=path1,path2,... (default is ".") 
            verbose: bool
                set verbose mode
            prune: bool
                prune jsonnet output
            quiet: bool
                set quiet mode, only critical output
            output_path: str
                set output path, default is "."
            targets: str
                targets to compile, comma separated targets like --targets=tar1,tar2,... (default is all)
            parallelism: int
                Number of concurrent compile processes, default is 4
            secrets_path: str
                set secrets path, default is "./secrets"
            reveal: bool
                reveal secrets (warning: this will write sensitive data)
            inventory_path: str
                set inventory path, default is "./inventory"
            cache: bool
                enable compilation caching to .kapitan_cache, default is False
            cache_paths: bool
                cache additional paths to .kapitan_cache, comma separated values like --cache-paths=path1,path2,... (default is [])
            ignore_version_check: bool
                ignore the version from .kapitan
        '''
        if quiet:
            logging.basicConfig(level=logging.CRITICAL, format="%(message)s")
        elif verbose:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        
        if isinstance(search_paths, bool) or isinstance(cache_paths, bool) or isinstance(targets, bool):
            fatal_error("expected at least one argument")
        
        search_paths = parse_arg_delimiter(search_paths, ",", is_a_path=True)
        cache_paths = parse_arg_delimiter(cache_paths, ",", is_a_path=True)
        targets = parse_arg_delimiter(targets, ",")
        
        if not ignore_version_check:
            check_version()

        ref_controller = RefController(secrets_path)

        compile_targets(inventory_path, search_paths, output_path,
                        parallelism, targets, ref_controller,
                        prune=(prune), indent=indent, reveal=reveal,
                        cache=cache, cache_paths=cache_paths)

    def lint(self, fail_on_warning=from_dot_kapitan('lint', 'fail-on-warning', False), 
            skip_class_checks=from_dot_kapitan('lint', 'skip-class-checks', False),
            skip_yamllint=from_dot_kapitan('lint', 'skip-yamllint', False),
            search_secrets=from_dot_kapitan('lint', 'search-secrets', False),
            secrets_path=from_dot_kapitan('lint', 'secrets-path', './secrets'),
            compiled_path=from_dot_kapitan('lint', 'compiled-path', './compiled'),
            inventory_path=from_dot_kapitan('lint', 'inventory-path', './inventory')):
        '''
        linter for inventory and secrets

        Args:
            fail_on_warning: bool
                exit with failure code if warnings exist, default is False
            skip_class_checks: bool
                skip checking for unused classes, default is False
            skip_yamllint: bool
                skip running yamllint on inventory, default is False
            search_secrets: bool
                searches for plaintext secrets in inventory, default is False
            secrets_path: str
                set secrets path, default is "./secrets"
            compiled_path: str
                set compiled path, default is "./compiled"
            inventory_path: str
                set inventory path, default is "./inventory"
        '''
        start_lint(fail_on_warning, skip_class_checks,skip_yamllint, inventory_path, search_secrets, secrets_path, compiled_path)

    def init(self, directory=from_dot_kapitan('init', 'directory', '.')):
        '''
        initialize a directory with the recommended kapitan project skeleton.

        Args:
            directory: str
                set path, in which to generate the project skeleton, assumes directory already exists. default is "./"
        '''
        initialise_skeleton(directory)

    def secrets(self, write=None, update=None, update_targets=from_dot_kapitan('secrets', 'update-targets', False), 
                validate_targets=from_dot_kapitan('secrets', 'validate-targets', False),
                b64e=from_dot_kapitan('secrets', 'base64', False),
                reveal=from_dot_kapitan('secrets', 'reveal', False),
                file=None, target_name=None, inventory_path=from_dot_kapitan('secrets', 'inventory-path', './inventory'),
                recipients=from_dot_kapitan('secrets', 'recipients', []),
                key=from_dot_kapitan('secrets', 'key', ''),
                secrets_path=from_dot_kapitan('secrets', 'secrets-path', './secrets'),
                verbose=from_dot_kapitan('secrets', 'verbose', False)):
        '''
        manage secrets

        Args:
            write: str
                write secret token
            update: str
                update recipients for secret token
            update_targets: bool
                update target secrets
            validate_targets: bool
                validate target secrets
            b64e: bool
                base64 encode file content
            reveal: bool
                reveal secrets
            file: str
                read file or directory, set "-" for stdin
            target_name: str
                grab recipients from target name
            inventory_path: str
                set inventory path, default is "./inventory"
            recipients: str
                set GPG recipients
            key: str
                set KMS key
            secrets_path: str
                set secrets path, default is "./secrets"
            verbose: bool
                set verbose mode (warning: this will show sensitive data)
        '''
        if verbose:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        
        if isinstance(recipients, bool):
            fatal_error("expected at least one argument")            
        
        recipients = parse_arg_delimiter(recipients, ",")
        
        ref_controller = RefController(secrets_path)

        if write is not None:
            secret_write(write, file, recipients, target_name, inventory_path, 
                    b64e, key, ref_controller)
        elif reveal:
            secret_reveal(file, ref_controller)
        elif update:
            secret_update(update, recipients, target_name, inventory_path, key, ref_controller)
        elif update_targets or validate_targets:
            secret_update_validate(inventory_path, secrets_path, validate_targets, ref_controller)

    def inventory(self, target_name=from_dot_kapitan('inventory', 'target-name', ''),
                inventory_path=from_dot_kapitan('inventory', 'inventory-path', './inventory'),
                flat=from_dot_kapitan('inventory', 'flat', False),
                pattern=from_dot_kapitan('inventory', 'pattern', ''),
                verbose=from_dot_kapitan('inventory', 'verbose', False)):
        '''
        show inventory

        Args:
            target_name: str
                set target name, default is all targets
            inventory_path: str
                set inventory path, default is "./inventory"
            flat: bool
                flatten nested inventory variables            
            pattern: str
                filter pattern (e.g. parameters.mysql.storage_class, or storage_class, or storage_*), default is ""
            verbose: bool
                set verbose mode
        '''
        if verbose:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        
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

        Args:
            searchvar: str
                e.g. parameters.mysql.storage_class, or storage_class, or storage_*   
            inventory_path: str
                set inventory path, default is "./inventory"
            verbose: bool
                set verbose mode
            pretty_print:
                Pretty print content of var
        '''    
        if verbose:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

        searchvars(searchvar, inventory_path, pretty_print)


def main():
    """main function for command line usage"""
    fire.Fire(KapitanCLI, name=PROJECT_NAME)


def secret_write(write, file, recipients, target_name, inventory_path, 
                 b64e, key, ref_controller):
    "Write secret to ref_controller based on cli args"
    token_name = write
    file_name = file
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
        recipients = [dict((("name", name),)) for name in recipients]
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

            recipients = kap_inv_params['secrets']['gpg']['recipients']
        if not recipients:
            raise KapitanError("No GPG recipients specified. Use --recipients or specify them in " +
                               "parameters.kapitan.secrets.gpg.recipients and use --target")

        secret_obj = GPGSecret(data, recipients, encode_base64=b64e)
        tag = '?{{gpg:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("gkms:"):
        type_name, token_path = token_name.split(":")
        key = key
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

            key = kap_inv_params['secrets']['gkms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target")
        secret_obj = GoogleKMSSecret(data, key, encode_base64=b64e)
        tag = '?{{gkms:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        type_name, token_path = token_name.split(":")
        key = key
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

            key = kap_inv_params['secrets']['awskms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.awskms.key and use --target")
        secret_obj = AWSKMSSecret(data, key, encode_base64=b64e)
        tag = '?{{awskms:{}}}'.format(token_path)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("ref:"):
        type_name, token_path = token_name.split(":")
        _data = data.encode()
        encoding = 'original'
        if b64e:
            _data = base64.b64encode(_data).decode()
            _data = _data.encode()
            encoding = 'base64'
        ref_obj = Ref(_data, encoding=encoding)
        tag = '?{{ref:{}}}'.format(token_path)
        ref_controller[tag] = ref_obj

    else:
        fatal_error("Invalid token: {name}. Try using gpg/gkms/awskms/ref:{name}".format(name=token_name))


def secret_update(update, recipients, target_name, inventory_path, key, ref_controller):
    "Update secret gpg recipients/gkms/awskms key" 
    # TODO --update *might* mean something else for other types
    token_name = update
    if token_name.startswith("gpg:"):
        # args.recipients is a list, convert to recipients dict
        recipients = [dict([("name", name), ]) for name in recipients]
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

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
        key = key
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

            key = kap_inv_params['secrets']['gkms']['key']
        if not key:
            raise KapitanError("No KMS key specified. Use --key or specify it in parameters.kapitan.secrets.gkms.key and use --target")
        type_name, token_path = token_name.split(":")
        tag = '?{{gkms:{}}}'.format(token_path)
        secret_obj = ref_controller[tag]
        secret_obj.update_key(key)
        ref_controller[tag] = secret_obj

    elif token_name.startswith("awskms:"):
        key = key
        if target_name:
            inv = inventory_reclass(inventory_path)
            kap_inv_params = inv['nodes'][target_name]['parameters']['kapitan']
            if 'secrets' not in kap_inv_params:
                raise KapitanError("parameters.kapitan.secrets not defined in {}".format(target_name))

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


def secret_reveal(file, ref_controller):
    "Reveal secrets in file_name"
    revealer = Revealer(ref_controller)
    file_name = file
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


def secret_update_validate(inventory_path, secrets_path, validate_targets, ref_controller):
    "Validate and/or update target secrets"
    # update gpg recipients/gkms/awskms key for all secrets in secrets_path
    # use --secrets-path to set scanning path
    inv = inventory_reclass(inventory_path)
    targets = set(inv['nodes'].keys())
    secrets_path = os.path.abspath(secrets_path)
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
                    if validate_targets:
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
                    if validate_targets:
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
                    if validate_targets:
                        logger.info("%s key mismatch", token_path)
                        ret_code = 1
                    else:
                        secret_obj.update_key(awskey)
                        ref_controller[token_path] = secret_obj

            else:
                logger.info("Invalid secret %s, could not get type, skipping", token_path)
                ret_code = 1

    sys.exit(ret_code)