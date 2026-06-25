#!/usr/bin/env bash
set -euo pipefail

# Parallel data fetcher for /open-prs skill.
# Collects PR metadata, JIRA enrichment, review comments, CI status, and diffs.
# Output: single JSON object to stdout. Progress messages to stderr.
# Compatible with Bash 3.2+ (no associative arrays).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}/../../.."

REPO_FILTER=""
COMPONENT_FILTER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo|--component|--base-dir)
      if [ -z "${2:-}" ] || case "$2" in -*) true;; *) false;; esac; then
        echo "Missing value for $1" >&2; exit 2
      fi
      case "$1" in
        --repo)      REPO_FILTER="$2" ;;
        --component) COMPONENT_FILTER="$2" ;;
        --base-dir)  BASE_DIR="$2" ;;
      esac
      shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

REPOS_FILE="${BASE_DIR}/references/github-repos.md"
if [ ! -f "$REPOS_FILE" ]; then
  REPOS_FILE="${BASE_DIR}/../../references/github-repos.md"
fi
TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

emit_error_json() {
  local msg="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg err "$msg" '{"metadata":{"error":$err,"jira_available":false,"repos_queried":0,"repos_failed":[],"total_prs":0,"warnings":[]},"prs":[]}'
    return
  fi
  msg=${msg//\\/\\\\}
  msg=${msg//\"/\\\"}
  msg=${msg//$'\n'/\\n}
  printf '{"metadata":{"error":"%s","jira_available":false,"repos_queried":0,"repos_failed":[],"total_prs":0,"warnings":[]},"prs":[]}\n' "$msg"
}

for cmd in gh jq; do
  if ! command -v "$cmd" &>/dev/null; then
    emit_error_json "$cmd is not installed"
    exit 0
  fi
done

if ! gh auth status &>/dev/null 2>&1; then
  emit_error_json "gh CLI is not authenticated"
  exit 0
fi

JIRA_AVAILABLE=false
if command -v jira &>/dev/null; then
  JIRA_AVAILABLE=true
fi

if [ -n "$COMPONENT_FILTER" ] && [ "$JIRA_AVAILABLE" != "true" ]; then
  emit_error_json "--component requires JIRA CLI but jira is not available"
  exit 0
fi

if [ ! -f "$REPOS_FILE" ]; then
  emit_error_json "github-repos.md not found at $REPOS_FILE"
  exit 0
fi

REPOS=$(grep -oE '`[a-zA-Z0-9_-]+`' "$REPOS_FILE" | tr -d '`' | sort -u)

if [ -z "$REPOS" ]; then
  emit_error_json "No repositories parsed from $REPOS_FILE"
  exit 0
fi

if [ -n "$REPO_FILTER" ]; then
  if ! echo "$REPOS" | grep -Fxq "$REPO_FILTER"; then
    emit_error_json "Invalid repo: $REPO_FILTER. Valid repos: $(echo "$REPOS" | tr '\n' ', ')"
    exit 0
  fi
  REPOS="$REPO_FILTER"
fi

REPO_COUNT=$(echo "$REPOS" | wc -l | tr -d ' ')
echo "Fetching PRs from $REPO_COUNT repos..." >&2

# --- Phase 1: Fetch all open PRs across repos (parallel) ---

PR_FIELDS="number,title,author,createdAt,updatedAt,additions,deletions,changedFiles,reviewDecision,labels,isDraft,reviewRequests,url,headRefName,statusCheckRollup,latestReviews"

mkdir -p "$TMPDIR_WORK/prs" "$TMPDIR_WORK/repo_errors"

fetch_repo_prs() {
  local repo="$1"
  local outfile="$TMPDIR_WORK/prs/${repo}.json"
  local errfile="$TMPDIR_WORK/repo_errors/${repo}.txt"

  if result=$(gh pr list --repo "openshift-hyperfleet/$repo" --state open \
    --limit 100 --json "$PR_FIELDS" 2>"$errfile"); then
    if echo "$result" | jq -c --arg repo "$repo" '[.[] | . + {repo: $repo}]' > "${outfile}.tmp" 2>/dev/null \
       && [ -s "${outfile}.tmp" ] && jq empty "${outfile}.tmp" 2>/dev/null; then
      mv "${outfile}.tmp" "$outfile"
      rm -f "$errfile"
    else
      rm -f "${outfile}.tmp"
      echo "jq processing failed for repo: $repo" >> "$errfile"
    fi
  fi
}

for repo in $REPOS; do
  fetch_repo_prs "$repo" &
done
wait

ALL_PRS="$TMPDIR_WORK/all_prs.json"
if compgen -G "$TMPDIR_WORK"/prs/*.json > /dev/null 2>&1; then
  jq -s 'add' "$TMPDIR_WORK"/prs/*.json > "$ALL_PRS"
else
  echo '[]' > "$ALL_PRS"
fi

REPO_ERRORS="[]"
for f in "$TMPDIR_WORK"/repo_errors/*.txt; do
  [ -f "$f" ] || continue
  repo_name=$(basename "$f" .txt)
  error_msg=$(tr '\n' ' ' < "$f" | jq -Rs '.')
  REPO_ERRORS=$(echo "$REPO_ERRORS" | jq --arg r "$repo_name" --argjson e "$error_msg" '. + [{"repo": $r, "error": $e}]')
done

TOTAL_PRS=$(jq 'length' "$ALL_PRS")
echo "Found $TOTAL_PRS open PRs" >&2

if [ "$TOTAL_PRS" -eq 0 ]; then
  jq -n \
    --argjson jira "$JIRA_AVAILABLE" \
    --argjson queried "$REPO_COUNT" \
    --argjson repos_with_prs "0" \
    --argjson errors "$REPO_ERRORS" \
    --arg component "${COMPONENT_FILTER:-}" \
    '{
      metadata: {
        generated_at: (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
        jira_available: $jira,
        repos_queried: $queried,
        repos_with_prs: $repos_with_prs,
        repos_failed: $errors,
        total_prs: 0,
        component_filter: (if $component == "" then null else $component end),
        warnings: []
      },
      prs: []
    }'
  exit 0
fi

# --- Phase 2: Extract JIRA keys and fetch ticket details ---

echo "Extracting JIRA ticket keys..." >&2

JIRA_KEYS=$(jq -r '.[].title' "$ALL_PRS" | \
  grep -oE '(HYPERFLEET|ROSAENG|AIHCM)-[0-9]+' | \
  sort -u || true)

JIRA_KEY_COUNT=$(echo "$JIRA_KEYS" | grep -c . || true)

mkdir -p "$TMPDIR_WORK/jira"

if [ "$JIRA_AVAILABLE" = true ] && [ "$JIRA_KEY_COUNT" -gt 0 ]; then
  echo "Fetching $JIRA_KEY_COUNT JIRA tickets..." >&2

  fetch_jira_ticket() {
    local key="$1"
    local outfile="$TMPDIR_WORK/jira/${key}.json"

    if ! echo "$key" | grep -qE '^(HYPERFLEET|ROSAENG|AIHCM)-[0-9]+$'; then
      return
    fi

    if result=$(jira issue view "$key" --raw 2>/dev/null); then
      local tmpfile="${outfile}.tmp"
      printf '%s' "$result" | LC_ALL=C tr -d '\000-\010\013\014\016-\037' | jq -c '{
        key: .key,
        priority: (.fields.priority.name // "Undefined"),
        story_points: (.fields.customfield_10028 // null),
        status: (.fields.status.name // "Unknown"),
        type: (.fields.issuetype.name // "Unknown"),
        components: [(.fields.components // [])[] | .name],
        activity_type: ((.fields.customfield_10127 // {}).value // null),
        description: ((.fields.description // "") | tostring | .[0:500]),
        sprint: (
          [(.fields.customfield_10020 // [])[] | select(.state == "active")] |
          if length > 0 then {state: .[0].state, end_date: .[0].endDate} else null end
        ),
        issuelinks: [
          (.fields.issuelinks // [])[] |
          if .type.name == "Blocks" then
            if .inwardIssue then
              {type: "blocks", direction: "outward", key: .inwardIssue.key,
               priority: (.inwardIssue.fields.priority.name // "Unknown")}
            elif .outwardIssue then
              {type: "blocks", direction: "inward", key: .outwardIssue.key,
               priority: (.outwardIssue.fields.priority.name // "Unknown")}
            else empty end
          else empty end
        ],
        last_comments: [
          (.fields.comment.comments // []) | .[-5:][] |
          {author: .author.displayName, body: (.body | tostring | .[0:300]), created: .created}
        ]
      }' > "$tmpfile" 2>/dev/null
      if [ -s "$tmpfile" ] && jq empty "$tmpfile" 2>/dev/null; then
        mv "$tmpfile" "$outfile"
      else
        rm -f "$tmpfile"
      fi
    fi
  }

  for key in $JIRA_KEYS; do
    fetch_jira_ticket "$key" &
    # Rate-limit: batch of 10
    if [ "$(jobs -r | wc -l)" -ge 10 ]; then
      wait -n 2>/dev/null || wait
    fi
  done
  wait
fi

JIRA_FILES_WRITTEN=$(find "$TMPDIR_WORK/jira" -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
WARNINGS="[]"

if [ -n "$COMPONENT_FILTER" ] && [ "$JIRA_KEY_COUNT" -gt 0 ] && [ "$JIRA_FILES_WRITTEN" -eq 0 ]; then
  emit_error_json "--component filter active but all $JIRA_KEY_COUNT JIRA queries failed (auth expired or network issue?)"
  exit 0
fi

if [ "$JIRA_KEY_COUNT" -gt 0 ] && [ "$JIRA_FILES_WRITTEN" -eq 0 ]; then
  WARNINGS=$(echo "$WARNINGS" | jq '. + ["All JIRA queries failed — scores will lack JIRA context (priority, blocking, story points)"]')
elif [ "$JIRA_KEY_COUNT" -gt 0 ] && [ "$JIRA_FILES_WRITTEN" -lt "$JIRA_KEY_COUNT" ]; then
  WARNINGS=$(echo "$WARNINGS" | jq --arg n "$((JIRA_KEY_COUNT - JIRA_FILES_WRITTEN))" '. + ["\($n) JIRA ticket(s) could not be fetched — affected PRs will have reduced scoring accuracy"]')
fi

# --- Phase 3: Per-PR deep data (reviews, commits, CI, diff) ---

echo "Fetching per-PR details (reviews, CI, diffs)..." >&2

mkdir -p "$TMPDIR_WORK/pr_details"

fetch_pr_details() {
  local repo="$1"
  local number="$2"
  local outfile="$TMPDIR_WORK/pr_details/${repo}_${number}.json"
  local org="openshift-hyperfleet"

  local review_comments="[]"
  local issue_comments="[]"
  local latest_commit_date=""
  local commit_status='{}'
  local mergeable=""
  local diff_content=""

  review_comments=$(gh api --paginate "repos/$org/$repo/pulls/$number/comments" \
    --jq '[.[] | {author: .user.login, created: .created_at}]' 2>/dev/null) || review_comments="[]"

  issue_comments=$(gh api --paginate "repos/$org/$repo/issues/$number/comments" \
    --jq '[.[] | {author: .user.login, created: .created_at}]' 2>/dev/null) || issue_comments="[]"

  latest_commit_date=$(gh api --paginate "repos/$org/$repo/pulls/$number/commits" \
    --jq '.[-1].commit.committer.date' 2>/dev/null) || latest_commit_date=""

  local head_sha
  head_sha=$(gh api "repos/$org/$repo/pulls/$number" --jq '.head.sha' 2>/dev/null) || head_sha=""
  if [ -n "$head_sha" ]; then
    commit_status=$(gh api "repos/$org/$repo/commits/$head_sha/status" \
      --jq '{state: .state, statuses: [.statuses[] | {context: .context, state: .state}]}' 2>/dev/null) || commit_status='{}'
  fi

  mergeable=$(gh pr view "$number" --repo "$org/$repo" --json mergeable --jq '.mergeable' 2>/dev/null) || mergeable="UNKNOWN"

  diff_content=$(gh pr diff "$number" --repo "$org/$repo" 2>/dev/null) || diff_content=""
  local diff_lines
  diff_lines=$(echo "$diff_content" | wc -l | tr -d ' ')
  if [ "$diff_lines" -gt 3000 ]; then
    diff_content=$(gh pr diff "$number" --repo "$org/$repo" --stat 2>/dev/null || echo "")
    diff_content=$(printf '[LARGE PR: %s lines — showing stat only]\n%s' "$diff_lines" "$diff_content")
  fi

  jq -n \
    --arg repo "$repo" \
    --argjson number "$number" \
    --argjson review_comments "$review_comments" \
    --argjson issue_comments "$issue_comments" \
    --arg latest_commit_date "$latest_commit_date" \
    --argjson commit_status "$commit_status" \
    --arg mergeable "$mergeable" \
    --arg diff_content "$diff_content" \
    '{
      repo: $repo,
      number: $number,
      review_comments: $review_comments,
      issue_comments: $issue_comments,
      latest_commit_date: $latest_commit_date,
      commit_status: $commit_status,
      mergeable: $mergeable,
      diff_excerpt: $diff_content
    }' > "${outfile}.tmp" 2>/dev/null
  if [ -s "${outfile}.tmp" ] && jq empty "${outfile}.tmp" 2>/dev/null; then
    mv "${outfile}.tmp" "$outfile"
  else
    rm -f "${outfile}.tmp"
  fi
}

PR_LIST=$(jq -r '.[] | "\(.repo) \(.number)"' "$ALL_PRS")

BATCH_COUNT=0
while IFS=' ' read -r repo number; do
  [ -z "$repo" ] && continue
  fetch_pr_details "$repo" "$number" &
  BATCH_COUNT=$((BATCH_COUNT + 1))
  if [ "$BATCH_COUNT" -ge 5 ]; then
    wait
    BATCH_COUNT=0
  fi
done <<< "$PR_LIST"
wait

# --- Phase 4: Assemble final JSON ---

echo "Assembling results..." >&2

assemble_pr() {
  local pr_file="$1"
  local repo number title author_login

  repo=$(jq -r '.repo' "$pr_file")
  number=$(jq -r '.number' "$pr_file")
  title=$(jq -r '.title' "$pr_file")
  author_login=$(jq -r '.author.login' "$pr_file")

  local jira_keys
  jira_keys=$(echo "$title" | grep -oE '(HYPERFLEET|ROSAENG|AIHCM)-[0-9]+' || true)

  local jira_data_file="$TMPDIR_WORK/assembled/_jira_${repo}_${number}.json"
  echo '{}' > "$jira_data_file"
  if [ -n "$jira_keys" ]; then
    for key in $jira_keys; do
      local jira_file="$TMPDIR_WORK/jira/${key}.json"
      if [ -f "$jira_file" ]; then
        jq --arg k "$key" --slurpfile v "$jira_file" '. + {($k): $v[0]}' "$jira_data_file" > "${jira_data_file}.tmp" \
          && mv "${jira_data_file}.tmp" "$jira_data_file"
      fi
    done
  fi

  local details_file="$TMPDIR_WORK/pr_details/${repo}_${number}.json"
  if [ ! -f "$details_file" ]; then
    echo '{}' > "$details_file"
  fi

  local risk_label
  risk_label=$(jq -r '[.labels[]?.name // empty | select(startswith("risk/"))] | first // ""' "$pr_file")

  jq -c \
    --slurpfile details "$details_file" \
    --slurpfile jira_data "$jira_data_file" \
    --arg author_login "$author_login" \
    --arg risk_label "$risk_label" \
    --argjson jira_keys "$(echo "$jira_keys" | jq -R -s 'split("\n") | map(select(. != ""))')" \
    '{
      repo: .repo,
      number: .number,
      title: .title,
      author: $author_login,
      url: .url,
      created_at: .createdAt,
      updated_at: .updatedAt,
      additions: .additions,
      deletions: .deletions,
      changed_files: .changedFiles,
      is_draft: .isDraft,
      head_branch: .headRefName,
      labels: [.labels[]?.name // empty],
      risk_label: $risk_label,
      review_decision: .reviewDecision,
      latest_reviews: .latestReviews,
      status_check_rollup: .statusCheckRollup,
      mergeable: ($details[0].mergeable // "UNKNOWN"),
      latest_commit_date: ($details[0].latest_commit_date // ""),
      commit_status: ($details[0].commit_status // {}),
      review_comments: ($details[0].review_comments // []),
      issue_comments: ($details[0].issue_comments // []),
      diff_excerpt: ($details[0].diff_excerpt // ""),
      jira_keys: $jira_keys,
      jira_data: $jira_data[0]
    }' "$pr_file"
}

mkdir -p "$TMPDIR_WORK/assembled"

PR_INDEX=0
while IFS= read -r pr_line; do
  [ -z "$pr_line" ] && continue
  pr_input_file="$TMPDIR_WORK/assembled/input_${PR_INDEX}.json"
  printf '%s\n' "$pr_line" > "$pr_input_file"
  assembled=$(assemble_pr "$pr_input_file")
  if [ -n "$assembled" ]; then
    printf '%s\n' "$assembled" > "$TMPDIR_WORK/assembled/pr_${PR_INDEX}.json"
  fi
  PR_INDEX=$((PR_INDEX + 1))
done < <(jq -c '.[]' "$ALL_PRS")

RESULT_FILE="$TMPDIR_WORK/result_prs.json"
if compgen -G "$TMPDIR_WORK"/assembled/pr_*.json > /dev/null 2>&1; then
  jq -s '.' "$TMPDIR_WORK"/assembled/pr_*.json > "$RESULT_FILE"
else
  echo '[]' > "$RESULT_FILE"
fi

if [ -n "$COMPONENT_FILTER" ] && [ "$JIRA_AVAILABLE" = true ]; then
  jq --arg comp "$COMPONENT_FILTER" '[
    .[] | select(
      .jira_data as $jd |
      (.jira_keys | length > 0) and
      (.jira_keys | any(. as $k | $jd[$k].components // [] | any(. == $comp)))
    )
  ]' "$RESULT_FILE" > "${RESULT_FILE}.tmp" && mv "${RESULT_FILE}.tmp" "$RESULT_FILE"
  TOTAL_PRS=$(jq 'length' "$RESULT_FILE")
fi

REPOS_WITH_PRS=$(jq '[.[].repo] | unique | length' "$RESULT_FILE")

jq -n \
  --argjson jira "$JIRA_AVAILABLE" \
  --argjson queried "$REPO_COUNT" \
  --argjson errors "$REPO_ERRORS" \
  --argjson total "$TOTAL_PRS" \
  --argjson repos_with_prs "$REPOS_WITH_PRS" \
  --argjson warnings "$WARNINGS" \
  --slurpfile prs "$RESULT_FILE" \
  --arg component "$COMPONENT_FILTER" \
  '{
    metadata: {
      generated_at: (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
      jira_available: $jira,
      repos_queried: $queried,
      repos_with_prs: $repos_with_prs,
      repos_failed: $errors,
      total_prs: $total,
      component_filter: (if $component != "" then $component else null end),
      warnings: $warnings
    },
    prs: $prs[0]
  }'

echo "Done." >&2
