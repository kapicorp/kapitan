import sys
import os
from ruamel.yaml import YAML
from pathlib import Path
import regex

REF_TOKEN = r".*\$\{.*\}.*"


def replace_token(token: str) -> str:
    token = token.replace(":", ".")

    return token.replace


def replace_str(input: str) -> str:
    if regex.match(REF_TOKEN, input):
        return replace_token(input)

    return input


def migrate_file(input_file: str) -> None:
    # load the file
    yaml = YAML()
    file_path = Path(input_file)
    yaml.load(file_path)

    # replace all references with modern


def migrate(inv_path: str = "") -> None:
    if len(sys.argv) != 2:
        print("Usage: migrate_omegaconf.py INV_PATH")
        return 0

    inv_path = sys.argv[1]

    if not os.path.exists(inv_path):
        print("Path does not exist")

    targets_path = os.path.join(inv_path, "targets")
    classes_path = os.path.join(inv_path, "classes")

    for root, subdirs, files in os.walk(targets_path):
        for target_file in files:
            migrate_file(target_file)

    for root, subdirs, files in os.walk(classes_path):
        for class_file in files:
            migrate_file(class_file)


# support running the file without kapitan
if __name__ == "__main__":
    migrate()
