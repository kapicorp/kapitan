#!/usr/bin/env python3

import argparse
import os
import re
import sys
from io import StringIO


def update_secrets(file_path):
    temp_buf = StringIO()
    updated = False

    with open(file_path) as fp:
        for line in fp:
            if line == "type: ref\n":
                temp_buf.write("type: base64\n")
                if not updated:  # only set updated once
                    updated = True
            else:
                temp_buf.write(line)
    if updated:
        print(">>> updating:", file_path)
        with open(file_path, "w") as fp:
            fp.write(temp_buf.getvalue())


def update_inventory(file_path):
    temp_buf = StringIO()
    REF_TOKEN_TAG_PATTERN = re.compile(r"(\?{([\w\:\.\-\/@]+)([\|\w\:\.\-\/]+)?=*})")
    TOKEN_TAG_PATTERN = re.compile(r"(\?{([^|]+)([\|].*)?=*})")

    updated = False

    def ref_to_base64(match_obj):
        tag, token, _ = match_obj.groups()
        if token.startswith("ref:"):
            return "?{base64" + token[3:] + "}"
        else:
            return tag

    def single_to_double(match_obj):
        tag, token, funcs = match_obj.groups()
        if not (funcs is None):
            return tag.replace("|", "||", 1)
        else:
            return tag

    with open(file_path) as fp:
        for line in fp:
            _line = REF_TOKEN_TAG_PATTERN.sub(ref_to_base64, line)
            _line = TOKEN_TAG_PATTERN.sub(single_to_double, _line)
            temp_buf.write(_line)
            if not updated and (line != _line):  # only set updated once
                updated = True
    if updated:
        print(">>> updating:", file_path)
        with open(file_path, "w") as fp:
            fp.write(temp_buf.getvalue())


def find_files(path):
    if not (os.path.isdir(path) and os.path.exists(path)):
        raise Exception("path is not a directory or doesn't exist")
    for root, _, files in os.walk(path):
        for f in files:
            if not f.startswith("."):
                yield os.path.join(root, f)


def pre_warning():
    print(
        """
    KAP-5 MIGRATION SCRIPT

    WARNING: This will update your 'ref' type secret objects and your inventory secret declaration!

    KAP-5 discontinues 'ref' type secrets and introduces 'base64' type instead.
    Along with that we also changed the first | in secret references to || to
    better signify it's closer to a logical OR.

    If you have any ref type secrets like in this form: ?{ref:path/to/thing}
    you will want to run this script when upgrading to Kapitan v0.25
    Kapitan v0.25 requires your ref type secrets to be 'base64' instead ?{base64:path/to/thing}

    This script will update any 'ref' types found in --secrets-path and --inventory-path
    and will overwrite them with the new 'base64' type.
    It will also update all secrets in the inventory from ?{type:path/to/thing|function1|function2} to
    ?{type:path/to/thing||function1|function2}.
    """
    )

    response = input('Do you want to proceed? ("yes" to continue): ')
    if response != "yes":
        print("aborting...")
        sys.exit(1)


def post_warning():
    print(
        """
    Now that your ref types are updated into base64 types, you will need to:

    1. ensure you have installed Kapitan v0.25.
    2. review your templates and update any 'ref' types into 'base64' types.
    3. if you're using the default secrets directory, rename it from './secrets' into './refs'.
    4. note that the command '$ kapitan secrets' is now '$ kapitan refs'.
    5. note that the flag in '$ kapitan compile --secrets-path' is now '$ kapitan compile --refs-path'.
    6. run '$ kapitan compile' again and review any changes. Only 'ref' to 'base64' changes are expected.
    """
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Kapitan KAP-5 migration", description="Updates ref secret types into base64 ref types"
    )

    parser.add_argument("--secrets-path", type=str, default="./secrets", help="set secrets path")
    parser.add_argument("--inventory-path", type=str, default="./inventory", help="set inventory path")

    args = parser.parse_args()

    pre_warning()

    print("searching for refs in secrets-path:", args.refs_path)

    for file_path in find_files(args.refs_path):
        update_secrets(file_path)

    print()
    print("searching for refs in inventory-path:", args.inventory_path)

    for file_path in find_files(args.inventory_path):
        update_inventory(file_path)

    post_warning()
