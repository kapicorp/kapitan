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

"lint module"

import logging
from sys import exit

from kapitan.utils import get_entropy, termcolor
from kapitan.resources import inventory_reclass
from pprint import pformat

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def start_lint(fail_on_warning, skip_variable_checks, search_secrets, entropy_warn, inventory_path):
    if skip_variable_checks and not search_secrets:
        logger.info("Nothing to check. Either remove --skip-variable-checks or add --search-secrets")
        exit(0)

    if not skip_variable_checks:
        logger.info("\nInventory path:{}\n".format(inventory_path))
        logger.info("\nChecking for unused variables...\n")
        status_var_no_usage = lint_var_no_usage(inventory_path)
        logger.info("\nChecking for variable redefinition or duplicate values...\n")
        status_var_redefinition = lint_var_redefinition(inventory_path)

    status_secrets = 0
    if search_secrets:
        logger.info("\nChecking for plaintext secrets in inventory...\n")
        status_secrets = lint_secrets(entropy_warn, inventory_path)

    if fail_on_warning and (status_var_no_usage + status_var_redefinition + status_secrets) > 0:
        exit(1)


def lint_var_redefinition(inventory_path):
    logger.info(pformat(inventory_reclass(inventory_path)))
    return 0


def lint_var_no_usage(inventory_path):
    return 0


# --search-secrets looks for key, pass, token, secret, pin, security, crypto
def lint_secrets(entropy_warn, inventory_path):

    return 0
