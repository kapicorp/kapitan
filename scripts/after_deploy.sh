#!/usr/bin/env bash

set -e

notify_slack() {
  if [ -z "$SLACK_WEBHOOK" ]; then
    return 0
  fi

  curl -s --retry 3 --retry-delay 3 -X POST --data-urlencode 'payload={"text": "'"$1"'"}' $SLACK_WEBHOOK > /dev/null
}

export LATEST_TAG=$(git describe --abbrev=0 --tags)
notify_slack "Succesfully deployed ${LATEST_TAG} on Kapitan. https://github.com/deepmind/kapitan/releases/tag/${LATEST_TAG}"
