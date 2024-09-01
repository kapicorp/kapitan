#!/usr/bin/env bash

set -e

notify_slack() {
  if [ -z "$SLACK_WEBHOOK" ]; then
    return 0
  fi

  curl -s --retry 3 --retry-delay 3 -X POST --data-urlencode 'payload={"text": "'"$1"'"}' ${SLACK_WEBHOOK} > /dev/null
}

notify_hangouts() {
  if [ -z "$HANGOUTS_WEBHOOK" ]; then
    return 0
  fi

  curl -s --retry 3 --retry-delay 3 -H 'Content-Type: application/json' -X POST -d '{"text": "'"$1"'"}' ${HANGOUTS_WEBHOOK} > /dev/null
}

export LATEST_TAG=$(git describe --abbrev=0 --tags)
MSG="Succesfully deployed ${LATEST_TAG} on Kapitan. https://github.com/kapicorp/kapitan/releases/tag/${LATEST_TAG}"
notify_slack "${MSG}"
notify_hangouts "${MSG}"
