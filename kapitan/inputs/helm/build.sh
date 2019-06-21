#!/usr/bin/env bash
go build -buildmode=c-shared -o libtemplate.so template.go
python cffi_build.py