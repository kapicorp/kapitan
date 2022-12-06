#!/bin/bash -e
DIR=$(dirname ${BASH_SOURCE[0]})
{% set i = inventory.parameters %} #(1)!

KUBECTL="kubectl -n {{i.namespace}}" #(2)!

# Create namespace before anything else
${KUBECTL} apply -f ${DIR}/pre-deploy/namespace.yml

for SECTION in manifests
do
  echo "## run kubectl apply for ${SECTION}"
  ${KUBECTL} apply -f ${DIR}/${SECTION}/ | column -t
done
