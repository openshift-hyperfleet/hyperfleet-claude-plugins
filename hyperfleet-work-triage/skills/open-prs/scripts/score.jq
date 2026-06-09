# score.jq — Deterministic scoring engine for /open-prs skill.
# Input: JSON from collect-data.sh via stdin
# Args: --arg now "ISO8601 timestamp"
# Output: Enriched JSON with scores, tiers, overrides, sorted by priority.

def parse_iso8601:
  # Convert ISO8601 to epoch seconds (handles Z and +00:00 suffixes)
  gsub("[TZ]"; " ") | gsub("\\+00:00$"; "") | split(".")[0] |
  strptime("%Y-%m-%d %H:%M:%S") | mktime;

def safe_parse_iso8601:
  if . == null or . == "" then 0
  else (parse_iso8601 // 0) end;

def day_of_week:
  # 0=Sunday, 1=Monday, ..., 6=Saturday (from epoch)
  (. / 86400 + 4) % 7 | floor;

def business_days_between(from_epoch; to_epoch):
  # Count business days (Mon-Fri) between two epoch timestamps
  if to_epoch <= from_epoch then 0
  else
    ((to_epoch - from_epoch) / 86400) as $total_days |
    ($total_days | floor) as $days |
    [range($days)] | map(
      ((from_epoch + . * 86400) | day_of_week) as $dow |
      if $dow == 0 or $dow == 6 then 0 else 1 end
    ) | add // 0
  end;

def known_bots:
  ["coderabbitai", "openshift-ci[bot]", "openshift-ci", "dependabot[bot]",
   "renovate[bot]", "github-actions[bot]"];

# --- Factor 1: JIRA Priority & Urgency (20%) ---
def score_factor1($now_epoch):
  .jira_data as $jd |
  .jira_keys as $keys |
  .metadata_jira_available as $jira_avail |

  if ($jira_avail | not) then
    {score: 5, detail: "JIRA unavailable, default neutral score"}
  elif ($keys | length) == 0 then
    {score: 0, detail: "No JIRA ticket linked"}
  else
    # Use highest-priority ticket
    [$keys[] | $jd[.] // null | select(. != null)] |
    if length == 0 then {score: 0, detail: "No JIRA data fetched"}
    else
      (sort_by(
        if .priority == "Blocker" then 0
        elif .priority == "Critical" then 1
        elif .priority == "Major" then 2
        elif .priority == "High" then 2
        elif .priority == "Normal" then 3
        elif .priority == "Minor" then 4
        elif .priority == "Low" then 4
        else 5 end
      ) | first) as $ticket |

      # Base score from priority
      (if $ticket.priority == "Blocker" then 9
       elif $ticket.priority == "Critical" then 8
       elif $ticket.priority == "Major" or $ticket.priority == "High" then 6
       elif $ticket.priority == "Normal" then
         if $ticket.sprint != null then 5 else 4 end
       elif $ticket.priority == "Minor" or $ticket.priority == "Low" then 3
       else 2 end) as $base |

      # Activity type boost
      (if $ticket.activity_type == "Security & Compliance" then 8
       elif $ticket.activity_type == "Incidents & Support" then 8
       else $base end) as $base_with_activity |
      (if $base_with_activity > $base then $base_with_activity else $base end) as $effective_base |

      # Sprint proximity boost
      (if $ticket.sprint != null and $ticket.sprint.end_date != null then
        ($ticket.sprint.end_date | safe_parse_iso8601) as $end_epoch |
        if $end_epoch <= 0 then 0
        else
          business_days_between($now_epoch; $end_epoch) as $bdays |
          if $bdays <= 0 then 3
          elif $bdays <= 3 then 2
          elif $bdays <= 7 then 1
          else 0 end
        end
       else 0 end) as $boost |

      ([($effective_base + $boost), 10] | min) as $final |

      {score: $final,
       detail: "\($ticket.priority) priority\(if $ticket.sprint != null then ", in current sprint" else "" end)\(if $boost > 0 then ", sprint boost +\($boost)" else "" end)"}
    end
  end;

# --- Factor 2: Blocking Impact (18%, partial — LLM refines from comments) ---
def score_factor2:
  .jira_data as $jd |
  .jira_keys as $keys |
  .metadata_jira_available as $jira_avail |
  .labels as $labels |

  if ($jira_avail | not) then
    # Check labels only
    (if ($labels | any(. == "blocking" or . == "prerequisite" or . == "release-blocker")) then 4
     else 2 end) as $score |
    {score: $score, detail: "JIRA unavailable, label-based only", needs_llm: true}
  else
    # Count explicit blocking links (outward = this ticket blocks others)
    ([$keys[] | $jd[.] // null | select(. != null) |
      .issuelinks[] | select(.direction == "outward")] | length) as $blocks_count |

    # Check priorities of blocked tickets
    ([$keys[] | $jd[.] // null | select(. != null) |
      .issuelinks[] | select(.direction == "outward") |
      select(.priority == "Blocker" or .priority == "Critical" or .priority == "High" or .priority == "Major")
    ] | length) as $high_priority_blocks |

    # Check PR labels for blocking signals
    ($labels | any(. == "blocking" or . == "prerequisite" or . == "release-blocker")) as $has_blocking_label |

    (if $blocks_count >= 3 then 10
     elif $blocks_count == 2 and $high_priority_blocks >= 1 then 9
     elif $blocks_count >= 1 and $high_priority_blocks >= 1 then 8
     elif $blocks_count >= 1 then 7
     elif $has_blocking_label then 4
     else 2 end) as $score |

    {score: $score,
     detail: "\($blocks_count) blocking link(s)\(if $high_priority_blocks > 0 then ", \($high_priority_blocks) high-priority" else "" end)",
     needs_llm: true,
     blocks_count: $blocks_count}
  end;

# --- Factor 3: Staleness & Age (16%) ---
def score_factor3($now_epoch):
  (.created_at | safe_parse_iso8601) as $created |
  (($now_epoch - $created) / 86400) as $age_days |
  (.latest_reviews | length) as $review_count |

  # Filter out bot reviews
  ([.latest_reviews[]? | select(.author.login as $a | known_bots | any(. == $a) | not)] | length) as $human_reviews |

  (if $age_days > 14 and $human_reviews == 0 then 10
   elif $age_days > 14 then 9
   elif $age_days > 7 and $human_reviews == 0 then 9
   elif $age_days > 7 then 8
   elif $age_days > 5 then 7
   elif $age_days > 3 then 6
   elif $age_days > 2 then 5
   elif $age_days > 1 then 4
   elif $age_days > 0.5 then 3
   elif $age_days > 0.167 then 2
   elif $age_days > 0.042 then 1
   else 0 end) as $score |

  {score: $score,
   detail: "\($age_days | . * 10 | floor | . / 10)d old\(if $human_reviews == 0 then ", no reviews" else ", \($human_reviews) review(s)" end)",
   age_days: ($age_days | . * 10 | floor | . / 10)};

# --- Factor 4: Risk & Content Analysis (14%) — deterministic floor from risk label, LLM fills rest ---
def score_factor4:
  .risk_label as $rl |
  .labels as $labels |
  .head_branch as $branch |
  .jira_data as $jd |
  .jira_keys as $keys |

  # Deterministic floor from Prow risk label (HYPERFLEET-1168)
  (if $rl == "risk/high" then 8
   elif $rl == "risk/medium" then 6
   else null end) as $label_floor |

  # Additional deterministic signals from labels and branch name
  (if ($labels | any(. == "security" or . == "hotfix")) then 10
   elif ($branch | test("^(hotfix|security)/"; "i") // false) then 9
   elif ($labels | any(. == "bug")) or ($branch | test("^(bugfix|fix)/"; "i") // false) then 7
   elif ($labels | any(. == "feature" or . == "feat")) then 5
   elif ($labels | any(. == "docs" or . == "documentation")) then 2
   elif ($labels | any(. == "refactor" or . == "chore")) then 3
   else null end) as $label_signal |

  # JIRA type signal
  ([$keys[] | $jd[.] // null | select(. != null)] | first // null) as $ticket |
  (if $ticket != null then
    if $ticket.activity_type == "Security & Compliance" then 10
    elif $ticket.activity_type == "Incidents & Support" then 9
    elif $ticket.type == "Bug" then 7
    elif $ticket.type == "Story" or $ticket.type == "Feature" then 5
    elif $ticket.type == "Spike" then 0
    else null end
   else null end) as $jira_signal |

  # Take max of deterministic signals as the floor
  ([$label_floor, $label_signal, $jira_signal] | map(select(. != null)) | max // null) as $det_floor |

  {score: $det_floor,
   needs_llm: true,
   label_floor: $label_floor,
   label_signal: $label_signal,
   jira_signal: $jira_signal,
   risk_label: ($rl // null),
   detail: (
     if $det_floor != null then
       "Deterministic floor: \($det_floor)\(if $label_floor != null then " (risk label: \($rl))" else "" end)"
     else
       "No deterministic signals, LLM classification needed"
     end
   )};

# --- Factor 5: Review Progress (12%) ---
def score_factor5($now_epoch):
  .review_decision as $rd |
  .latest_reviews as $reviews |
  .review_comments as $rev_comments |
  .issue_comments as $iss_comments |
  .latest_commit_date as $lcd |
  .author as $author |
  (.created_at | safe_parse_iso8601) as $created |
  (($now_epoch - $created) / 86400) as $age_days |

  # Filter out bots from reviews
  ([($reviews // [])[] | select(.author.login as $a | known_bots | any(. == $a) | not)] | length) as $human_reviews |

  # All comments excluding bots and author
  ([($rev_comments // [])[], ($iss_comments // [])[] |
    select(.author != $author and (.author as $a | known_bots | any(. == $a) | not))
  ]) as $reviewer_comments |

  # Author's comments
  ([($rev_comments // [])[], ($iss_comments // [])[] |
    select(.author == $author)
  ]) as $author_comments |

  # Latest reviewer comment timestamp
  ([$reviewer_comments[] | .created | safe_parse_iso8601] | max // 0) as $latest_reviewer |

  # Latest author activity (commit or comment)
  ($lcd | safe_parse_iso8601) as $commit_epoch |
  ([$author_comments[] | .created | safe_parse_iso8601] | max // 0) as $author_comment_epoch |
  ([$commit_epoch, $author_comment_epoch] | max) as $latest_author_activity |

  # Detect "waiting on author"
  # Formal: CHANGES_REQUESTED and no newer commits
  ([$reviews[] | select(.state == "CHANGES_REQUESTED") | .submittedAt | safe_parse_iso8601] | max // 0) as $changes_req_time |
  ($changes_req_time > 0 and $commit_epoch < $changes_req_time) as $formal_waiting |

  # Informal: reviewer commented after author's last activity
  ($latest_reviewer > 0 and $latest_author_activity > 0 and $latest_reviewer > $latest_author_activity) as $informal_waiting |
  ($latest_reviewer > 0 and $latest_author_activity == 0) as $informal_waiting_no_response |

  ($formal_waiting or $informal_waiting or $informal_waiting_no_response) as $waiting_on_author |

  # Approvals
  ([$reviews[] | select(.state == "APPROVED")] | length) as $approvals |

  (if $human_reviews == 0 and $age_days > 2 then 10
   elif $human_reviews == 0 and $age_days > 1 then 9
   elif $human_reviews == 0 then 8
   elif $waiting_on_author then 1
   elif $rd == "APPROVED" then 0
   elif $approvals > 0 then 5
   elif $rd == "CHANGES_REQUESTED" and $commit_epoch > $changes_req_time then 6
   elif ($reviewer_comments | length) > 0 and $latest_author_activity > $latest_reviewer then 3
   elif ($reviewer_comments | length) > 0 then 4
   else 7 end) as $score |

  {score: $score,
   waiting_on_author: $waiting_on_author,
   formal_waiting: $formal_waiting,
   informal_waiting: ($informal_waiting or $informal_waiting_no_response),
   approvals: $approvals,
   human_reviews: $human_reviews,
   detail: (
     if $human_reviews == 0 then "Zero engagement, \($age_days | floor)d old"
     elif $waiting_on_author then "Waiting on author\(if $formal_waiting then " (changes requested)" else " (reviewer comment unanswered)" end)"
     elif $rd == "APPROVED" then "Approved, ready to merge"
     elif $approvals > 0 then "\($approvals) approval(s), needs more"
     else "\($human_reviews) review(s)" end
   )};

# --- Factor 6: PR Size & Complexity (8%) ---
def score_factor6:
  (.additions + .deletions) as $total |
  .changed_files as $files |

  (if $total <= 10 and $files <= 2 then 10
   elif $total <= 50 and $files <= 3 then 9
   elif $total <= 100 and $files <= 5 then 8
   elif $total <= 200 and $files <= 8 then 7
   elif $total <= 300 and $files <= 10 then 6
   elif $total <= 500 and $files <= 15 then 5
   elif $total <= 800 and $files <= 20 then 4
   elif $total <= 1200 then 3
   elif $total <= 2000 then 2
   elif $total <= 3000 then 1
   else 0 end) as $score |

  {score: $score,
   total_lines: $total,
   detail: "+\(.additions)/-\(.deletions) (\($files) files)"};

# --- Factor 7: CI/Check Status (7%) ---
def score_factor7:
  .status_check_rollup as $rollup |
  .commit_status as $cs |
  .labels as $labels |

  # Check for needs-ok-to-test label
  ($labels | any(. == "needs-ok-to-test")) as $needs_ok_to_test |

  # Merge statusCheckRollup and commit status
  # statusCheckRollup entries: {name, status, conclusion}
  # commit status entries: {context, state}

  # Normalize rollup entries
  ([($rollup // [])[] |
    select(.name != null and .name != "tide") |
    select(.status != null or .conclusion != null) |
    {name: .name,
     state: (if .conclusion == "SUCCESS" or .conclusion == "success" then "success"
             elif .conclusion == "FAILURE" or .conclusion == "failure" then "failure"
             elif .status == "COMPLETED" and .conclusion == null then null
             elif .status == "IN_PROGRESS" or .status == "QUEUED" or .status == "PENDING" then "pending"
             else .conclusion // .status // null end)}
  ] | map(select(.state != null))) as $rollup_checks |

  # Normalize commit status entries
  ([($cs.statuses // [])[] |
    select(.context != "tide") |
    {name: .context, state: .state}
  ]) as $status_checks |

  ($rollup_checks + $status_checks) as $all_checks |

  # Filter out all-null
  ([$all_checks[] | select(.state != null)] | length) as $total_checks |

  ([$all_checks[] | select(.state == "failure" or .state == "FAILURE")] | length) as $failing |
  ([$all_checks[] | select(.state == "success" or .state == "SUCCESS")] | length) as $passing |
  ([$all_checks[] | select(.state == "pending" or .state == "PENDING")] | length) as $pending |

  (if $needs_ok_to_test then
    {score: 6, ci_failing: false, detail: "Needs ok-to-test approval (process gate)"}
   elif $total_checks == 0 then
    {score: 6, ci_failing: false, detail: "No checks configured"}
   elif $failing > 0 then
    {score: 0, ci_failing: true, detail: "\($failing) check(s) failing"}
   elif $passing == $total_checks then
    {score: 10, ci_failing: false, detail: "All \($passing) checks passing"}
   else
    {score: 6, ci_failing: false, detail: "\($passing) passing, \($pending) pending"}
   end);

# --- Factor 8: Story Points & Impact (5%) ---
def score_factor8:
  .jira_data as $jd |
  .jira_keys as $keys |
  .metadata_jira_available as $jira_avail |

  if ($jira_avail | not) then
    {score: 2, detail: "JIRA unavailable, default"}
  elif ($keys | length) == 0 then
    {score: 0, detail: "No JIRA ticket"}
  else
    ([$keys[] | $jd[.] // null | select(. != null)] | first // null) as $ticket |
    if $ticket == null then {score: 1, detail: "JIRA data not fetched"}
    else
      ($ticket.story_points // null) as $sp |
      (if $sp == null then {score: 1, detail: "Story points not set"}
       elif $sp >= 13 then {score: 10, detail: "\($sp) story points"}
       elif $sp >= 8 then {score: 8, detail: "\($sp) story points"}
       elif $sp >= 5 then {score: 6, detail: "\($sp) story points"}
       elif $sp >= 3 then {score: 4, detail: "\($sp) story points"}
       elif $sp >= 1 then {score: 3, detail: "\($sp) story point(s)"}
       else {score: 2, detail: "0 story points"} end)
    end
  end;

# --- Data Completeness (for confidence) ---
def data_completeness:
  . as $pr |
  (25) +  # GitHub PR metadata always present
  (if $pr.metadata_jira_available and ($pr.jira_keys | length > 0) and
      ($pr.jira_keys | any(. as $k | $pr.jira_data[$k] != null))
   then 25 else 0 end) +
  (if ($pr.status_check_rollup // [] | length) > 0 or
      ($pr.commit_status.statuses // [] | length) > 0
   then 15 else 0 end) +
  (if ($pr.diff_excerpt // "") != "" then 15 else 0 end) +
  (if $pr.metadata_jira_available and
      ($pr.jira_keys | any(. as $k | ($pr.jira_data[$k].last_comments // []) | length > 0))
   then 10 else 0 end) +
  (if $pr.metadata_jira_available then 10 else 0 end);

# --- Detect related PR groups ---
def find_related_prs:
  [.[] | . as $pr | .jira_keys[] | {jira_key: ., repo: $pr.repo, number: $pr.number}] |
  group_by(.jira_key) |
  map(select(length > 1)) |
  [.[] | {
    jira_key: .[0].jira_key,
    prs: [.[] | {repo: .repo, number: .number}] | unique_by(.repo + "/" + (.number | tostring))
  }];

# --- Generate flags ---
def generate_flags($now_epoch):
  . as $pr |
  (($now_epoch - ($pr.created_at | safe_parse_iso8601)) / 86400) as $age_days |
  [
    (if ($pr.additions + $pr.deletions) > 500 then "large_pr" else empty end),
    (if $age_days > 3 and ($pr.scores.factor5.human_reviews // 0) == 0 then "sla_breach" else empty end),
    (if ($pr.jira_keys | length) == 0 then "no_jira_ticket" else empty end),
    (if $age_days > 7 then "stale" else empty end),
    (if ($pr.labels | any(. == "needs-rebase")) then "needs_rebase" else empty end),
    (if ($pr.scores.factor8.score // 0) >= 10 then "high_story_points" else empty end)
  ];

# --- Override rules ---
def apply_overrides:
  .scores.factor7.ci_failing as $ci_fail |
  .scores.factor5.waiting_on_author as $waiting |
  .mergeable as $mergeable |
  .is_draft as $draft |
  .jira_keys as $keys |
  .jira_data as $jd |
  .metadata_jira_available as $jira_avail |

  # Highest JIRA priority
  ([$keys[] | $jd[.] // null | select(. != null) | .priority] |
   map(if . == "Blocker" then 0 elif . == "Critical" then 1 else 10 end) |
   min // 10) as $highest_priority_rank |

  if $ci_fail then
    {override: "tier4", reason: "CI failing"}
  elif $waiting then
    {override: "tier4", reason: "Waiting on author"}
  elif $mergeable == "CONFLICTING" then
    {override: "tier4", reason: "Merge conflicts"}
  elif $draft then
    {override: "tier4", reason: "Draft"}
  elif $highest_priority_rank <= 1 then
    {override: "tier1", reason: "JIRA Blocker/Critical"}
  elif ($keys | length) == 0 then
    {override: "cap_tier3", reason: "No JIRA ticket"}
  else
    {override: null, reason: null}
  end;

# --- Weighted score calculation ---
def compute_weighted_score:
  .scores as $s |
  # Weights: F1=20%, F2=18%, F3=16%, F4=14%, F5=12%, F6=8%, F7=7%, F8=5%
  (($s.factor1.score * 20) +
   ($s.factor2.score * 18) +
   ($s.factor3.score * 16) +
   (($s.factor4.score // 5) * 14) +  # Default to 5 (neutral) if LLM hasn't scored yet
   ($s.factor5.score * 12) +
   ($s.factor6.score * 8) +
   ($s.factor7.score * 7) +
   ($s.factor8.score * 5)) / 10;

def compute_score_range:
  .scores as $s |
  # Min: Factor 4 = 0 (or label floor if exists)
  (($s.factor4.score // 0) as $f4_min |
   (($s.factor1.score * 20) + ($s.factor2.score * 18) + ($s.factor3.score * 16) +
    ($f4_min * 14) + ($s.factor5.score * 12) + ($s.factor6.score * 8) +
    ($s.factor7.score * 7) + ($s.factor8.score * 5)) / 10) as $min |
  # Max: Factor 4 = 10
  ((($s.factor1.score * 20) + ($s.factor2.score * 18) + ($s.factor3.score * 16) +
    (10 * 14) + ($s.factor5.score * 12) + ($s.factor6.score * 8) +
    ($s.factor7.score * 7) + ($s.factor8.score * 5)) / 10) as $max |
  [$min, $max];

def assign_tier:
  .deterministic_score as $score |
  .override_info.override as $override |

  if $override == "tier4" then 4
  elif $override == "tier1" then 1
  elif $override == "cap_tier3" then
    (if $score >= 75 then 3
     elif $score >= 50 then 3
     elif $score >= 25 then 3
     else 4 end)
  elif $score >= 75 then 1
  elif $score >= 50 then 2
  elif $score >= 25 then 3
  else 4 end;

# ===== MAIN =====

($now | safe_parse_iso8601) as $now_epoch |

.metadata as $meta |
.prs as $prs |

# Detect related PR groups
($prs | find_related_prs) as $related_groups |

# Score each PR
[.prs[] |
  # Inject metadata availability flag into each PR for factor functions
  . + {metadata_jira_available: $meta.jira_available} |

  # Compute all factors
  . + {scores: {
    factor1: score_factor1($now_epoch),
    factor2: score_factor2,
    factor3: score_factor3($now_epoch),
    factor4: score_factor4,
    factor5: score_factor5($now_epoch),
    factor6: score_factor6,
    factor7: score_factor7,
    factor8: score_factor8
  }} |

  # Apply overrides
  . + {override_info: apply_overrides} |

  # Compute scores
  . + {deterministic_score: compute_weighted_score} |
  . + {score_range: compute_score_range} |

  # Assign tier
  . + {provisional_tier: assign_tier} |

  # Data completeness
  . + {data_completeness: data_completeness} |

  # Flags
  . + {flags: generate_flags($now_epoch)} |

  # Related PRs
  . as $current_pr |
  . + {related_prs: (
    [$related_groups[] |
     select(.prs | any(.repo == $current_pr.repo and .number == $current_pr.number)) |
     .prs[] | select(.repo != $current_pr.repo or .number != $current_pr.number) |
     "\(.repo)#\(.number)"
    ] // []
  )} |

  # Remove injected helper field
  del(.metadata_jira_available)

] |

# Sort: by deterministic_score desc, then data_completeness desc, then age desc, then size asc
sort_by([
  (-.deterministic_score),
  (-.data_completeness),
  (-(.scores.factor3.age_days // 0)),
  (.scores.factor6.total_lines // 0)
]) |

# Build final output
{
  metadata: ($meta + {
    scoring_version: "1.0.0",
    scored_at: ($now)
  }),
  related_pr_groups: $related_groups,
  scored_prs: .
}
