#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Generate large synthetic inventories for performance benchmarking.

The generated inventory reproduces the workload shape that hides backend
rendering regressions: many targets that all share one deep class stack.
Every target includes a single root class which chains ``classes`` levels
deep, so the same shared class tree is parsed and merged for each target.
This is the exact shape that made the OmegaConf rendering cost visible.

Backend-neutral: only plain ``classes``/``parameters`` YAML is emitted, so the
same tree renders identically on reclass, reclass-rs and omegaconf.
"""

import os


def make_large_inventory(
    base_path: str,
    *,
    targets: int = 40,
    classes: int = 12,
    keys: int = 15,
) -> str:
    """Write a synthetic inventory under ``base_path`` and return its path.

    The layout is ``<base_path>/classes`` + ``<base_path>/targets``, so
    ``base_path`` can be used directly as ``--inventory-path``.

    Args:
        base_path: directory to create the ``classes``/``targets`` tree in.
        targets: number of targets, all sharing the same class stack.
        classes: depth of the shared class chain (root -> ... -> leaf).
        keys: number of parameter keys defined by each class in the stack.

    Returns:
        ``base_path`` (now populated with the inventory tree).
    """
    if targets < 1 or classes < 1 or keys < 1:
        raise ValueError("targets, classes and keys must all be >= 1")

    classes_dir = os.path.join(base_path, "classes", "stack")
    targets_dir = os.path.join(base_path, "targets")
    os.makedirs(classes_dir)
    os.makedirs(targets_dir)

    # Deep shared class chain: c0 -> c1 -> ... -> c{classes-1}.
    # Each level adds its own unique keys so merging does real work instead of
    # repeatedly overwriting the same key.
    for level in range(classes):
        lines = []
        if level + 1 < classes:
            lines.append("classes:")
            lines.append(f"  - stack.c{level + 1}")
        lines.append("parameters:")
        for k in range(keys):
            lines.append(f"  c{level}_k{k}: v{level}_{k}")
        with open(os.path.join(classes_dir, f"c{level}.yml"), "w") as f:
            f.write("\n".join(lines) + "\n")

    # Every target pulls the whole stack via the single root class, plus one
    # target-specific key so targets are not byte-identical.
    for t in range(targets):
        with open(os.path.join(targets_dir, f"t{t}.yml"), "w") as f:
            f.write(f"classes:\n  - stack.c0\nparameters:\n  target_id: t{t}\n")

    return base_path
