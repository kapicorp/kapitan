"""Inventory and refs search utility helpers."""

import logging

import yaml

from kapitan.utils.compat import YamlLoader
from kapitan.utils.data import deep_get
from kapitan.utils.filesystem import list_all_paths


logger = logging.getLogger(__name__)


def searchvar(args):
    """Show all inventory files where a given reclass variable is declared."""
    output = []
    maxlength = 0
    keys = args.searchvar.split(".")
    for full_path in list_all_paths(args.inventory_path):
        if full_path.endswith((".yml", ".yaml")):
            with open(full_path) as handle:
                data = yaml.load(handle, Loader=YamlLoader)
                value = deep_get(data, keys)
                if value is not None:
                    output.append((full_path, value))
                    maxlength = max(len(full_path), maxlength)
    if args.pretty_print:
        for item in output:
            print(item[0])
            for line in yaml.dump(item[1], default_flow_style=False).splitlines():
                print("    ", line)
            print()
    else:
        for item in output:
            print("{0!s:{length}} {1!s}".format(*item, length=maxlength + 2))


def search_target_token_paths(target_secrets_path, targets):
    """
    Return dict of target names and their secret token paths in target_secrets_path.
    """
    target_files = {}
    for full_path in list_all_paths(target_secrets_path):
        secret_path = full_path[len(target_secrets_path) + 1 :]
        target_name = secret_path.split("/")[0]
        if target_name in targets and full_path.endswith((".yml", ".yaml")):
            with open(full_path) as handle:
                obj = yaml.load(handle, Loader=YamlLoader)
                try:
                    secret_type = obj["type"]
                except KeyError:
                    secret_type = "gpg"
                token_path = f"?{{{secret_type}:{secret_path}}}"
            logger.debug("search_target_token_paths: found %s", token_path)
            target_files.setdefault(target_name, []).append(token_path)
    return target_files
