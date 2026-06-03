#!/usr/bin/env bash
set -euo pipefail

# Fetches mechanical code review check definitions from the architecture repo.
# Single GraphQL query fetches tree entries with blob text in one call.
#
# Requires: gh CLI authenticated with repo access.
# Output: delimited sections prefixed with ===== check/<name>.md =====
# Errors: reported under ===== FETCH FAILURES =====
#
# Compatible with Bash 3.2+ (no associative arrays).

for cmd in gh jq; do
  if ! command -v "$cmd" &>/dev/null; then
    printf '===== FETCH FAILURES =====\n%s is not installed\n' "$cmd"
    exit 0
  fi
done

RESPONSE=$(gh api graphql -f query='
{
  repository(owner: "openshift-hyperfleet", name: "architecture") {
    object(expression: "main:hyperfleet/standards/code-review") {
      ... on Tree {
        entries {
          name
          type
          object { ... on Blob { text } }
        }
      }
    }
  }
}
' 2>&1) || {
  printf '===== FETCH FAILURES =====\nGraphQL query failed: %s\n' "$RESPONSE"
  exit 0
}

# Print successful entries (non-null text)
OUTPUT=$(echo "$RESPONSE" | jq -r '
  [.data.repository.object.entries // [] | .[]
   | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md"))]
  | if length == 0 then empty
    else .[] | select(.object.text != null) | "===== check/\(.name) =====\n\(.object.text)\n"
    end
' 2>&1) || {
  printf '===== FETCH FAILURES =====\njq parsing failed: %s\n' "$OUTPUT"
  exit 0
}

if [ -n "$OUTPUT" ]; then
  echo "$OUTPUT"
fi

# Report failures: null blobs or empty directory
FAILURES=$(echo "$RESPONSE" | jq -r '
  [.data.repository.object.entries // [] | .[]
   | select(.type == "blob" and (.name | endswith(".md")) and (.name != "README.md") and (.name != "CLAUDE.md"))]
  | if length == 0 then "No .md files found in hyperfleet/standards/code-review/"
    else [.[] | select(.object.text == null) | "check/\(.name): returned null"] | .[]
    end
' 2>&1) || FAILURES="Failed to check for null entries"

if [ -n "$FAILURES" ]; then
  printf '===== FETCH FAILURES =====\n%s\n' "$FAILURES"
fi
