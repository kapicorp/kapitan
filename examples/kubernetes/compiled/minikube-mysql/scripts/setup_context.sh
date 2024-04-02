#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

kubectl config set-context minikube-mysql --cluster minikube --user minikube --namespace minikube-mysql
kubectl config use-context minikube-mysql