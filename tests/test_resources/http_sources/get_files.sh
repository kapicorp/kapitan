#!/usr/bin/env bash

set -euo pipefail

URLS=(
  "https://github.com/kapicorp/kapitan/raw/4897ec6/examples/docker/components/jsonnet/jsonnet.jsonnet"
  "https://github.com/kapicorp/kapitan/raw/4897ec6/examples/docker/components/kadet/__init__.py"
  "https://github.com/BurdenBear/kube-charts-mirror/raw/e452e07/docs/nfs-client-provisioner-1.2.8.tgz"
  "https://github.com/BurdenBear/kube-charts-mirror/raw/e452e07/docs/prometheus-pushgateway-1.2.13.tgz"
  "https://github.com/BurdenBear/kube-charts-mirror/raw/e452e07/docs/prometheus-11.3.0.tgz"
)

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for url in "${URLS[@]}"; do
  commit_hash="$(echo "${url}" | sed -n 's#.*/raw/\([0-9a-f]\{7,\}\)/.*#\1#p')"
  filename="$(basename "${url}")"
  output_path="${script_dir}/${commit_hash}.${filename}"

  [[ -f "${output_path}" ]] && continue

  curl --fail --silent --show-error --location \
    --output "${output_path}" \
    "${url}"

  chmod 444 "${output_path}"
done
