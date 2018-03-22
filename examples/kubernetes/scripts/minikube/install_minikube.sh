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
