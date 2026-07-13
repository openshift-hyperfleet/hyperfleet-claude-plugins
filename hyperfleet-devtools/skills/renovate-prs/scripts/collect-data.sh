#!/usr/bin/env bash
set -euo pipefail

REPOS=("openshift-hyperfleet/hyperfleet-sentinel" "openshift-hyperfleet/hyperfleet-adapter" "openshift-hyperfleet/hyperfleet-api")
BOT_AUTHOR="^app/red-hat-konflux"

classify_bump() {
  local branch="$1" title="$2"
  if [[ "$branch" == *"major-"* ]] || echo "$title" | grep -qiE 'to v[0-9]+$'; then
    echo "major"
  elif [[ "$branch" == *"minorpatch"* ]] || [[ "$branch" == *"minor-patch"* ]] || echo "$title" | grep -qi "minor/patch"; then
    echo "minor/patch"
  elif [[ "$branch" == *"-digest"* ]] || echo "$title" | grep -qi "digest"; then
    echo "digest"
  elif [[ "$branch" == *"docker-image"* ]] || echo "$title" | grep -qi "docker image"; then
    echo "docker"
  else
    echo "unknown"
  fi
}

collect_repo() {
  local repo="$1"
  local short_name
  short_name=$(echo "$repo" | sed 's|openshift-hyperfleet/||')

  local schedule errfile
  errfile=$(mktemp)
  if ! schedule=$(gh api "repos/$repo/contents/renovate.json" --jq '.content' 2>"$errfile" \
    | base64 -d \
    | jq -r '(.schedule // []) | join(", ")'); then
    echo "WARN: could not read renovate.json schedule for $repo: $(cat "$errfile")" >&2
    schedule="unknown"
  fi
  [ -z "$schedule" ] && schedule="unknown"

  local prs
  if ! prs=$(gh pr list --repo "$repo" --state open --limit 100 --json number,title,headRefName,mergeable,labels,statusCheckRollup,author,url \
    --jq "[.[] | select(.author.login | test(\"$BOT_AUTHOR\"))]" 2>"$errfile"); then
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
    local number title branch mergeable url
    number=$(echo "$pr" | jq -r '.number')
    title=$(echo "$pr" | jq -r '.title')
    branch=$(echo "$pr" | jq -r '.headRefName')
    mergeable=$(echo "$pr" | jq -r '.mergeable')
    url=$(echo "$pr" | jq -r '.url')

    local labels
    labels=$(echo "$pr" | jq -r '[.labels[].name] | join(",")')

    local has_lgtm="false" has_approved="false" needs_rebase="false"
    [[ "$labels" == *"lgtm"* ]] && has_lgtm="true"
    [[ "$labels" == *"approved"* ]] && has_approved="true"
    [[ "$labels" == *"needs-rebase"* ]] && needs_rebase="true"

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

    local bump_type
    bump_type=$(classify_bump "$branch" "$title")

    local conflicting="false"
    [[ "$mergeable" == "CONFLICTING" ]] && conflicting="true"

    jq -n \
      --arg repo "$short_name" \
      --arg full_repo "$repo" \
      --argjson number "$number" \
      --arg title "$title" \
      --arg branch "$branch" \
      --arg url "$url" \
      --arg bump_type "$bump_type" \
      --arg ci_state "$ci_state" \
      --arg mergeable "$mergeable" \
      --argjson has_lgtm "$has_lgtm" \
      --argjson has_approved "$has_approved" \
      --argjson needs_rebase "$needs_rebase" \
      --argjson conflicting "$conflicting" \
      --arg schedule "$schedule" \
      --arg last_bot_commit "$last_bot_commit" \
      '{repo: $repo, full_repo: $full_repo, number: $number, title: $title, branch: $branch, url: $url, bump_type: $bump_type, ci_state: $ci_state, mergeable: $mergeable, has_lgtm: $has_lgtm, has_approved: $has_approved, needs_rebase: $needs_rebase, conflicting: $conflicting, schedule: $schedule, last_bot_commit: $last_bot_commit}'
  done
}

results="[]"
for repo in "${REPOS[@]}"; do
  if ! repo_results=$(collect_repo "$repo"); then
    echo "ERROR: data collection failed for $repo; skipping" >&2
    repo_results=""
  fi
  if [ -n "$repo_results" ]; then
    results=$(echo "$results" | jq --argjson new "$(echo "$repo_results" | jq -s '.')" '. + $new')
  fi
done

echo "$results" | jq '.'
