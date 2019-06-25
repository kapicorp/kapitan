#!/usr/bin/env bash
cd $(dirname "$0")
go build -buildmode=c-shared -o libtemplate.so template.go
python cffi_build.py