#!/usr/bin/env bash

set -e

echomsg() {
  echo "--- ${1} ---"
}

export LAST_COMMIT_MSG="$(git log -1 --oneline)"

if ! $(echo "$LAST_COMMIT_MSG" | grep -q "deepmind/release-v" ); then
  echomsg "Not a release, skipping version incrementing"
  exit 0;
fi

echomsg "Incrementing Version"

# Get everything after deepmind/release-v
export VERSION="${LAST_COMMIT_MSG##*deepmind/release-v}"
# Get everything before space character
export VERSION="${VERSION%% *}"
export TRAVIS_TAG="v$VERSION"

echomsg "Computed version from commit: $VERSION"

sed -i.bak "s/VERSION =.*/VERSION = '$VERSION'/g" ./kapitan/version.py

echomsg "Setup git"

git config --local user.email "kapitan@google.com"
git config --local user.name "Kapitan CI"
git remote remove origin
git remote set-head origin -d
git remote add origin https://${GH_TOKEN}@github.com/deepmind/kapitan.git
#git fetch
#git checkout --track origin/master

echomsg "Increment version in kapitan/version.py"

git add ./kapitan/version.py
git commit -m "Version increment $VERSION"
git tag -a "v$VERSION" -m "Version increment $VERSION"

echomsg "Push new commit"
git push origin master

echomsg "Push new tag v$VERSION"
git push origin "v$VERSION"
