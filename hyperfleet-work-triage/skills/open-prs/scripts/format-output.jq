# format-output.jq — Deterministic formatter for /open-prs skill.
# Input: Final scored JSON (after LLM fills Factor 4) via stdin
# Args: --arg mode "compact|slack"
# Output: Formatted text to stdout.

def confidence_label:
  if . >= 85 then "Very High"
  elif . >= 70 then "High"
  elif . >= 50 then "Med"
  else "Low" end;

def confidence_label_full:
  if . >= 85 then "Very High"
  elif . >= 70 then "High"
  elif . >= 50 then "Medium"
  else "Low" end;

def confidence_emoji:
  if . >= 70 then "🟢"
  elif . >= 50 then "🟡"
  else "🔴" end;

def tier_emoji:
  if . == 1 then "🚨"
  elif . == 2 then "🟡"
  elif . == 3 then "🟢"
  else "🔵" end;

def header_emoji($prs):
  [$prs[].provisional_tier] | min // 3 | tier_emoji;

def age_format:
  if . < 0.042 then "\((. * 1440) | floor)m"
  elif . < 1 then "\((. * 24) | floor)h"
  else "\(. | floor)d" end;

def override_status:
  .override_info.reason // "Informational";

def review_status:
  if .scores.factor5.human_reviews == 0 then "No reviews"
  elif .scores.factor5.waiting_on_author then "Changes requested"
  elif .review_decision == "APPROVED" then "Approved"
  elif .scores.factor5.approvals > 0 then "\(.scores.factor5.approvals) approved"
  else "In review" end;

def compact_status:
  (.scores.factor3.age_days // 0) as $age |
  "\(review_status), \($age | age_format)";

def ci_status:
  if .scores.factor7.ci_failing then "Failing"
  elif .scores.factor7.score == 10 then "Passing"
  elif .scores.factor7.score == 6 then "Pending"
  else "None" end;

def jira_display:
  if (.jira_keys | length) == 0 then "No ticket"
  else .jira_keys[0] as $key | "[\($key)](https://redhat.atlassian.net/browse/\($key))" end;

def jira_display_with_priority:
  if (.jira_keys | length) == 0 then "No ticket"
  else
    .jira_keys[0] as $key |
    (.jira_data[$key].priority // null) as $pri |
    if $pri != null then "\($key) (\($pri))"
    else $key end
  end;

# ===== COMPACT MODE =====

def format_compact:
  .metadata as $meta |
  .scored_prs as $prs |
  ($prs | length) as $total |
  ([$prs[] | select(.provisional_tier == 1)]) as $t1 |
  ([$prs[] | select(.provisional_tier == 2)]) as $t2 |
  ([$prs[] | select(.provisional_tier == 3)]) as $t3 |
  ([$prs[] | select(.provisional_tier == 4)]) as $t4 |

  # Header
  "## Open PRs — openshift-hyperfleet\n\n" +
  "**Generated:** \($meta.generated_at // $meta.scored_at) | **\($total) PRs** across \($meta.repos_with_prs) repos | Sorted by priority score | `/open-prs --explain` for full analysis\n" +

  (if $meta.component_filter != null then "**Filter:** component=\($meta.component_filter)\n" else "" end) +
  (if ($meta.jira_available | not) then "**Note:** JIRA unavailable — GitHub-only mode, confidence reduced.\n" else "" end) +

  # Tier tables
  (if ($t1 | length) > 0 then
    "\n### Tier 1 — Immediate Attention (\($t1 | length) PRs)\n\n" +
    "| # | PR | JIRA | Status |\n|---|----|------|--------|\n" +
    ([range($t1 | length)] | map(
      . as $i | $t1[$i] |
      "| \($i + 1) | [\(.repo)#\(.number)](\(.url)) — \(.title) | \(jira_display) | \(compact_status) |"
    ) | join("\n")) + "\n"
  else "" end) +

  (if ($t2 | length) > 0 then
    "\n### Tier 2 — Should Review Soon (\($t2 | length) PRs)\n\n" +
    "| # | PR | JIRA | Status |\n|---|----|------|--------|\n" +
    (($t1 | length) as $offset |
    [range($t2 | length)] | map(
      . as $i | $t2[$i] |
      "| \($offset + $i + 1) | [\(.repo)#\(.number)](\(.url)) — \(.title) | \(jira_display) | \(compact_status) |"
    ) | join("\n")) + "\n"
  else "" end) +

  (if ($t3 | length) > 0 then
    "\n### Tier 3 — This Week (\($t3 | length) PRs)\n\n" +
    "| # | PR | JIRA | Status |\n|---|----|------|--------|\n" +
    (($t1 | length) + ($t2 | length)) as $offset |
    ([range($t3 | length)] | map(
      . as $i | $t3[$i] |
      "| \($offset + $i + 1) | [\(.repo)#\(.number)](\(.url)) — \(.title) | \(jira_display) | \(compact_status) |"
    ) | join("\n")) + "\n"
  else "" end) +

  (if ($t4 | length) > 0 then
    "\n### Tier 4 — Informational (\($t4 | length) PRs)\n\n" +
    "| PR | JIRA | Status |\n|----|------|--------|\n" +
    ([$t4[] |
      "| [\(.repo)#\(.number)](\(.url)) — \(.title) | \(jira_display) | \(override_status) |"
    ] | join("\n")) + "\n"
  else "" end) +

  # Recommendation
  "\n---\n\n" +
  (if ($t1 + $t2 + $t3 | length) > 0 then
    ($t1 + $t2 + $t3)[0] as $top |
    "**Start with:** [\($top.repo)#\($top.number)](\($top.url)) — \($top.override_info.reason // "highest priority score")"
  else
    "**No actionable PRs right now** — all open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback."
  end);

# ===== SLACK MODE =====

def format_slack:
  .metadata as $meta |
  .scored_prs as $prs |
  ($prs | length) as $total |
  ([$prs[] | select(.provisional_tier == 1)]) as $t1 |
  ([$prs[] | select(.provisional_tier == 2)]) as $t2 |
  ([$prs[] | select(.provisional_tier == 3)]) as $t3 |
  ([$prs[] | select(.provisional_tier == 4)]) as $t4 |

  # Tier visibility rules
  ($total > 10) as $hide_t3 |
  (($t1 | length) == 0 and ($t2 | length) == 0) as $fallback_to_t3 |

  # Show Tier 3 if total <= 10 OR if no T1/T2 PRs exist
  ($hide_t3 | not or $fallback_to_t3) as $show_t3 |

  # Header emoji based on highest tier with PRs
  (if ($t1 | length) > 0 then "🚨"
   elif ($t2 | length) > 0 then "🟡"
   else "🟢" end) as $hdr_emoji |

  # Zero PRs edge case
  if $total == 0 then
    "🟢 No open PRs found across the openshift-hyperfleet organization. 🎉"
  # All Tier 4 edge case
  elif ($t1 + $t2 + $t3 | length) == 0 then
    "🔴 Open PRs — openshift-hyperfleet\n_\($meta.generated_at // $meta.scored_at) | \($total) PRs across \($meta.repos_with_prs) repos_\n\nNo actionable PRs right now — all \($total) open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback."
  else
    # Main header
    "\($hdr_emoji) *Open PRs — openshift-hyperfleet*\n" +
    "_\($meta.generated_at // $meta.scored_at) | \($total) PRs across \($meta.repos_with_prs) repos_\n" +

    (if $meta.component_filter != null then "_Filter: component=\($meta.component_filter)_\n" else "" end) +
    (if ($meta.jira_available | not) then "_⚠️ JIRA unavailable — GitHub-only mode, confidence reduced_\n" else "" end) +

    # Tier 1
    (if ($t1 | length) > 0 then
      "\n🚨 *Tier 1 — Immediate Attention (\($t1 | length) PRs)*\n\n" +
      ([$t1[] |
        "<\(.url)|`\(.repo) #\(.number)`> : \(.title)" +
        (if (.jira_keys | length) > 0 then
          " | <https://redhat.atlassian.net/browse/\(.jira_keys[0])|\(.jira_keys[0])>"
        else "" end) +
        " — _\(compact_status)_"
      ] | map("• " + .) | join("\n")) + "\n"
    else "" end) +

    # Tier 2
    (if ($t2 | length) > 0 then
      "\n🟡 *Tier 2 — Should Review Soon (\($t2 | length) PRs)*\n\n" +
      ([$t2[] |
        "<\(.url)|`\(.repo) #\(.number)`> : \(.title)" +
        (if (.jira_keys | length) > 0 then
          " | <https://redhat.atlassian.net/browse/\(.jira_keys[0])|\(.jira_keys[0])>"
        else "" end) +
        " — _\(compact_status)_"
      ] | map("• " + .) | join("\n")) + "\n"
    else "" end) +

    # Tier 3 (conditional)
    (if $show_t3 and ($t3 | length) > 0 then
      "\n🟢 *Tier 3 — This Week (\($t3 | length) PRs)*\n\n" +
      ([$t3[] |
        "<\(.url)|`\(.repo) #\(.number)`> : \(.title)" +
        (if (.jira_keys | length) > 0 then
          " | <https://redhat.atlassian.net/browse/\(.jira_keys[0])|\(.jira_keys[0])>"
        else "" end) +
        " — _\(compact_status)_"
      ] | map("• " + .) | join("\n")) + "\n"
    else "" end) +

    # Summary line
    (
      (if $hide_t3 and ($fallback_to_t3 | not) then ($t3 | length) else 0 end) as $hidden_t3 |
      ($t4 | length) as $hidden_t4 |
      ($hidden_t3 + $hidden_t4) as $total_hidden |
      if $total_hidden > 0 then
        "\n_\($total_hidden) more PRs in Tier 3-4 (not shown). Run `/open-prs` for full list._"
      else "" end
    )
  end;

# ===== MAIN =====

if $mode == "slack" then
  format_slack
elif $mode == "compact" then
  format_compact
else
  "Error: unknown mode '\($mode)'. Use --arg mode compact or --arg mode slack" | halt_error(1)
end
