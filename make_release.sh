#!/usr/bin/env bash

set -e

if [[ "$#" -ne 1 ]]; then
  echo "Please pass version to release (e.g. ./make_release.sh 0.16.5)"
  exit 1
fi

VERSION=$1

sed -i.bak "s/VERSION =.*/VERSION = '$VERSION'/g" ./kapitan/version.py
echo "Updated version on ./kapitan/version.py to $VERSION"

echo "Making commit and tag for new release..."

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "master" ]]; then
  echo "Not on master branch, aborting."
  exit 1
fi

echo "Pulling first..."
git pull

echo "Committing..."
git add ./kapitan/version.py
git commit -m "Version incremenet $VERSION"

echo "Tagging..."
git tag "v$VERSION" master

echo "Pushing..."
git push origin master && git push origin "v$VERSION"

echo "Making release to PyPi..."
# Install deps
pip3 install --user --upgrade setuptools wheel twine
# Package kapitan
rm -r dist/ build/
python3 setup.py sdist bdist_wheel
# Upload kapitan to PyPi
twine upload --repository-url https://pypi.org/ dist/*

echo "Done"
echo
echo "Don't forget to update CHANGELOG.md and the tag release message"
