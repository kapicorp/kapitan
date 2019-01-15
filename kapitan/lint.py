#!/usr/bin/env python3.6
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

"lint module"

import logging
import os
from pprint import pformat
from sys import exit

from kapitan.utils import list_all_paths

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def start_lint(fail_on_warning, skip_class_checks, inventory_path, search_secrets, secrets_path, compiled_path):
    if skip_class_checks and not search_secrets:
        logger.info("Nothing to check. Remove --skip-class-checks or add --search-secrets to lint secrets")
        exit(0)

    status_class_checks = 0
    if not skip_class_checks:
        if not os.path.isdir(inventory_path):
            logger.info("\nInventory path is invalid or not provided, skipping class checks\n")
        else:
            logger.info("\nChecking for orphan classes in inventory...\n")
            status_class_checks = lint_unused_classes(inventory_path)

    status_secrets = 0
    if search_secrets:
        logger.info("\nChecking for orphan secrets files...\n")
        status_secrets = lint_orphan_secrets(compiled_path, secrets_path)

    if fail_on_warning and (status_secrets + status_class_checks) > 0:
        exit(1)


def lint_orphan_secrets(compiled_path, secrets_path):
    logger.debug("Find secret paths for " + secrets_path)
    secrets_paths = set()
    for path in list_all_paths(secrets_path):
        if os.path.isfile(path):
            path = path[len(secrets_path) + 1:]
            secrets_paths.add(path)

    logger.debug("Collected # of paths: {}".format(len(secrets_paths)))
    logger.debug("Checking if all secrets are declared in " + compiled_path)

    for path in list_all_paths(compiled_path):
        if os.path.isfile(path):
            with open(path, "r") as compiled_file:
                file_contents = compiled_file.read()
                for secret_path in list(secrets_paths):
                    if secret_path in file_contents:
                        secrets_paths.discard(secret_path)

    status = len(secrets_paths) > 0
    if status:
        logger.info("No usage found for the following {} secrets files:\n{}".format(len(secrets_paths), pformat(secrets_paths)))

    return status


def lint_unused_classes(inventory_path):
    classes_dir = os.path.join(inventory_path, "classes/")
    logger.debug("Find unused classes from {}".format(classes_dir))
    class_paths = set()
    for path in list_all_paths(classes_dir):
        if os.path.isfile(path) and (path.endswith('.yml') or path.endswith('.yaml')):
            path = path[len(classes_dir):]
            path = path.replace(".yml", "").replace(".yaml", "").replace("/", ".")
            class_paths.add(path)

    logger.debug("Collected # of paths: {}".format(len(class_paths)))
    logger.debug("Checking if all classes are declared in " + classes_dir)

    for path in list_all_paths(inventory_path):
        if os.path.isfile(path):
            with open(path, "r") as compiled_file:
                file_contents = compiled_file.read()
                for class_path in list(class_paths):
                    if class_path in file_contents:
                        class_paths.discard(class_path)

    status = len(class_paths) > 0
    if status:
        logger.info("No usage found for the following {} classes:\n{}".format(len(class_paths), pformat(class_paths)))

    return status
