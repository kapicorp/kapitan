#!/usr/bin/env bash
go build -buildmode=c-shared -o template.so template.go
gcc -Wall -o caller caller.c ./template.so # Wall means warn all
# it is better to produce -buildmode-c-archive: gives out error for now, just skip