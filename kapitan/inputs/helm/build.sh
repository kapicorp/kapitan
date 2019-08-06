#!/usr/bin/env bash

if ! command -v go >/dev/null 2>&1; then
    echo 'go is required to build the helm template binding'
    exit 1
fi

cd $(dirname "$0")
pwd
so_name=libtemplate.so

go build -buildmode=c-shared -o $so_name template.go
if [ -e $so_name ]
then
    echo "$so_name built successfully. Creating the Python binding"
else
    echo "$so_name is missing. Exiting"
    exit 1
fi
python cffi_build.py