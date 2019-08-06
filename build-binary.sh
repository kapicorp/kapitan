#!/usr/bin/env bash

set -e
IMAGE_NAME='pyinstaller-debian'
KAPITAN_BIN_PATH='dist/runner' # when changing this value, also change it on BinaryTest
docker build -t $IMAGE_NAME -f pyinstaller-Dockerfile .
docker run -it -v $(pwd)/dist:/kapitan/dist $IMAGE_NAME
mv dist/__main__ $KAPITAN_BIN_PATH
