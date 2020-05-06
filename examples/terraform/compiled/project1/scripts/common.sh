#!/bin/bash

set -e           # If a command fails, the whole script exit
set -u           # Treat unset variables as an error, and immediately exit.
set -o pipefail  # this will make your script exit if any command in a pipeline errors

DIR=$(realpath $(dirname ${BASH_SOURCE[0]}))

check_tf_initialized() {
    if [[ ! -d "$TF_DATA_DIR" ]]; then
        echo "Terraform has not been initialized. Running $(bold init.sh) first..."
        "${DIR}"/init.sh
        echo
    fi
}

########################################################################################
# Check required binaries are installed

check_installed() {
  CMD=$1
  if ! command -v "$CMD" > /dev/null; then
      echo "$CMD not installed. Exiting..."
  fi
}

check_installed realpath
check_installed terraform

########################################################################################
# Variables
export DIR=$(realpath $(dirname ${BASH_SOURCE[0]}))                      # Folder where this script is
export TF_DIR=$(realpath ${DIR}/../terraform)                            # Folder where TF files are
export TF_DATA_DIR=$(realpath -m ${DIR}/../../../.TF_DATA_DIR/project1) # Folder for TF initialization (preferable outside of compiled)
export OUTPUT_DIR=$(realpath -m ${DIR}/../../../output/project1) # Folder for storing output files (preferable outside of compiled)
export TERRAFORM="terraform"
DEBUG=${DEBUG:-0}

########################################################################################
# MAIN

if [ $DEBUG -ne 0 ]; then
    debug
fi

pushd $TF_DIR &> /dev/null
