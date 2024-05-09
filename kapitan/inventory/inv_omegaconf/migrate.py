import os
import sys

from regex import regex

from kapitan.inventory.inventory import InventoryError


def migrate(inventory_path: str):
    # FEAT: write migrations to temp dir and copy only if succeeded

    if os.path.exists(inventory_path):
        if os.path.isdir(inventory_path):
            migrate_dir(inventory_path)
        elif os.path.isfile(inventory_path):
            migrate_file(inventory_path)
    else:
        print(f"Error while migrating: inventory path at {inventory_path} does not exist")


def migrate_dir(path: str):
    """migrates all .yml/.yaml files in the given path to omegaconfs syntax"""

    for root, _, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            name, ext = os.path.splitext(file)

            if ext not in (".yml", ".yaml"):
                continue

            try:
                migrate_file(file)
            except Exception as e:
                InventoryError(f"{file}: error with migration: {e}")


def migrate_file(file: str):
    with open(file, "r") as fp:
        content = fp.read()

    updated_content = migrate_str(content)

    with open(file, "w") as fp:
        fp.write(updated_content)


def migrate_str(content: str):
    # FEAT: don't migrate custom resolvers
    # FEAT: migrate interpolations with '.' in the keyname

    # search for interpolation pattern
    # migrate path delimiter
    # migrate meta data name
    updated_content = regex.sub(
        r"(?<!\\)\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
        lambda match: "${" + match.group(1).replace(":", ".",).replace("_reclass_", "_kapitan_") + "}",
        content,
    )

    # replace escaped tags with specific resolver
    excluded_chars = "!"
    invalid = any(c in updated_content for c in excluded_chars)
    updated_content = regex.sub(
        r"\\\${([^\${}]*+(?:(?R)[^\${}]*)*+)}",
        lambda match: ("${escape:" if not invalid else "\\\\\\${") + match.group(1) + "}",
        updated_content,
    )

    return updated_content


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./migrate.py <inventory-path>")
    print(f"Migrating all .yml/.yaml files in {sys.argv[1]}")
    migrate(sys.argv[1])
