#!/usr/bin/env bash

set -ex

compile_dir=$1

echo "This is going into a file" > "${compile_dir}/${FILE_NAME}"