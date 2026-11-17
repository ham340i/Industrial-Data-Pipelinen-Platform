#!/usr/bin/env bash
# AI contribution: 50% or more AI-generated
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/setup.py" milestones "$@"
