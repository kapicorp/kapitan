#!/usr/bin/env bash
# Generate SHA256SUMS for release artifacts.
#
# Usage: generate_checksums.sh <artifacts_dir> [output_file]
#
# Scans <artifacts_dir> for kapitan wheels, sdists, and SBOMs, then writes
# standard sha256sum-format entries to <output_file>.
# Defaults output_file to <artifacts_dir>/SHA256SUMS.
#
# Note: this script covers Python package artifacts only (wheel, sdist, SBOM).
# The PEX binary checksum is written to SHA256SUMS.pex by the PEX build workflow.
# Docker image SBOMs are uploaded as separate named assets without a shared manifest.

set -euo pipefail

ARTIFACTS_DIR="${1:?Usage: $0 <artifacts_dir> [output_file]}"
OUTPUT_FILE="${2:-${ARTIFACTS_DIR}/SHA256SUMS}"

echo "=== Generating SHA256 checksums in ${ARTIFACTS_DIR} ==="

ARTIFACT_FILES=()
while IFS= read -r -d '' file; do
    ARTIFACT_FILES+=("$(basename "${file}")")
done < <(find "${ARTIFACTS_DIR}" -maxdepth 1 \
    \( -name "kapitan-*.whl" \
    -o -name "kapitan-*.tar.gz" \
    -o -name "kapitan-*.python.sbom.cdx.json" \
    \) -print0 | sort -z)

if [[ ${#ARTIFACT_FILES[@]} -eq 0 ]]; then
    echo "ERROR: No artifacts found in ${ARTIFACTS_DIR}" >&2
    exit 1
fi

(
    cd "${ARTIFACTS_DIR}"
    sha256sum "${ARTIFACT_FILES[@]}"
) > "${OUTPUT_FILE}"

echo "Checksums written to: ${OUTPUT_FILE}"
cat "${OUTPUT_FILE}"
