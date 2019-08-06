#!/bin/bash -i

# this script is for building the binary inside docker image.]

set -e
. /root/.bashrc

entry='__main__'
output_name='runner'
pyi-makespec kapitan/"$entry".py --onefile \
    --add-data kapitan/reclass/reclass:reclass \
    --add-data kapitan/lib:kapitan/lib \
    --add-data kapitan/inputs/helm/libtemplate.so:kapitan/inputs/helm \
    --hidden-import pyparsing --hidden-import jsonschema \
    --exclude-module doctest --exclude-module pydoc
pyinstaller "$entry".spec --clean
mv dist/$entry dist/$output_name
