#!/usr/bin/env bash
entry='__main__'
rm dist/$entry && echo "removed dist/$entry"
rm -rf build/$entry && echo "removed build/$entry"
rm "$entry".spec && echo "removed $entry.spec"
pyi-makespec kapitan/"$entry".py --onefile \
    --add-data kapitan/reclass/reclass:reclass \
    --add-data kapitan/lib:kapitan/lib \
    --hidden-import pyparsing --hidden-import jsonschema --hidden-import pyyaml
pyinstaller "$entry".spec
#mv dist/$entry examples/kubernetes/runner