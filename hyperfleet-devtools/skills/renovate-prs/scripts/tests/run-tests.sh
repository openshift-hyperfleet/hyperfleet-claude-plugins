#!/usr/bin/env bash
# Offline tests for the renovate-prs data collection helpers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(dirname "$SCRIPT_DIR")"
FIXTURES="$SCRIPT_DIR/fixtures.json"

# shellcheck disable=SC1091  # resolved at runtime
source "$SCRIPTS_DIR/lib.sh"

PASS=0
FAIL=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    printf "  ok   %s\n" "$label"
    PASS=$((PASS + 1))
  else
    printf "  FAIL %s: expected '%s', got '%s'\n" "$label" "$expected" "$actual"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Bump classification ==="
while IFS= read -r case_json; do
  name=$(echo "$case_json" | jq -r '.name')
  branch=$(echo "$case_json" | jq -r '.branch')
  title=$(echo "$case_json" | jq -r '.title')
  expected=$(echo "$case_json" | jq -r '.expected')
  assert_eq "$name" "$expected" "$(classify_bump "$branch" "$title")"
done < <(jq -c '.bump_cases[]' "$FIXTURES")

echo ""
echo "=== Review policy (from the shared preset labels) ==="
while IFS= read -r case_json; do
  name=$(echo "$case_json" | jq -r '.name')
  labels=$(echo "$case_json" | jq -r '.labels')
  expected=$(echo "$case_json" | jq -r '.expected')
  assert_eq "$name" "$expected" "$(review_policy "$labels")"
done < <(jq -c '.policy_cases[]' "$FIXTURES")

echo ""
echo "=== Bot author and platform detection ==="
while IFS= read -r case_json; do
  login=$(echo "$case_json" | jq -r '.login')
  expected_bot=$(echo "$case_json" | jq -r '.is_bot')
  expected_platform=$(echo "$case_json" | jq -r '.platform')
  if is_bot_author "$login"; then actual_bot="true"; else actual_bot="false"; fi
  assert_eq "is_bot_author($login)" "$expected_bot" "$actual_bot"
  if [ "$expected_bot" = "true" ]; then
    assert_eq "platform_for_author($login)" "$expected_platform" "$(platform_for_author "$login")"
  fi
done < <(jq -c '.author_cases[]' "$FIXTURES")

echo ""
echo "=== Effective schedule resolution ==="
PRESET_JSON=$(jq -c '.preset' "$FIXTURES")
while IFS= read -r case_json; do
  name=$(echo "$case_json" | jq -r '.name')
  config=$(echo "$case_json" | jq -r '.config')
  expected_schedule=$(echo "$case_json" | jq -r '.schedule')
  expected_timezone=$(echo "$case_json" | jq -r '.timezone')
  IFS=$'\t' read -r schedule timezone <<<"$(schedule_of "$config" "$PRESET_JSON")"
  assert_eq "$name: schedule" "$expected_schedule" "$schedule"
  assert_eq "$name: timezone" "$expected_timezone" "$timezone"
done < <(jq -c '.schedule_cases[]' "$FIXTURES")

echo ""
echo "=== Summary ==="
printf "  %d passed, %d failed\n" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
