#!/usr/bin/env bash
# Validate a CycloneDX SBOM JSON file.
#
# Usage: validate_sbom.sh <sbom_file>
#
# Exits non-zero if the file is missing, not valid JSON, or does not have
# bomFormat == "CycloneDX". Reports component count on success.

set -euo pipefail

SBOM_FILE="${1:?Usage: $0 <sbom_file>}"

python3 -c "
import json, sys
with open('${SBOM_FILE}') as f:
    data = json.load(f)
bom_format = data.get('bomFormat', '<missing>')
if bom_format != 'CycloneDX':
    print(f'ERROR: unexpected bomFormat: {bom_format}', file=sys.stderr)
    sys.exit(1)
component_count = len(data.get('components', []))
print(f'SBOM validation: OK (file=${SBOM_FILE}, bomFormat={bom_format}, components={component_count})')
"
