#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

DIR=$(dirname ${BASH_SOURCE[0]})

for SECTION in pre-deploy manifests
do
  echo "## run kubectl apply for ${SECTION}"
  kapitan refs --reveal -f ${DIR}/../${SECTION}/ | ${DIR}/kubectl.sh apply -f - | column -t
done