#!/usr/bin/env bash

# make sure to run this from project root
set -e
IMAGE_NAME='pyinstaller-debian'
docker build -t $IMAGE_NAME -f Dockerfile.pyinstaller .
docker run -it -v $(pwd)/bindist:/kapitan/dist $IMAGE_NAME
