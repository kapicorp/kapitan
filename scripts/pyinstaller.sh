#!/bin/bash

# this script is for building the kapitan binary inside docker image
# created by Dockerfile.pyinstaller

set -e

entry='__main__'
output_name='kapitan-linux-amd64'
pyi-makespec kapitan/"$entry".py --onefile \
    --add-data kapitan/reclass/reclass:reclass \
    --add-data kapitan/lib:kapitan/lib \
    --add-data kapitan/inputs/templates:kapitan/inputs/templates \
    --add-data kapitan/inputs/helm/libtemplate.so:kapitan/inputs/helm \
    --add-data kapitan/dependency_manager/helm/helm_fetch.so:kapitan/dependency_manager/helm \
    --hidden-import pyparsing --hidden-import jsonschema \
    --hidden-import 'pkg_resources.py2_warn' \
    --exclude-module doctest --exclude-module pydoc \
    --additional-hooks-dir .
pyinstaller "$entry".spec --clean
mv dist/$entry dist/$output_name
# Open permissions so that when this binary
# is used outside of docker (on the volume mount) it
# also can be deleted by Travis CI
chmod 777 dist/$output_name
