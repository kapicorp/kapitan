"""CLI command modules."""

from .compile import compile_command
from .init import init_command
from .inventory import inventory_command
from .targets import targets_command

__all__ = [
    "targets_command",
    "compile_command",
    "inventory_command",
    "init_command"
]
