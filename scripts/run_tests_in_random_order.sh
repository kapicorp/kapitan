#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="/tmp/run_tests_in_random_order"
LOG="${BASE_DIR}/log"
# 0 means "infinite"
DEFAULT_MAX_ITERS=0
MAX_ITERS="${RUN_TESTS_MAX_ITERS:-${DEFAULT_MAX_ITERS}}"


_extract_seed() {
  local run_file="${1}"
  sed -n 's/.*--random-order-seed=\([0-9][0-9]*\).*/\1/p' "${run_file}" | tail -n 1
}

_usage() {
  cat <<'EOF'
Usage:
  scripts/run_tests_in_random_order.sh [MAX_ITERS]

Arguments:
  MAX_ITERS   Optional number of iterations to run. 0 means infinite.

Environment:
  RUN_TESTS_MAX_ITERS   Optional default for MAX_ITERS (arg takes precedence).
EOF
}

_parse_args() {
  local arg_max_iters="${1:-}"

  if [[ "${arg_max_iters}" == "-h" || "${arg_max_iters}" == "--help" ]]; then
    _usage
    exit 0
  fi

  if [[ -n "${arg_max_iters}" ]]; then
    MAX_ITERS="${arg_max_iters}"
  fi

  if ! [[ "${MAX_ITERS}" =~ ^[0-9]+$ ]]; then
    echo "ERROR: MAX_ITERS must be a non-negative integer (got '${MAX_ITERS}')." >&2
    exit 1
  fi
}

_run_tests() {
  local iteration="${1}"
  local run_file="${BASE_DIR}/.run.${iteration}"
  local seed

  echo -n "$(date) - iteration: ${iteration} ... "

  if {
    echo "timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo "iteration=${iteration}"
    echo "requested_seed=${PYTEST_RANDOM_SEED:-auto}"
    echo
    echo "=== make clean ==="
    make clean
    echo
    echo "=== make setup ==="
    make setup
    echo
    echo "=== make tests ==="
    make tests
  } > "${run_file}" 2>&1; then
    seed="$(_extract_seed "${run_file}")"
    rm -f "${run_file}"
    if [[ -n "${seed}" ]]; then
      echo "PASS (seed: ${seed})"
    else
      echo "PASS"
    fi
    return 0
  else
    local failure_file
    seed="$(_extract_seed "${run_file}")"
    if [[ -n "${seed}" ]]; then
      failure_file="${BASE_DIR}/seed.${seed}"
    else
      failure_file="${BASE_DIR}/iteration.${iteration}"
    fi
    mv -f "${run_file}" "${failure_file}"
    echo "FAILED (log: ${failure_file})"
    return 1
  fi
}

_parse_args "${1:-}"

mkdir -p "${BASE_DIR}"
rm -rf "${BASE_DIR}/.run"*

{
  local_iteration=0
  local_failures=0

  while true; do
    local_iteration=$((local_iteration + 1))
    if ! _run_tests "${local_iteration}"; then
      local_failures=$((local_failures + 1))
    fi

    if (( MAX_ITERS > 0 && local_iteration >= MAX_ITERS )); then
      break
    fi
  done

  echo
  echo "Summary: iterations=${local_iteration} failures=${local_failures} log=${LOG}"
} 2>&1 | tee "${LOG}"
