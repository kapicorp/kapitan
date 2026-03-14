"""CLI-facing utility helpers."""

import logging
import os
import sys

import yaml

from kapitan import cached
from kapitan.version import VERSION


logger = logging.getLogger(__name__)


def fatal_error(message):
    "Logs error message, sys.exit(1)"
    logger.error(message)
    sys.exit(1)


class termcolor:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def dot_kapitan_config():
    """Returns the parsed YAML .kapitan file. Subsequent requests will be cached."""
    if not cached.dot_kapitan:
        if os.path.exists(".kapitan"):
            with open(".kapitan") as handle:
                cached.dot_kapitan = yaml.safe_load(handle)

    return cached.dot_kapitan


def from_dot_kapitan(command, flag, default):
    """
    Returns the 'flag' from the '<command>' or from the 'global' section in the .kapitan file.
    If neither section provides a value for the flag, the value passed in `default` is returned.
    """
    kapitan_config = dot_kapitan_config()
    global_config = kapitan_config.get("global", {})
    cmd_config = kapitan_config.get(command, {})
    return cmd_config.get(flag, global_config.get(flag, default))


def compare_versions(v1_raw, v2_raw):
    """
    Parses v1_raw and v2_raw into versions and compares them.
    Returns 'equal' if v1 == v2, 'greater' if v1 > v2, and 'lower' if v1 < v2.
    """
    v1 = v1_raw.replace("-rc", "")
    v2 = v2_raw.replace("-rc", "")
    v1_split = v1.split(".")
    v2_split = v2.split(".")
    min_range = min(len(v1_split), len(v2_split))

    for i in range(min_range):
        if v1_split[i] == v2_split[i]:
            continue
        if v1_split[i] > v2_split[i]:
            return "greater"
        if v1_split[i] < v2_split[i]:
            return "lower"

    if min_range > 2:
        v1_is_rc = "-rc" in v1_raw
        v2_is_rc = "-rc" in v2_raw

        if not v1_is_rc and v2_is_rc:
            return "greater"
        if v1_is_rc and not v2_is_rc:
            return "lower"

    return "equal"


def check_version():
    """
    Checks the version in .kapitan is the same as the current version.
    If the version in .kapitan is greater, it will prompt to upgrade.
    If the version in .kapitan is lower, it will prompt to update .kapitan or downgrade.
    """
    kapitan_config = dot_kapitan_config()
    try:
        if kapitan_config and kapitan_config["version"]:
            dot_kapitan_version = str(kapitan_config["version"])
            result = compare_versions(dot_kapitan_version, VERSION)
            if result == "equal":
                return
            print(f"{termcolor.WARNING}Current version: {VERSION}")
            print(f"Version in .kapitan: {dot_kapitan_version}{termcolor.ENDC}\n")

            if result == "greater":
                print(
                    f"Upgrade kapitan to '{dot_kapitan_version}' in order to keep results consistent:\n"
                )
            elif result == "lower":
                print(
                    f"Option 1: You can update the version in .kapitan to '{VERSION}' and recompile\n"
                )
                print(
                    f"Option 2: Downgrade kapitan to '{dot_kapitan_version}' in order to keep results consistent:\n"
                )

            print(f"Docker: docker pull kapicorp/kapitan:{dot_kapitan_version}")
            print(
                f"Pip (user): pip3 install --user --upgrade kapitan=={dot_kapitan_version}\n"
            )
            print(
                "Check https://github.com/kapicorp/kapitan#quickstart for more info.\n"
            )
            print(
                "If you know what you're doing, you can skip this check by adding '--ignore-version-check'."
            )
            sys.exit(1)
    except KeyError:
        pass
