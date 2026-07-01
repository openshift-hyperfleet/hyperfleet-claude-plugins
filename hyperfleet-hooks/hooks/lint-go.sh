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

# Determine whether we're in a git repo with at least one commit, so we can
# scope lint findings to changed lines via --new-from-rev. If not, fall back
# to linting the whole package (whole-file gate) since there's no baseline
# to diff against.
USE_NEW_FROM_REV=false
if git -C "$LINT_DIR" rev-parse HEAD &>/dev/null; then
  USE_NEW_FROM_REV=true
fi

# If the file is untracked (brand-new), register it as intent-to-add so
# git diff HEAD includes all its lines as "new" and --new-from-rev works.
if [[ "$USE_NEW_FROM_REV" == true ]]; then
  if ! git -C "$LINT_DIR" ls-files --error-unmatch "$FILE_PATH" &>/dev/null; then
    git -C "$LINT_DIR" add -N "$FILE_PATH"
  fi
fi

LINT_ARGS=(run)
if [[ "$USE_NEW_FROM_REV" == true ]]; then
  # Only report issues on lines new/changed relative to HEAD, including
  # uncommitted working-tree changes. Pre-existing issues elsewhere in the
  # file/package are ignored.
  LINT_ARGS+=(--new-from-rev=HEAD)
fi
LINT_ARGS+=("$LINT_DIR/...")

LINT_OUTPUT=$(golangci-lint "${LINT_ARGS[@]}" 2>&1)
RETCODE=$?

if [[ $RETCODE -eq 0 ]]; then
  exit 0
elif [[ $RETCODE -eq 1 ]]; then
  if [[ "$USE_NEW_FROM_REV" == true ]]; then
    echo "golangci-lint found issues in lines you changed in $LINT_DIR:" >&2
  else
    echo "golangci-lint found issues in $LINT_DIR (no git baseline found, linted whole package):" >&2
  fi
  echo "$LINT_OUTPUT" >&2
  exit 2
else
  echo "golangci-lint failed to run (exit $RETCODE):" >&2
  echo "$LINT_OUTPUT" >&2
  exit 1
fi
