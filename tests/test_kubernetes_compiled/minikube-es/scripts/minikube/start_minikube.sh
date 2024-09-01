#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

eval $(minikube docker-env)
minikube start --insecure-registry https://quay.io --memory=4096 --cpus=4
minikube ssh "sudo ip link set docker0 promisc on"