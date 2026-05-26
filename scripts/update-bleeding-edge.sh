#!/usr/bin/env bash
set -euo pipefail

REPO="kapicorp/kapitan"
UPSTREAM_REMOTE="origin"

# Ensure we're in a git repo
cd "$(git rev-parse --show-toplevel)"

echo "==> Fetching upstream master..."
git fetch "$UPSTREAM_REMOTE"
git checkout -B bleeding-edge "$UPSTREAM_REMOTE/master"

echo ""
echo "==> Fetching open PRs from $REPO..."
prs_json=$(gh pr list --repo "$REPO" --state open --json number,title,isDraft,headRefName)

# Filter out drafts
non_draft_prs=$(echo "$prs_json" | jq -r '.[] | select(.isDraft == false) | .number')

merged=0
skipped=0

for number in $non_draft_prs; do
    title=$(echo "$prs_json" | jq -r ".[] | select(.number == $number) | .title")

    echo ""
    echo "PR #$number: $title"

    # Get head SHA
    sha=$(gh api "repos/$REPO/pulls/$number" --jq '.head.sha' 2>/dev/null || true)
    if [ -z "$sha" ]; then
        echo "  SKIPPED: could not get PR details"
        skipped=$((skipped + 1))
        continue
    fi

    # Check GitHub Actions / check-suites
    failing_checks=false
    check_conclusions=$(gh api "repos/$REPO/commits/$sha/check-suites" --jq '.check_suites[].conclusion // empty' 2>/dev/null || true)
    if [ -n "$check_conclusions" ]; then
        if echo "$check_conclusions" | grep -qiE "failure|error|timed_out|action_required"; then
            echo "  SKIPPED: failing checks detected"
            skipped=$((skipped + 1))
            failing_checks=true
        fi
    fi
    if [ "$failing_checks" = true ]; then
        continue
    fi

    # Check legacy commit statuses
    failing_statuses=false
    status_states=$(gh api "repos/$REPO/commits/$sha/status" --jq '.statuses[].state // empty' 2>/dev/null || true)
    if [ -n "$status_states" ]; then
        if echo "$status_states" | grep -qiE "failure|error"; then
            echo "  SKIPPED: failing statuses detected"
            skipped=$((skipped + 1))
            failing_statuses=true
        fi
    fi
    if [ "$failing_statuses" = true ]; then
        continue
    fi

    # Fetch and merge PR
    if git fetch "$UPSTREAM_REMOTE" "pull/${number}/head:pr-${number}" >/dev/null 2>&1; then
        if git merge --no-edit "pr-${number}" >/dev/null 2>&1; then
            echo "  MERGED"
            merged=$((merged + 1))
        else
            echo "  SKIPPED: merge conflict"
            git merge --abort >/dev/null 2>&1 || true
            skipped=$((skipped + 1))
        fi
    else
        echo "  SKIPPED: fetch failed"
        skipped=$((skipped + 1))
    fi
done

echo ""
echo "==> Summary: $merged merged, $skipped skipped"
echo "==> Pushing bleeding-edge..."
git push origin bleeding-edge --force-with-lease
echo "==> Done!"
