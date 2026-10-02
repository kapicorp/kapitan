#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Shared configuration for inventory backend example compile tests and golden snapshot refresh.

Both the test suite and ``scripts/refresh_inventory_backend_goldens.py`` consume this module
so that compile arguments are defined in a single place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


TEST_PWD = os.getcwd()

RECLASS_EXAMPLE = os.path.join(TEST_PWD, "examples", "reclass")
OMEGACONF_EXAMPLE = os.path.join(TEST_PWD, "examples", "omegaconf")

RECLASS_INVENTORY = os.path.join(TEST_PWD, "examples", "reclass", "inventory")
OMEGACONF_INVENTORY = os.path.join(TEST_PWD, "examples", "omegaconf", "inventory")

# Reclass and reclass-rs share the same inventory because they are drop-in
# compatible at the file-format level. They have separate golden snapshot
# directories because runtime differences (e.g. exports) may affect compiled
# output in the future even if they match today.
GOLDEN_BASE = os.path.join(TEST_PWD, "tests", "golden", "inventory_backend_examples")


@dataclass(frozen=True)
class InventoryBackendExample:
    name: str
    source_dir: str
    golden_dir: str
    compile_args: List[str]


INVENTORY_BACKEND_EXAMPLES = [
    InventoryBackendExample(
        name="reclass",
        source_dir=RECLASS_EXAMPLE,
        golden_dir=os.path.join(GOLDEN_BASE, "reclass"),
        compile_args=[
            "compile",
            "--inventory-path",
            "inventory",
            "--inventory-backend=reclass",
        ],
    ),
    InventoryBackendExample(
        name="reclass-rs",
        source_dir=RECLASS_EXAMPLE,
        golden_dir=os.path.join(GOLDEN_BASE, "reclass-rs"),
        compile_args=[
            "compile",
            "--inventory-path",
            "inventory",
            "--inventory-backend=reclass-rs",
        ],
    ),
    InventoryBackendExample(
        name="omegaconf",
        source_dir=OMEGACONF_EXAMPLE,
        golden_dir=os.path.join(GOLDEN_BASE, "omegaconf"),
        compile_args=[
            "compile",
            "--inventory-path",
            "inventory",
            "--inventory-backend=omegaconf",
        ],
    ),
]
