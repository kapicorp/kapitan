#!/bin/bash -e
DIR=$(dirname ${BASH_SOURCE[0]})
 #(1)!

KUBECTL="kubectl -n minikube-nginx-kadet" #(2)!

# Create namespace before anything else
${KUBECTL} apply -f ${DIR}/pre-deploy/namespace.yml

for SECTION in manifests
do
  echo "## run kubectl apply for ${SECTION}"
  ${KUBECTL} apply -f ${DIR}/${SECTION}/ | column -t
done