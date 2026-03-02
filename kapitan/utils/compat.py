"""Compatibility helpers used across the Kapitan utility modules."""

try:
    from enum import StrEnum
except ImportError:
    from strenum import StrEnum  # noqa: F401

try:
    from yaml import CSafeLoader as YamlLoader
except ImportError:
    from yaml import SafeLoader as YamlLoader  # noqa: F401
