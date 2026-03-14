# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from tests.support.paths import (
    EXAMPLE_DOCKER_ROOT,
    EXAMPLE_TERRAFORM_ROOT,
    KAPITAN_HELM_INTEGRATION,
)
from tests.support.projects import prepare_isolated_project


@pytest.fixture
def isolated_helm_project(tmp_path):
    """
    Create an isolated copy of the helm fixture project for test execution.
    Returns the path to the isolated copy.
    """
    return prepare_isolated_project(tmp_path, KAPITAN_HELM_INTEGRATION, "helm_project")


@pytest.fixture
def isolated_terraform_inventory(tmp_path):
    """
    Create an isolated copy of the terraform example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(
        tmp_path, EXAMPLE_TERRAFORM_ROOT, "terraform"
    )
    assert EXAMPLE_TERRAFORM_ROOT not in isolated_path.parents
    assert tmp_path in isolated_path.parents
    return isolated_path


@pytest.fixture
def isolated_docker_inventory(tmp_path):
    """
    Create an isolated copy of the docker example for test execution.
    Returns the path to the isolated copy.
    """
    isolated_path = prepare_isolated_project(tmp_path, EXAMPLE_DOCKER_ROOT, "docker")
    assert EXAMPLE_DOCKER_ROOT not in isolated_path.parents
    assert tmp_path in isolated_path.parents
    return isolated_path
