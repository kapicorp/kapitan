#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

{% set i = inventory.parameters %}
{% set cluster = i.cluster %}
kubectl config set-context {{i.target_name}} --cluster {{cluster.id}} --user {{cluster.user}} --namespace {{i.namespace}}
kubectl config use-context {{i.target_name}}