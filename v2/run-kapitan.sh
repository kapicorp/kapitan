#!/bin/bash
# Helper script to run Kapitan v2 with correct Python path
PYTHONPATH=/home/coder/kapitan/v2/src uv run python -m kapitan.cli.main "$@"