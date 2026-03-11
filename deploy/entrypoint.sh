#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "bash" ]]; then
  exec bash
fi

exec researchclaw app --host 0.0.0.0 --port "${PORT:-8088}"
