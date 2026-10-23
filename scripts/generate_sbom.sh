#!/usr/bin/env bash
# Generate a CycloneDX SBOM JSON for the kapitan Python package release.
#
# Usage: generate_sbom.sh <version> [output_dir]
#
# Must be run from the repository root (pyproject.toml must be present in $PWD).
# Exports the maximal supported install (production deps + all optional extras)
# via uv and generates a CycloneDX JSON SBOM using cyclonedx-py.
# The tool validates the output against the CycloneDX schema by default.
#
# Output filename: kapitan-${VERSION}.python.sbom.cdx.json
# The ".python." infix distinguishes this from the per-platform Docker image
# SBOMs which are named kapitan-${VERSION}-py<X>-<platform>-docker.sbom.cdx.json.

set -euo pipefail

VERSION="${1:?Usage: $0 <version> [output_dir]}"
OUTPUT_DIR="${2:-dist}"
OUTPUT_FILE="${OUTPUT_DIR}/kapitan-${VERSION}.python.sbom.cdx.json"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Generating SBOM for kapitan ${VERSION} ==="

REQUIREMENTS_FILE="$(mktemp /tmp/kapitan-requirements-XXXXXX.txt)"
TMP_RAW="$(mktemp /tmp/kapitan-requirements-raw-XXXXXX.txt)"
trap 'rm -f "${REQUIREMENTS_FILE}" "${TMP_RAW}"' EXIT

# Export production deps + all optional extras.
# --no-dev:           exclude the 'dev' dependency group
# --no-group test:    exclude the 'test' dependency group
# --no-group docs:    exclude the 'docs' dependency group
# --all-extras:       include gojsonnet/omegaconf/reclass-rs (PEP 621 extras)
# --no-editable:      strip the editable self-reference (-e .)

uv export \
    --no-dev \
    --no-group test \
    --no-group docs \
    --all-extras \
    --no-editable \
    --format requirements-txt \
    --no-hashes \
    --output-file "${TMP_RAW}"

# Strip comments, blank lines, and the bare '.' self-reference (left behind
# by `uv export --no-editable`) so cyclonedx-py does not warn about an
# unpinned 'unknown' component for the project itself.
grep -Ev '^[[:space:]]*(#|\.[[:space:]]*$|$)' "${TMP_RAW}" > "${REQUIREMENTS_FILE}"

echo "Exported $(wc -l < "${REQUIREMENTS_FILE}") dependency lines"

# Generate CycloneDX SBOM from requirements.
# cyclonedx-bom is pinned to >=4,<5 to prevent silent CLI breakage on major bumps.
# --validate (default=on) checks the output against the CycloneDX schema.
# --output-reproducible strips timestamps/random UUIDs for deterministic output.
# Note: --pyproject is intentionally omitted; it crashes cyclonedx-bom 4.x
#       (observed in 4.6.1 with "'str' object has no attribute 'get'").
#       Re-evaluate when bumping to cyclonedx-bom 5.x.
# --python 3.13: run the tool under a Python with prebuilt lxml wheels. lxml is
#       a transitive dep of cyclonedx-python-lib[validation] and has no cp314
#       wheels yet, so on Python 3.14 uv builds it from source and fails on
#       runners lacking libxml2/libxslt dev headers. Pinning the tool's
#       interpreter keeps it independent of the project's Python, which tracks
#       pyproject's requires-python upper bound (<3.15) and may select 3.14.
uvx --python 3.13 --from 'cyclonedx-bom>=4,<5' cyclonedx-py requirements \
    --mc-type application \
    --of JSON \
    --output-reproducible \
    -o "${OUTPUT_FILE}" \
    "${REQUIREMENTS_FILE}"

echo "SBOM written to: ${OUTPUT_FILE}"

"${SCRIPT_DIR}/validate_sbom.sh" "${OUTPUT_FILE}"
