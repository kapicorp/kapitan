#!/usr/bin/env python3

import sys
import os
from ruamel.yaml import YAML
from pathlib import Path
import regex as re

REF_TOKEN = r"(?<!\\)\${([^\${}]*+(?:(?R)[^\${}]*)*+)}"


def replace_token(token: str) -> str:
    inner_token = token[2:-1]

    if "parameters." in inner_token:
        return token

    offset = 0
    matches = re.finditer(REF_TOKEN, inner_token)
    for match in matches:
        replaced = replace_token(match.group())
        inner_token = inner_token[: match.start() - offset] + replaced + inner_token[match.end() - offset :]
        offset += len(match.group()) - len(replaced)

    inner_token = inner_token.replace(":", ".")
    inner_token = "parameters." + inner_token

    token = "${" + inner_token + "}"

    return token


def replace_str(input: str) -> str:
    offset = 0
    matches = re.finditer(REF_TOKEN, input)
    for match in matches:
        replaced = replace_token(match.group())
        input = input[: match.start() - offset] + replaced + input[match.end() - offset :]
        offset += len(match.group()) - len(replaced)

    return input


# replace all references with OmegaConf syntax
def migrate_yaml_obj(yaml_obj: dict | list | str) -> None:
    # dictionary
    if isinstance(yaml_obj, dict):
        for k, v in yaml_obj.items():
            yaml_obj[k] = migrate_yaml_obj(v)
    # list
    elif isinstance(yaml_obj, list):
        yaml_obj = [migrate_yaml_obj(item) for item in yaml_obj]
    # string --> replace the references
    elif isinstance(yaml_obj, str):
        yaml_obj = replace_str(yaml_obj)

    return yaml_obj


def migrate_file(input_file: str) -> None:
    # load the file
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True

    file_path = Path(input_file).resolve()

    try:
        yaml_obj = yaml.load(file_path)
        yaml_obj = migrate_yaml_obj(yaml_obj)
    except:
        print("ERROR in: ", file_path)
        return
    # yaml.dump(yaml_obj, file_path)

    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.dump(yaml_obj, file_path)


def migrate(inv_path: str, output_path: str = "") -> None:
    targets_path = os.path.join(inv_path, "targets")
    classes_path = os.path.join(inv_path, "classes")

    for root, subdirs, files in os.walk(targets_path):
        for target_file in files:
            target_file = os.path.join(root, target_file)
            _, ext = os.path.splitext(target_file)

            if ext not in (".yml", ".yaml"):
                continue

            migrate_file(target_file)

    for root, subdirs, files in os.walk(classes_path):
        for class_file in files:
            class_file = os.path.join(root, class_file)

            _, ext = os.path.splitext(class_file)

            if ext not in (".yml", ".yaml"):
                continue

            migrate_file(class_file)


# support running the file without kapitan
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: migrate_omegaconf.py INV_PATH")
        sys.exit(1)

    inv_path = sys.argv[1]

    if not os.path.exists(inv_path):
        print("Path does not exist")

    migrate(inv_path)
