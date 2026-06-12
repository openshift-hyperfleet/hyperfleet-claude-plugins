#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(dirname "$SCRIPT_DIR")"
FIXTURES="$SCRIPT_DIR/fixtures.json"
NOW="2026-06-08T10:00:00Z"

PASS=0
FAIL=0
TMPFILES=()
trap 'rm -f "${TMPFILES[@]}"' EXIT

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    printf "  ✓ %s\n" "$label"
    PASS=$((PASS + 1))
  else
    printf "  ✗ %s: expected '%s', got '%s'\n" "$label" "$expected" "$actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    printf "  ✓ %s\n" "$label"
    PASS=$((PASS + 1))
  else
    printf "  ✗ %s: expected to contain '%s'\n" "$label" "$needle"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    printf "  ✗ %s: should not contain '%s'\n" "$label" "$needle"
    FAIL=$((FAIL + 1))
  else
    printf "  ✓ %s\n" "$label"
    PASS=$((PASS + 1))
  fi
}

# --- Run score.jq ---

echo "=== Scoring Tests ==="
if ! SCORED=$(jq --arg now "$NOW" -f "$SCRIPTS_DIR/score.jq" "$FIXTURES" 2>&1); then
  echo "FATAL: score.jq failed to run"
  echo "$SCORED"
  exit 1
fi

echo ""
echo "--- Test: PR count preserved ---"
SCORED_COUNT=$(echo "$SCORED" | jq '.scored_prs | length')
assert_eq "6 PRs scored" "6" "$SCORED_COUNT"

echo ""
echo "--- Test: Critical/Security PR (hyperfleet-adapter#88) → Tier 1 ---"
PR88=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-adapter" and .number == 88)')
assert_eq "Tier 1 (Blocker/Critical override)" "1" "$(echo "$PR88" | jq '.provisional_tier')"
assert_eq "Override: JIRA Blocker/Critical" '"JIRA Blocker/Critical"' "$(echo "$PR88" | jq '.override_info.reason')"
assert_eq "Factor 1: Critical + Security activity = 10" "10" "$(echo "$PR88" | jq '.scores.factor1.score')"
assert_eq "Factor 4: risk/high label floor = 10 (max of label 8, label_signal 10)" "10" "$(echo "$PR88" | jq '.scores.factor4.score')"
assert_eq "Factor 7: CI passing = 10" "10" "$(echo "$PR88" | jq '.scores.factor7.score')"
assert_eq "Factor 2: 1 blocking link, high-priority = 8" "8" "$(echo "$PR88" | jq '.scores.factor2.score')"

echo ""
echo "--- Test: Draft PR (hyperfleet-api#120) → Tier 4 ---"
PR120=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-api" and .number == 120)')
assert_eq "Tier 4 (draft)" "4" "$(echo "$PR120" | jq '.provisional_tier')"
assert_eq "Override reason: Draft" '"Draft"' "$(echo "$PR120" | jq '.override_info.reason')"
assert_eq "No JIRA ticket" "0" "$(echo "$PR120" | jq '.jira_keys | length')"

echo ""
echo "--- Test: CI failing PR (hyperfleet-e2e#33) → Tier 4 ---"
PR33=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-e2e" and .number == 33)')
assert_eq "Tier 4 (CI failing)" "4" "$(echo "$PR33" | jq '.provisional_tier')"
assert_eq "Override reason: CI failing" '"CI failing"' "$(echo "$PR33" | jq '.override_info.reason')"
assert_eq "Factor 7: CI failing = 0" "0" "$(echo "$PR33" | jq '.scores.factor7.score')"

echo ""
echo "--- Test: Waiting on author PR (hyperfleet-chart#55) → Tier 4 ---"
PR55=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-chart" and .number == 55)')
assert_eq "Tier 4 (waiting on author)" "4" "$(echo "$PR55" | jq '.provisional_tier')"
assert_eq "Override reason: Waiting on author" '"Waiting on author"' "$(echo "$PR55" | jq '.override_info.reason')"
assert_eq "Factor 5: waiting_on_author = true" "true" "$(echo "$PR55" | jq '.scores.factor5.waiting_on_author')"

echo ""
echo "--- Test: Normal PR scoring (hyperfleet-api#115) ---"
PR115=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-api" and .number == 115)')
assert_eq "Tier 2" "2" "$(echo "$PR115" | jq '.provisional_tier')"
assert_eq "No override" "null" "$(echo "$PR115" | jq '.override_info.override')"
assert_eq "Factor 1: Major + in sprint + boost" "8" "$(echo "$PR115" | jq '.scores.factor1.score')"
assert_eq "Factor 3: 14d old, no reviews = 9" "9" "$(echo "$PR115" | jq '.scores.factor3.score')"
assert_eq "Factor 4: risk/medium label floor 6, label_signal 7 (bug label) → max 7" "7" "$(echo "$PR115" | jq '.scores.factor4.score')"
assert_eq "Factor 5: zero engagement >2d = 10" "10" "$(echo "$PR115" | jq '.scores.factor5.score')"
assert_eq "Factor 6: 279 lines = 6" "6" "$(echo "$PR115" | jq '.scores.factor6.score')"
assert_eq "Factor 8: 5 story points = 6" "6" "$(echo "$PR115" | jq '.scores.factor8.score')"

echo ""
echo "--- Test: Waiting on author PR (hyperfleet-sentinel#42) ---"
PR42=$(echo "$SCORED" | jq '.scored_prs[] | select(.repo == "hyperfleet-sentinel" and .number == 42)')
WAITING=$(echo "$PR42" | jq '.scores.factor5.waiting_on_author')
assert_eq "Reviewer commented with no author response → waiting" "true" "$WAITING"
assert_eq "Tier 4 override" "4" "$(echo "$PR42" | jq '.provisional_tier')"

echo ""
echo "--- Test: Sorting order (score descending) ---"
FIRST_REPO=$(echo "$SCORED" | jq -r '.scored_prs[0].repo')
FIRST_NUM=$(echo "$SCORED" | jq '.scored_prs[0].number')
assert_eq "Highest score PR first" "hyperfleet-adapter" "$FIRST_REPO"
assert_eq "PR #88 is first" "88" "$FIRST_NUM"

echo ""
echo "--- Test: Data completeness ---"
DC_88=$(echo "$PR88" | jq '.data_completeness')
DC_120=$(echo "$PR120" | jq '.data_completeness')
assert_eq "Full data PR completeness = 100" "100" "$DC_88"
assert_eq "No-JIRA PR completeness = 50" "50" "$DC_120"

echo ""
echo "--- Test: Flags ---"
assert_contains "SLA breach flag on 14d PR" "sla_breach" "$(echo "$PR115" | jq -c '.flags')"
assert_contains "No JIRA ticket flag on draft PR" "no_jira_ticket" "$(echo "$PR120" | jq -c '.flags')"
assert_contains "Stale flag on 14d PR" "stale" "$(echo "$PR115" | jq -c '.flags')"

# --- Run format-output.jq ---

echo ""
echo "=== Format Tests ==="

echo ""
echo "--- Test: Slack format ---"
if ! SLACK_OUT=$(echo "$SCORED" | jq --arg mode "slack" -rf "$SCRIPTS_DIR/format-output.jq" 2>&1); then
  echo "FATAL: format-output.jq (slack) failed"
  echo "$SLACK_OUT"
  exit 1
fi

assert_contains "Slack header emoji" "🚨 *Open PRs" "$SLACK_OUT"
assert_contains "Tier 1 section" "🚨 *Tier 1" "$SLACK_OUT"
assert_contains "PR link format" "<https://github.com/openshift-hyperfleet/" "$SLACK_OUT"
assert_contains "JIRA link inline in title" "<https://redhat.atlassian.net/browse/HYPERFLEET-1100|HYPERFLEET-1100>" "$SLACK_OUT"
assert_not_contains "No separate JIRA pipe in Slack" "| <https://redhat.atlassian.net" "$SLACK_OUT"
assert_contains "Slack status suffix" "No reviews," "$SLACK_OUT"
if echo "$SLACK_OUT" | grep -q ":[a-z_]*:"; then
  printf "  ✗ Should not contain Slack shortcodes\n"
  FAIL=$((FAIL + 1))
else
  printf "  ✓ No Slack shortcodes\n"
  PASS=$((PASS + 1))
fi

# Tier 4 section header should NOT appear in Slack
if echo "$SLACK_OUT" | grep -q '\*Tier 4'; then
  printf "  ✗ Tier 4 section should not appear in Slack output\n"
  FAIL=$((FAIL + 1))
else
  printf "  ✓ Tier 4 section not shown in Slack output\n"
  PASS=$((PASS + 1))
fi

echo ""
echo "--- Test: Slack format — Tier 3 hidden when >10 PRs ---"
# Create >10 PRs with some in Tier 3 (provisional_tier=3) to test visibility rule
MANY_TMP=$(mktemp)
TMPFILES+=("$MANY_TMP" "${MANY_TMP}.slack")
jq --arg now "$NOW" -f "$SCRIPTS_DIR/score.jq" "$FIXTURES" > "$MANY_TMP"
jq '
  .scored_prs as $orig |
  .scored_prs = ($orig + [
    $orig[] | .number += 1000 | .provisional_tier = 3 | .override_info = {override: null, reason: null}
  ] | .[0:12])
' "$MANY_TMP" | jq --arg mode "slack" -rf "$SCRIPTS_DIR/format-output.jq" > "${MANY_TMP}.slack"
if grep -q '\*Tier 3' "${MANY_TMP}.slack"; then
  printf "  ✗ Tier 3 section should not appear when >10 PRs\n"
  FAIL=$((FAIL + 1))
else
  printf "  ✓ Tier 3 hidden when >10 PRs\n"
  PASS=$((PASS + 1))
fi

echo ""
echo "--- Test: Compact format ---"
if ! COMPACT_OUT=$(echo "$SCORED" | jq --arg mode "compact" -rf "$SCRIPTS_DIR/format-output.jq" 2>&1); then
  echo "FATAL: format-output.jq (compact) failed"
  echo "$COMPACT_OUT"
  exit 1
fi

assert_contains "Compact header" "## Open PRs — openshift-hyperfleet" "$COMPACT_OUT"
assert_contains "Tier table header (3 columns)" "| # | PR | Status |" "$COMPACT_OUT"
assert_not_contains "No separate JIRA column" "| JIRA |" "$COMPACT_OUT"
assert_contains "JIRA ticket linked in title" "[HYPERFLEET-856](https://redhat.atlassian.net/browse/HYPERFLEET-856)" "$COMPACT_OUT"
assert_contains "Recommendation line" "**Start with:**" "$COMPACT_OUT"

echo ""
echo "--- Test: Compact format — PR without ticket has no JIRA link ---"
NOTIX_OUT=$(echo "$SCORED" | jq '.scored_prs |= [.[] | select(.jira_keys | length == 0) | .provisional_tier = 3 | .override_info = {override: null, reason: null}]' | \
  jq --arg mode "compact" -rf "$SCRIPTS_DIR/format-output.jq" 2>&1)
assert_not_contains "No JIRA link for no-ticket PR" "redhat.atlassian.net" "$NOTIX_OUT"

echo ""
echo "--- Test: Empty input ---"
EMPTY_SLACK=$(echo '{"metadata":{"generated_at":"2026-06-08","jira_available":true,"repos_with_prs":0},"scored_prs":[]}' | \
  jq --arg mode "slack" -rf "$SCRIPTS_DIR/format-output.jq" 2>&1)
assert_contains "Zero PRs message" "No open PRs found" "$EMPTY_SLACK"

# --- JIRA unavailable mode ---

echo ""
echo "--- Test: JIRA unavailable scoring ---"
if ! NOJIRA=$(jq '.metadata.jira_available = false' "$FIXTURES" | \
  jq --arg now "$NOW" -f "$SCRIPTS_DIR/score.jq" 2>&1); then
  echo "FATAL: score.jq failed with jira_available=false"
  echo "$NOJIRA"
  exit 1
fi

NOJIRA_F1=$(echo "$NOJIRA" | jq '.scored_prs[0].scores.factor1.score')
assert_eq "JIRA unavailable: Factor 1 defaults to 5" "5" "$NOJIRA_F1"

NOJIRA_F8=$(echo "$NOJIRA" | jq '.scored_prs[0].scores.factor8.score')
assert_eq "JIRA unavailable: Factor 8 defaults to 2" "2" "$NOJIRA_F8"

echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed"
echo "==============================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
