#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "Running yamllint..."
command -v yamllint >/dev/null
find . -type d \( -name .git -o -name node_modules -o -name .venv \) -prune -o \
  -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 | \
  xargs -0 sh -c 'if [ "$#" -gt 0 ]; then exec yamllint --strict "$@"; fi' sh
echo "yamllint passed."
