#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan@google.com>
#
# SPDX-License-Identifier: Apache-2.0

"lint module"

import logging
import os
import sys
from pprint import pformat

from kapitan.errors import KapitanError
from kapitan.utils import list_all_paths
from yamllint import linter
from yamllint.config import YamlLintConfig

logger = logging.getLogger(__name__)

yamllint_config = """
# https://yamllint.readthedocs.io/en/stable/rules.html
rules:
  braces: disable
  brackets: disable
  colons: disable
  commas: disable
  comments: disable
  comments-indentation: disable
  document-end: disable
  document-start: disable
  empty-lines: disable
  empty-values: disable
  hyphens: disable
  indentation: disable
  key-duplicates: enable
  key-ordering: disable
  line-length: disable
  new-line-at-end-of-file: disable
  new-lines: disable
  octal-values: enable
  quoted-strings: disable
  trailing-spaces: disable
  truthy: disable
"""


def start_lint(args):
    """ Runs all lint operations available
    Args:
        fail_on_warning (bool): if set to True, function will exit if any warning is found
        skip_class_checks (bool): whether to skip checking for class related warnings or not
        skip_yamllint (bool): whether to skip checking yaml files for lint problems
        inventory_path (string): path to your inventory/ folder
        search_secrets (bool): whether to search for secret related warnings or not
        secrets_path (string): path to your refs/ folder
        compiled_path (string): path to your compiled/ folder
    Yields:
        checks_sum (int): the number of lint warnings found
    """
    if args.skip_class_checks and args.skip_yamllint and not args.search_secrets:
        logger.info("Nothing to check. Remove --skip-class-checks or add --search-secrets to lint secrets")
        sys.exit(1)

    status_yamllint = 0
    status_secrets = 0
    status_class_checks = 0

    if not os.path.isdir(args.inventory_path):
        logger.info(
            "\nInventory path is invalid or not provided, skipping yamllint and orphan class checks\n"
        )
    else:
        if not args.skip_yamllint:
            logger.info("\nRunning yamllint on all inventory files...\n")
            status_yamllint = lint_yamllint(args.inventory_path)

        if not args.skip_class_checks:
            logger.info("\nChecking for orphan classes in inventory...\n")
            status_class_checks = lint_unused_classes(args.inventory_path)

    if args.search_secrets:
        logger.info("\nChecking for orphan secrets files...\n")
        status_secrets = lint_orphan_secrets(args.compiled_path, args.refs_path)

    checks_sum = status_secrets + status_class_checks + status_yamllint
    if args.fail_on_warning and checks_sum > 0:
        sys.exit(1)

    return checks_sum


def lint_orphan_secrets(compiled_path, secrets_path):
    """ Checks your refs/ folder for unused secrets files by:
        - iterating the secrets_path/ dir and extracting all secrets names from the file paths
        - does a text search over the entire compiled_path/ to find usages of those secrets
    Args:
        compiled_path (string): path to your compiled/ folder
        secrets_path (string): path to your refs/ folder
    Yields:
        checks_sum (int): the number of orphan secrets found
    """
    logger.debug("Find secret paths for " + secrets_path)
    secrets_paths = set()
    for path in list_all_paths(secrets_path):
        if os.path.isfile(path):
            path = path[len(secrets_path) + 1 :]
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

    checks_sum = len(secrets_paths)
    if checks_sum > 0:
        logger.info(
            "No usage found for the following {} secrets files:\n{}\n".format(
                len(secrets_paths), pformat(secrets_paths)
            )
        )

    return checks_sum


def lint_unused_classes(inventory_path):
    """ Checks your inventory for unused classes by:
        - iterating the inventory_path/classes/ dir and extracting all class names from the file paths
        - converting those file paths to class references (e.g. component/mysql -> component.mysql)
        - does a text search over the entire inventory_path/ to find usages of those classes
    Args:
        inventory_path (string): path to your inventory folder
    Yields:
        checks_sum (int): the number of unused classes found
    """
    classes_dir = os.path.join(inventory_path, "classes/")
    if not os.path.isdir(classes_dir):
        raise KapitanError("{} is not a valid directory or does not exist".format(classes_dir))

    logger.debug("Find unused classes from {}".format(classes_dir))
    class_paths = set()
    for path in list_all_paths(classes_dir):
        if os.path.isfile(path) and (path.endswith(".yml") or path.endswith(".yaml")):
            path = path[len(classes_dir) :]
            path = path.replace(".yml", "").replace(".yaml", "").replace("/", ".")
            class_paths.add(path)

    logger.debug("Collected # of paths: {}".format(len(class_paths)))
    logger.debug("Checking if all classes are declared in " + classes_dir)

    for path in list_all_paths(inventory_path):
        if os.path.isfile(path):
            with open(path, "r") as compiled_file:
                file_contents = compiled_file.read()
                for class_path in list(class_paths):
                    exists = class_path in file_contents
                    """
                    Classes files may reside in subdirectories, which act as namespaces.
                    For instance, a class ssh.server will result in the class definition to be read from ssh/server.yml.
                    Specifying just ssh will cause the class data to be read from ssh/init.yml or ssh.yml.
                    Note, however, that only one of those two may be present.
                    Thus we also check for ".init" being used in the class here to cover that case.
                    https://reclass.pantsfullofunix.net/operations.html
                    """
                    if class_path.endswith(".init"):
                        exists = (class_path[:-5] in file_contents) or (exists)

                    if exists:
                        class_paths.discard(class_path)

    checks_sum = len(class_paths)
    if checks_sum > 0:
        logger.info(
            "No usage found for the following {} classes:\n{}\n".format(
                len(class_paths), pformat(class_paths)
            )
        )

    return checks_sum


def lint_yamllint(inventory_path):
    """ Run yamllint on all yaml files in inventory
    Args:
        inventory_path (string): path to your inventory/ folder
    Yields:
        checks_sum (int): the number of yaml lint issues found
    """
    logger.debug("Running yamllint for " + inventory_path)

    if os.path.isfile(".yamllint"):
        logger.info("Loading values from .yamllint found.")
        conf = YamlLintConfig(file=".yamllint")
    else:
        logger.info(".yamllint not found. Using default values")
        conf = YamlLintConfig(yamllint_config)

    checks_sum = 0
    for path in list_all_paths(inventory_path):
        if os.path.isfile(path) and (path.endswith(".yml") or path.endswith(".yaml")):
            with open(path, "r") as yaml_file:
                file_contents = yaml_file.read()

                try:
                    problems = list(linter.run(file_contents, conf, filepath=path))
                except EnvironmentError as e:
                    logger.error(e)
                    sys.exit(-1)

                if len(problems) > 0:
                    checks_sum += len(problems)
                    logger.info("File {} has the following issues:".format(path))
                    for problem in problems:
                        logger.info("\t{}".format(problem))

    if checks_sum > 0:
        logger.info("\nTotal yamllint issues found: {}".format(checks_sum))

    return checks_sum
