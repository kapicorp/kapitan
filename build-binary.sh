#!/usr/bin/env bash

set -e
IMAGE_NAME='pyinstaller-debian'
docker build -t $IMAGE_NAME -f pyinstaller-Dockerfile .
docker run -it -v $(pwd)/dist:/kapitan/dist $IMAGE_NAME
