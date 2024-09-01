#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

kubectl config set-context minikube-es --cluster minikube --user minikube --namespace minikube-es
kubectl config use-context minikube-es