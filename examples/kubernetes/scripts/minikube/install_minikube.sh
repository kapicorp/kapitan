#!/bin/bash -eu

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

case "$(uname -s)" in
    Linux*)     MINIKUBE_BINARY=minikube-linux-amd64;;
    Darwin*)    MINIKUBE_BINARY=minikube-darwin-amd64;;
    *)          exit 1
esac

MINIKUBE_VERSION=${MINIKUBE_VERSION:-{{inventory.parameters.minikube.version}}}
URL=https://storage.googleapis.com/minikube/releases/${MINIKUBE_VERSION}/${MINIKUBE_BINARY}


echo Downloading minikube release ${MINIKUBE_VERSION} to /usr/local/bin/minikube
pause
sudo curl --progress-bar -o /usr/local/bin/minikube ${URL}
sudo chmod +x /usr/local/bin/minikube