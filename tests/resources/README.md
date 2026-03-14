# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

# Test Resources Layout

This directory contains all non-Python test assets used by the test suite.

## Structure

- `integration/`
  - Full fixture projects copied to temp directories and mutated during
    integration-style tests.
  - `kapitan_compile/`: compile-focused targets used by
    `isolated_test_resources`.
  - `kapitan_helm/`: helm-heavy targets and charts used by
    `isolated_helm_project`.
- `golden/`
  - Read-only expected outputs used for compile output assertions.
  - `compile/kubernetes`, `compile/terraform`, `compile/docker`.
- `fixtures/`
  - Small focused fixture inputs shared by unit and integration tests.
  - `cue/module1`, `jsonnet/files`, `yaml/`.
  - `lint/`: lint baseline fixture project used by `isolated_lint_project`.
  - `dependency_manager/http_sources/` for mocked dependency downloads.

## Usage Rules

- Treat everything under `tests/resources/` as read-only in tests.
- Use fixtures in `tests/conftest.py` (or constants in `tests/support/paths.py`)
  instead of hardcoded filesystem strings.
- Prefer adding new files under `fixtures/` for narrow unit-test inputs and
  under `integration/` when a full inventory/project layout is required.
