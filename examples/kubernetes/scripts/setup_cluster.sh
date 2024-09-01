#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

{% set i = inventory.parameters %}
{% set cluster = i.cluster %}

{% if cluster.type == "gke" %}
gcloud container clusters get-credentials {{cluster.name}} --zone {{cluster.zone}} --project {{i.project}}
{% elif cluster.type == "self-hosted" %}

kubectl config set-credentials $USER --client-certificate=$HOME/credentials/$USER.crt --client-key=$HOME/credentials/$USER.key
kubectl config set-cluster {{cluster.id}} --server={{cluster.kubernetes.master.api}} --certificate-authority={{cluster.kubernetes.master.ca}} --embed-certs={{cluster.kubernetes.master.embed}}

{% elif cluster.type == "minikube" %}

{% endif %}