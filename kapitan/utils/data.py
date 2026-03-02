"""Dictionary and collection utility helpers."""

import collections


def prune_empty(data):
    """
    Remove empty lists and empty dictionaries from data
    (similar to jsonnet std.prune but faster).
    """
    if not isinstance(data, dict | list):
        return data

    if isinstance(data, list):
        if len(data) > 0:
            return [
                value
                for value in (prune_empty(value) for value in data)
                if value is not None
            ]

    if isinstance(data, dict):
        if len(data) > 0:
            return {
                key: value
                for key, value in (
                    (key, prune_empty(value)) for key, value in data.items()
                )
                if value is not None
            }


def flatten_dict(data, parent_key="", sep="."):
    """Flatten nested elements in a dictionary."""
    items = []
    for key, value in data.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, collections.abc.MutableMapping):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def deep_get(dictionary, keys, previousKey=None):
    """Search recursively for `keys` in `dictionary` and return the value, or None."""
    value = None
    if len(keys) > 0:
        value = dictionary.get(keys[0], None) if isinstance(dictionary, dict) else None

        if value:
            if len(keys) == 1:
                return value

            if not isinstance(value, dict):
                return None

            return deep_get(value, keys[1:], previousKey=keys[0])

        if isinstance(dictionary, dict):
            if "*" in keys[0]:
                key_lower = keys[0].replace("*", "").lower()
                for dict_key in dictionary:
                    if key_lower in dict_key.lower():
                        if len(keys) == 1:
                            return dictionary[dict_key]
                        return deep_get(
                            dictionary[dict_key], keys[1:], previousKey=keys[0]
                        )

            if not previousKey:
                for nested_value in dictionary.values():
                    if isinstance(nested_value, dict):
                        if len(keys) > 1:
                            item = deep_get(nested_value, keys, previousKey=keys[0])
                        else:
                            item = deep_get(nested_value, keys)

                        if item is not None:
                            return item

    return value
