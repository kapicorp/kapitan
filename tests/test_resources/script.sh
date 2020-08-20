#!/usr/bin/env bash

# printenv
set -ex

echo "PWD $PWD"
echo "DOPE $DOPE"

echo "tried $@ "
echo "*****"
echo "***** $0 000"
echo "$1 111"
echo "$2 222"

echo "coool" > "$2/cool.yaml"
ls -al $2


echo "yooooos"

# echo "hello" > "$COMPILED_TARGET_DIR/cool.yaml"