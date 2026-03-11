#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_INSTALL=0

usage() {
  cat <<'EOF'
Usage: scripts/check-ci.sh [--skip-install]

Run the same checks used by GitHub Actions:
1. website format check
2. console format check
3. pre-commit run --all-files

Options:
  --skip-install   Skip npm/pnpm dependency installation
EOF
}

for arg in "$@"; do
  case "$arg" in
    --skip-install)
      SKIP_INSTALL=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

run_step() {
  local title="$1"
  shift
  echo
  echo "==> $title"
  "$@"
}

require_cmd npm
require_cmd corepack
require_cmd pre-commit

cd "$ROOT_DIR"

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  run_step "Install console dependencies" npm --prefix console install
  run_step "Install website dependencies" bash -lc 'cd website && corepack pnpm install --frozen-lockfile'
fi

run_step "Website format check" bash -lc 'cd website && corepack pnpm run format:check'
run_step "Console format check" npm --prefix console run format:check
run_step "Pre-commit checks" pre-commit run --all-files

echo
echo "All local CI checks passed."
