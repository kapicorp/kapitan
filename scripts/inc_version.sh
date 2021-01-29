#!/usr/bin/env bash

set -e

echomsg() {
  echo "--- ${1} ---"
}

export LAST_COMMIT_MSG="$(git log -1 --oneline)"

if ! $(echo "$LAST_COMMIT_MSG" | grep -qE "kapicorp/release-v([0-9]+.[0-9]{2}.[0-9]+)+" ); then
  echomsg "Not a release, skipping version incrementing"
  exit 0;
fi

echomsg "Incrementing Version"

# Get everything after kapicorp/release-v
export VERSION="${LAST_COMMIT_MSG##*kapicorp/release-v}"
# Get everything before space character
export VERSION="${VERSION%% *}"
export TRAVIS_TAG="v$VERSION"

echomsg "Computed version from commit: $VERSION"

sed -i.bak "s/VERSION =.*/VERSION = '$VERSION'/g" ./kapitan/version.py

echomsg "Setup git"

git config --local user.email "kapitan-admins@googlegroups.com"
git config --local user.name "Kapitan CI"

echomsg "Increment version in kapitan/version.py"

git add ./kapitan/version.py
git commit -m "Version increment $VERSION"
git tag -a "v$VERSION" -m "Version increment $VERSION"

git remote remove origin
git remote add origin https://${GH_TOKEN}@github.com/kapicorp/kapitan.git

echomsg "Push new commit and tag v$VERSION"
git push origin --tags HEAD:master
