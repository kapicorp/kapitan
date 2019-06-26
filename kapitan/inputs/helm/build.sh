#!/usr/bin/env bash

if ! command -v go >/dev/null 2>&1; then
    echo 'go is required to build the helm template binding'
    exit 1
fi

cd $(dirname "$0")
go build -buildmode=c-shared -o libtemplate.so template.go
python cffi_build.py