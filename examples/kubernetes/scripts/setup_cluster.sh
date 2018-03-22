#!/bin/bash -eu
#
# Copyright 2018 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

{% set i = inventory.parameters %}
{% set cluster = i.cluster %}

{% if cluster.type == "gke" %}
gcloud container clusters get-credentials {{cluster.name}} --zone {{cluster.zone}} --project {{i.project}}
{% elif cluster.type == "self-hosted" %}

kubectl config set-credentials $USER --client-certificate=$HOME/volta_credentials/$USER.crt --client-key=$HOME/volta_credentials/$USER.key
kubectl config set-cluster {{cluster.id}} --server={{cluster.kubernetes.master.api}} --certificate-authority={{cluster.kubernetes.master.ca}} --embed-certs={{cluster.kubernetes.master.embed}}

{% elif cluster.type == "minikube" %}

{% endif %}
