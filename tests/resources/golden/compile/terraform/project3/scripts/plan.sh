#!/bin/bash

set -e           # If a command fails, the whole script exit
set -u           # Treat unset variables as an error, and immediately exit.
set -o pipefail  # this will make your script exit if any command in a pipeline errors

DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
source "${DIR}"/common.sh

########################################################################################
# MAIN

check_tf_initialized
"${TERRAFORM}" plan -lock=false "$@"
