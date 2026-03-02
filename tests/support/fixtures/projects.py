# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from tests.support.paths import EXAMPLE_KUBERNETES_ROOT, KAPITAN_COMPILE_INTEGRATION
from tests.support.projects import copy_project_tree, prepare_isolated_project


def _attach_fixture(request, name, value):
    instance = getattr(request, "instance", None)
    if instance is not None:
        setattr(instance, name, value)


@pytest.fixture
def isolated_test_resources(tmp_path, request):
    """
    Create an isolated copy of the compile fixture project for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(
        tmp_path, KAPITAN_COMPILE_INTEGRATION, "compile_project"
    )
    _attach_fixture(request, "isolated_test_resources", isolated_path)
    return isolated_path


@pytest.fixture
def isolated_kubernetes_inventory(tmp_path):
    """
    Create an isolated copy of the kubernetes example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(
        tmp_path,
        EXAMPLE_KUBERNETES_ROOT,
        "kubernetes",
        clean_compiled=True,
    )
    assert EXAMPLE_KUBERNETES_ROOT not in isolated_path.parents
    assert tmp_path in isolated_path.parents
    return isolated_path


@pytest.fixture
def kubernetes_inventory_copy(tmp_path):
    """
    Create a writable copy of the kubernetes example without changing cwd.
    Returns the path to the isolated copy.
    """
    return copy_project_tree(tmp_path, EXAMPLE_KUBERNETES_ROOT, "kubernetes")


@pytest.fixture
def migrated_omegaconf_inventory(kubernetes_inventory_copy):
    """
    Return a migrated omegaconf inventory path under a writable copy.
    """
    from kapitan.inventory.backends.omegaconf import migrate
    from kapitan.inventory.backends.omegaconf.resolvers import register_resolvers

    inventory_path = Path(kubernetes_inventory_copy) / "inventory"
    migrate(str(inventory_path))
    register_resolvers()
    return inventory_path
