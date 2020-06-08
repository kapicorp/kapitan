#!/usr/bin/env bash

set -euo pipefail

cd $(dirname "$0")
pwd

so_name="helm_fetch.so"

# Compile the binding if a Go runtime exists
if [[ -z $(which go) ]]; then
    echo "[WARN] go is not available on this system -- skipping Helm binding build!"
else
    go build -buildmode=c-shared -o $so_name helm_fetch.go
fi

# Validate that the compiled binding exists
if [[ -e $so_name ]]; then
    echo "[INFO] $so_name built successfully or already exists"
else
    echo "[ERROR] $so_name does not exist!"
    exit 1
fi

# Compile the Python ffi binding if Python is available
if [[ -z $(which python3) ]]; then
    echo "[WARN] python3 is not available on this system -- skipping cffi build!"
else
    echo "[INFO] Building the Python binding using cffi"
    python3 cffi_build.py
fi

exit 0
