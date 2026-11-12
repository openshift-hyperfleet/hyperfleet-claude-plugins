#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # resolved at runtime
source "$SCRIPT_DIR/lib.sh"

# Repositories onboarded to a dependency bot. MintMaker owns the repositories
# that have a Konflux Component; the hosted Renovate app owns every other
# repository. Adding a repository here is enough: the platform is derived from
# the author of each PR, not from this list.
REPOS=(
  "openshift-hyperfleet/hyperfleet-sentinel"
  "openshift-hyperfleet/hyperfleet-adapter"
  "openshift-hyperfleet/hyperfleet-api"
  "openshift-hyperfleet/hyperfleet-applier"
  "openshift-hyperfleet/hyperfleet-operator"
  "openshift-hyperfleet/hyperfleet-broker"
  "openshift-hyperfleet/hyperfleet-e2e"
  "openshift-hyperfleet/hyperfleet-hooks"
  "openshift-hyperfleet/hyperfleet-logger"
  "openshift-hyperfleet/hyperfleet-credential-provider"
  "openshift-hyperfleet/hyperfleet-infra"
)

# Read the shared preset once per run. A failure is not fatal: repositories that
# override the schedule still work, and the others report preset-unreadable.
fetch_preset() {
  local preset
  if ! preset=$(gh api "repos/$PRESET_REPO/contents/$PRESET_FILE" --jq '.content' 2>/dev/null \
    | base64 -d); then
    echo "WARN: could not read the shared preset at $PRESET_REPO/$PRESET_FILE; affected repos will report schedule=preset-unreadable" >&2
    return 0
  fi
  printf '%s' "$preset"
}

# Emit one JSON object per open bot PR in a repository.
collect_repo() {
  local repo="$1" preset="$2"
  local short_name
  short_name="${repo##*/}"

  local config errfile
  errfile=$(mktemp)
  if ! config=$(gh api "repos/$repo/contents/renovate.json" --jq '.content' 2>"$errfile" \
    | base64 -d); then
    echo "WARN: could not read renovate.json for $repo: $(cat "$errfile")" >&2
    config=""
  fi
  rm -f "$errfile"

  local schedule schedule_timezone
  IFS=$'\t' read -r schedule schedule_timezone <<<"$(schedule_of "$config" "$preset")"

  local prs
  if ! prs=$(gh pr list --repo "$repo" --state open --limit 100 --json number,title,headRefName,headRefOid,mergeable,labels,statusCheckRollup,author,url \
    --jq "[.[] | select(.author.login | test(\"$BOT_AUTHOR_REGEX\"))]" 2>"$errfile"); then
    echo "ERROR: gh pr list failed for $repo: $(cat "$errfile")" >&2
    rm -f "$errfile"
    return 1
  fi
  rm -f "$errfile"

  local count
  count=$(echo "$prs" | jq 'length')

  if [ "$count" -eq 0 ]; then
    return
  fi

  echo "$prs" | jq -c '.[]' | while IFS= read -r pr; do
    local number title branch mergeable url author head_sha
    number=$(echo "$pr" | jq -r '.number')
    title=$(echo "$pr" | jq -r '.title')
    branch=$(echo "$pr" | jq -r '.headRefName')
    author=$(echo "$pr" | jq -r '.author.login')
    mergeable=$(echo "$pr" | jq -r '.mergeable')
    if [[ "$mergeable" == "UNKNOWN" ]]; then
      mergeable=$(gh pr view "$number" --repo "$repo" --json mergeable --jq '.mergeable' 2>/dev/null) || mergeable="UNKNOWN"
    fi
    url=$(echo "$pr" | jq -r '.url')
    head_sha=$(echo "$pr" | jq -r '.headRefOid')

    local labels
    labels=$(echo "$pr" | jq -r '[.labels[].name] | join(",")')

    local has_lgtm="false" has_approved="false" needs_rebase="false" has_ok_to_test="false"
    [[ ",$labels," == *",lgtm,"* ]] && has_lgtm="true"
    [[ ",$labels," == *",approved,"* ]] && has_approved="true"
    [[ ",$labels," == *",needs-rebase,"* ]] && needs_rebase="true"
    [[ ",$labels," == *",ok-to-test,"* ]] && has_ok_to_test="true"

    local policy platform bump_type
    policy=$(review_policy "$labels")
    platform=$(platform_for_author "$author")
    bump_type=$(classify_bump "$branch" "$title")

    local ci_state="unknown"
    local checks
    checks=$(echo "$pr" | jq -r '[.statusCheckRollup[]? | select(.context != "tide") | .state // empty] | if length == 0 then "none" elif all(. == "SUCCESS" or . == "NEUTRAL" or . == "SKIPPED") then "green" elif any(. == "FAILURE" or . == "ERROR") then "failed" elif any(. == "PENDING" or . == "EXPECTED" or . == "QUEUED" or . == "IN_PROGRESS") then "pending" else "unknown" end' 2>/dev/null) || checks="unknown"
    ci_state="$checks"

    local last_bot_commit lbc_err
    lbc_err=$(mktemp)
    if ! last_bot_commit=$(gh pr view "$number" --repo "$repo" --json commits --jq '[.commits[].committedDate] | last // ""' 2>"$lbc_err"); then
      echo "WARN: could not fetch commits for $repo#$number: $(cat "$lbc_err")" >&2
      last_bot_commit=""
    fi
    rm -f "$lbc_err"

    local conflicting="false"
    [[ "$mergeable" == "CONFLICTING" ]] && conflicting="true"

    jq -n \
      --arg repo "$short_name" \
      --arg full_repo "$repo" \
      --argjson number "$number" \
      --arg title "$title" \
      --arg branch "$branch" \
      --arg url "$url" \
      --arg author "$author" \
      --arg platform "$platform" \
      --arg bump_type "$bump_type" \
      --arg policy "$policy" \
      --arg ci_state "$ci_state" \
      --arg mergeable "$mergeable" \
      --argjson has_lgtm "$has_lgtm" \
      --argjson has_approved "$has_approved" \
      --argjson has_ok_to_test "$has_ok_to_test" \
      --argjson needs_rebase "$needs_rebase" \
      --argjson conflicting "$conflicting" \
      --arg schedule "$schedule" \
      --arg schedule_timezone "$schedule_timezone" \
      --arg last_bot_commit "$last_bot_commit" \
      --arg head_sha "$head_sha" \
      '{repo: $repo, full_repo: $full_repo, number: $number, title: $title, branch: $branch, url: $url, author: $author, platform: $platform, bump_type: $bump_type, policy: $policy, ci_state: $ci_state, mergeable: $mergeable, has_lgtm: $has_lgtm, has_approved: $has_approved, has_ok_to_test: $has_ok_to_test, needs_rebase: $needs_rebase, conflicting: $conflicting, schedule: $schedule, schedule_timezone: $schedule_timezone, last_bot_commit: $last_bot_commit, head_sha: $head_sha}'
  done
}

preset=$(fetch_preset)

results="[]"
for repo in "${REPOS[@]}"; do
  if ! repo_results=$(collect_repo "$repo" "$preset"); then
    echo "ERROR: data collection failed for $repo; skipping" >&2
    repo_results=""
  fi
  if [ -n "$repo_results" ]; then
    results=$(echo "$results" | jq --argjson new "$(echo "$repo_results" | jq -s '.')" '. + $new')
  fi
done

echo "$results" | jq '.'
