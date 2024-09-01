#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

KUBECTL="kubectl --context {{inventory.parameters.target_name}} --insecure-skip-tls-verify={{inventory.parameters.kubectl.insecure_skip_tls_verify}} "

${KUBECTL} $@