#!/bin/bash -eu

{% set i = inventory.parameters %}
DIR=$(dirname ${BASH_SOURCE[0]})

echo "Running for target {{ i.target_name }}"
echo ${DIR}

