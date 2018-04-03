#!/usr/bin/env sh

set -e

tempDir="/tmp/kapitan/"

mkdir -p $tempDir

# Copy files from /src to /tmp/kapitan
rsync -arz --exclude '.git' . $tempDir
cd $tempDir

# Pass arguments to kapitan and execute command
python -m kapitan "$@"

# Copy files from /tmp/kapitan back to /src
rsync -arz --force . /src/
