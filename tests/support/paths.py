# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

EXAMPLES_ROOT = REPO_ROOT / "examples"
EXAMPLE_KUBERNETES_ROOT = EXAMPLES_ROOT / "kubernetes"
EXAMPLE_TERRAFORM_ROOT = EXAMPLES_ROOT / "terraform"
EXAMPLE_DOCKER_ROOT = EXAMPLES_ROOT / "docker"

RESOURCES_ROOT = TESTS_ROOT / "resources"
INTEGRATION_ROOT = RESOURCES_ROOT / "integration"
FIXTURES_ROOT = RESOURCES_ROOT / "fixtures"
GOLDEN_ROOT = RESOURCES_ROOT / "golden"

KAPITAN_COMPILE_INTEGRATION = INTEGRATION_ROOT / "kapitan_compile"
KAPITAN_HELM_INTEGRATION = INTEGRATION_ROOT / "kapitan_helm"
KAPITAN_LINT_FIXTURE = FIXTURES_ROOT / "lint"

HTTP_SOURCES_ROOT = FIXTURES_ROOT / "dependency_manager" / "http_sources"

COMPILE_GOLDEN_ROOT = GOLDEN_ROOT / "compile"
KUBERNETES_COMPILE_GOLDEN = COMPILE_GOLDEN_ROOT / "kubernetes"
TERRAFORM_COMPILE_GOLDEN = COMPILE_GOLDEN_ROOT / "terraform"
DOCKER_COMPILE_GOLDEN = COMPILE_GOLDEN_ROOT / "docker"

CUE_FIXTURE_MODULE1 = FIXTURES_ROOT / "cue" / "module1"
JSONNET_FILES_FIXTURE = FIXTURES_ROOT / "jsonnet" / "files"
YAML_FIXTURES_ROOT = FIXTURES_ROOT / "yaml"
