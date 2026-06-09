#!/usr/bin/env bash
set -uo pipefail # -e omitted: golangci-lint exit code handled explicitly

if ! command -v jq &>/dev/null; then
  echo "jq is required but not installed" >&2
  exit 1
fi

INPUT=$(cat)

FILE_PATH=$(printf '%s\n' "$INPUT" | jq -r '.tool_input.file_path // empty')
if [[ -z "$FILE_PATH" ]] || [[ "$FILE_PATH" != *.go ]] || [[ "$FILE_PATH" == *../* ]]; then
  exit 0
fi

if [[ ! -f "$FILE_PATH" ]] || [[ "$FILE_PATH" == */vendor/* ]]; then
  exit 0
fi

if ! command -v golangci-lint &>/dev/null; then
  echo "golangci-lint not found" >&2
  exit 1
fi

LINT_DIR=$(dirname -- "$FILE_PATH")
LINT_OUTPUT=$(golangci-lint run -- "$LINT_DIR" 2>&1) && exit 0

echo "golangci-lint found issues in $LINT_DIR:" >&2
echo "$LINT_OUTPUT" >&2
exit 2
