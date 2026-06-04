#!/usr/bin/env bash
set -euo pipefail

# Fetches HyperFleet standards and component docs from the architecture repo.
# Single GraphQL query fetches tree entries with blob text in one call.
#
# Requires: gh CLI authenticated with repo access.
# Output: delimited sections prefixed with ===== <name>.md ===== or
#         ===== component/<name>/<file>.md =====
# Errors: reported under ===== FETCH FAILURES =====
#
# Compatible with Bash 3.2+ (no associative arrays).

for cmd in gh jq; do
  if ! command -v "$cmd" &>/dev/null; then
    printf '===== FETCH FAILURES =====\n%s is not installed\n' "$cmd"
    exit 0
  fi
done

# Detect component from project directory (optional arg, defaults to pwd)
RAW_DIR="$(basename "${1:-$(pwd)}")"
if [[ "$RAW_DIR" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  COMPONENT="${RAW_DIR#hyperfleet-}"
else
  COMPONENT=""
fi

if [ -n "$COMPONENT" ]; then
  COMPONENT_FIELD='componentDocs: object(expression: $cmpExpr) { ... on Tree { entries { name type object { ... on Blob { text } } } } }'
  QUERY_VARS='query($cmpExpr: String!)'
  GH_EXTRA_ARGS=(-f "cmpExpr=main:hyperfleet/components/$COMPONENT")
else
  COMPONENT_FIELD=""
  QUERY_VARS=""
  GH_EXTRA_ARGS=()
fi

RESPONSE=$(gh api graphql ${GH_EXTRA_ARGS[@]+"${GH_EXTRA_ARGS[@]}"} -f query="
$QUERY_VARS {
  repository(owner: \"openshift-hyperfleet\", name: \"architecture\") {
    standards: object(expression: \"main:hyperfleet/standards\") {
      ... on Tree {
        entries {
          name
          type
          object { ... on Blob { text } }
        }
      }
    }
    $COMPONENT_FIELD
  }
}
" 2>&1) || {
  printf '===== FETCH FAILURES =====\nGraphQL query failed: %s\n' "$RESPONSE"
  exit 0
}

# Print standards (top-level .md files only, skip directories)
STD_OUTPUT=$(echo "$RESPONSE" | jq -r '
  [.data.repository.standards.entries // [] | .[]
   | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md"))]
  | if length == 0 then empty
    else .[] | select(.object.text != null) | "===== \(.name) =====\n\(.object.text)\n"
    end
' 2>&1) || {
  printf '===== FETCH FAILURES =====\njq parsing failed: %s\n' "$STD_OUTPUT"
  exit 0
}

if [ -n "$STD_OUTPUT" ]; then
  echo "$STD_OUTPUT"
fi

# Print component docs (if path exists)
if [ -n "$COMPONENT" ]; then
  CMP_OUTPUT=$(echo "$RESPONSE" | jq -r --arg component "$COMPONENT" '
    if .data.repository.componentDocs == null then empty
    else
      [.data.repository.componentDocs.entries // [] | .[]
       | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md"))]
      | .[] | select(.object.text != null)
      | "===== component/\($component)/\(.name) =====\n\(.object.text)\n"
    end
  ' 2>&1) || {
    printf '===== FETCH FAILURES =====\njq parsing failed for component docs: %s\n' "$CMP_OUTPUT"
    CMP_OUTPUT=""
  }

  if [ -n "$CMP_OUTPUT" ]; then
    echo "$CMP_OUTPUT"
  fi
fi

# Report failures
FAILURES=""

STD_FAILURES=$(echo "$RESPONSE" | jq -r '
  [.data.repository.standards.entries // [] | .[]
   | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md"))]
  | if length == 0 then "No .md files found in hyperfleet/standards/"
    else [.[] | select(.object.text == null) | "\(.name): returned null"] | .[]
    end
' 2>&1) || STD_FAILURES="Failed to check for null entries"

if [ -n "$STD_FAILURES" ]; then
  FAILURES="$STD_FAILURES"
fi

if [ -n "$COMPONENT" ]; then
  CMP_FAILURES=$(echo "$RESPONSE" | jq -r --arg component "$COMPONENT" '
    if .data.repository.componentDocs == null then empty
    else
      [.data.repository.componentDocs.entries // [] | .[]
       | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md") and .object.text == null)]
      | .[] | "component/\($component)/\(.name): returned null"
    end
  ' 2>&1) || CMP_FAILURES="Failed to check component null entries"

  if [ -n "$CMP_FAILURES" ]; then
    FAILURES="${FAILURES:+$FAILURES
}$CMP_FAILURES"
  fi
fi

if [ -n "$FAILURES" ]; then
  printf '===== FETCH FAILURES =====\n%s\n' "$FAILURES"
fi
