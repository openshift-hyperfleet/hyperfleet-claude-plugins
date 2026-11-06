#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --write-baseline ) ]]; then
  echo "Usage: bash hack/markdownlint.sh [--write-baseline]" >&2
  exit 2
fi

results_dir=$(mktemp -d)
trap 'rm -rf "$results_dir"' EXIT
export MARKDOWNLINT_RESULTS="$results_dir/results.json"
status=0
echo "Running markdownlint-cli2..."
./node_modules/.bin/markdownlint-cli2 '**/*.md' || status=$?
# CLI exit 1 means findings; other failures must never be baseline exemptions.
if [[ $status -gt 1 ]]; then
  exit "$status"
fi
"${PYTHON:-python3}" hack/markdownlint-baseline.py "$MARKDOWNLINT_RESULTS" "$status" "$@"
