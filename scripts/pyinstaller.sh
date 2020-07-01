#!/bin/bash

# this script is for building the kapitan binary inside docker image
# created by Dockerfile.pyinstaller

set -e

if [[ "$OSTYPE" == "linux-gnu" ]]; then
    os_suffix="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    os_suffix="Darwin"
fi

lc_os=$(echo $os_suffix | sed 's/./\L&/g')

entry='__main__'
output_name="kapitan-$lc_os-amd64"
pyi-makespec kapitan/"$entry".py --onefile \
    --add-data "kapitan/reclass/reclass:reclass" \
    --add-data "kapitan/lib:kapitan/lib" \
    --add-data "kapitan/inputs/templates:kapitan/inputs/templates" \
    --add-data "kapitan/inputs/helm/libtemplate_$os_suffix.so:kapitan/inputs/helm" \
    --add-data "kapitan/dependency_manager/helm/helm_fetch_$os_suffix.so:kapitan/dependency_manager/helm" \
    --hidden-import pyparsing --hidden-import jsonschema \
    --exclude-module doctest --exclude-module pydoc
pyinstaller "$entry".spec --clean
mv dist/$entry dist/$output_name
# Open permissions so that when this binary
# is used outside of docker (on the volume mount) it
# also can be deleted by Travis CI
chmod 777 dist/$output_name
