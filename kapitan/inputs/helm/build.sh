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
    echo "$so_name built successfully"
else
    echo "error building $so_name. Exiting"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo 'python3 is not available on this system. Skipping cffi build'
    exit 0
else
    echo 'Building the Python binding using cffi'
    python3 cffi_build.py
fi
