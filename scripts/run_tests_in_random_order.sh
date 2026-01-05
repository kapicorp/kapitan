#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="/tmp/run_tests_in_random_order"
LOG="${BASE_DIR}/log"


_rand_uint32() {
    # -An: base "no address", so we only get the numeric output
    # -N4: read 4 bytes
    # -D: output unsigned decimal ints
    od -An -N4 -D /dev/urandom | tr -d ' '
}

_pytest() {
  poetry run pytest -n auto --no-cov --random-order-seed="${1}"
}

_run_tests() {
  local seed
  seed="$(_rand_uint32)"

  local run_file="${BASE_DIR}/.run.${seed}"
  local failure_file="${BASE_DIR}/seed.${seed}"

  echo -n "$(date) - seed: ${seed} ... "

  make clean >/dev/null 2>&1

  if _pytest "${seed}" > "${run_file}" 2>&1; then
    rm -f "${run_file}"
    echo "PASS"
    return 0
  else
    mv -f "${run_file}" "${failure_file}"
    echo "FAILED"
    return 1
  fi
}

mkdir -p "${BASE_DIR}"
rm -rf "${BASE_DIR}/.run"*

{
  while true; do
    _run_tests || true
  done
} 2>&1 | tee "${LOG}"
