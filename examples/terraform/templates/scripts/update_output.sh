#!/usr/bin/env bash


set -e           # If a command fails, the whole script exit
set -u           # Treat unset variables as an error, and immediately exit.
set -o pipefail  # this will make your script exit if any command in a pipeline errors

DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
source "${DIR}"/common.sh

########################################################################################
# MAIN

mkdir -p "$OUTPUT_DIR"
"${TERRAFORM}" output README > "${OUTPUT_DIR}"/README.md
