# format-output.jq — Deterministic formatter for /open-prs skill.
# Input: Final scored JSON (after LLM fills Factor 4) via stdin
# Args: --arg mode "compact|slack"
# Output: Formatted text to stdout.
#
# Both modes group PRs by area (Prow `area/*` label). A PR with several area
# labels is listed under its first label with the others shown inline; PRs with
# no area label are listed under "No area", always last. Tier still decides
# which PRs are shown (Slack hides Tier 4 and, above 10 PRs, Tier 3) and is
# shown per PR as an emoji.

def escape_md:
  gsub("[|]"; "\\|") | gsub("\\["; "\\[") | gsub("\\]"; "\\]");

def escape_slack:
  gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;");

# HyperFleet org project board — linked from the Slack digest header.
def board_url: "https://github.com/orgs/openshift-hyperfleet/projects/1/views/1";

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

def effective_tier:
  if .override_info.override == "tier4" then 4
  elif .override_info.override == "tier1" then 1
  elif .override_info.override == "cap_tier3" then
    (if .provisional_tier < 3 then 3 else .provisional_tier end)
  else .provisional_tier end;

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

def title_with_jira_link:
  if (.jira_keys | length) == 0 then (.title | escape_md)
  else
    .jira_keys[0] as $key |
    (.title | escape_md) | gsub("(?<pre>^|\\b)\($key)(?<post>\\b)"; "\(.pre)[\($key)](https://redhat.atlassian.net/browse/\($key))\(.post)")
  end;

def title_with_jira_link_slack:
  if (.jira_keys | length) == 0 then (.title | escape_slack)
  else
    .jira_keys[0] as $key |
    (.title | escape_slack) | gsub("(?<pre>^|\\b)\($key)(?<post>\\b)"; "\(.pre)<https://redhat.atlassian.net/browse/\($key)|\($key)>\(.post)")
  end;

# ===== AREA AND REVIEWER HELPERS =====

def area_name:
  (.area.primary // "No area") as $p |
  if $p == "No area" then "No area" else "area/\($p)" end;

def area_heading:
  if .area == "No area" then "No area" else "area/\(.area)" end;

# Pending review requests with business days since the latest request.
def reviewers_text:
  (.review_request // {}) as $rr |
  if (($rr.reviewers // []) | length) == 0 then "none requested"
  else "\($rr.reviewers | map("@" + .) | join(", ")) (\($rr.business_days_waiting // 0)bd)" end;

# Short flag list: reviewer overdue (>1 business day on a requested reviewer),
# SLA breach (>3 days with no human review), stale (>7 days).
def pr_flag_list:
  (.flags // []) as $f |
  [ (if (.review_request.overdue // false) then "overdue" else empty end),
    (if ($f | any(. == "sla_breach")) then "SLA" else empty end),
    (if ($f | any(. == "stale")) then "stale" else empty end) ];

def flags_text:
  pr_flag_list | if length == 0 then "" else " ⚠️ \(join(", "))" end;

def other_areas_md:
  (.area.others // []) | if length == 0 then "" else " (+\(map("area/" + .) | join(", ") | escape_md))" end;

def other_areas_slack:
  (.area.others // []) | if length == 0 then "" else " · _+\(map("area/" + .) | join(", ") | escape_slack)_" end;

# Group PRs by primary area. Input order (score descending) is kept inside each
# group. Areas are ordered by best tier, then highest score; "No area" is last.
def group_by_area:
  group_by(.area.primary // "No area") |
  map({
    area: (.[0].area.primary // "No area"),
    prs: .,
    best_tier: ([.[].effective_tier] | min),
    top_score: ([.[].deterministic_score // 0] | max)
  }) |
  sort_by([(if .area == "No area" then 1 else 0 end), .best_tier, (-.top_score), .area]);

# Rank map: position of each Tier 1-3 PR in the score-sorted list.
def rank_map:
  [.[] | select(.effective_tier <= 3)] | to_entries |
  map({key: "\(.value.repo)#\(.value.number)", value: (.key + 1)}) | from_entries;

def pr_count_label:
  if . == 1 then "1 PR" else "\(.) PRs" end;

# ===== COMPACT MODE =====

def format_compact:
  .metadata as $meta |
  (.scored_prs | map(. + {effective_tier: effective_tier})) as $prs |
  ($prs | length) as $total |

  if $total == 0 then
    "No open PRs found across the openshift-hyperfleet organization. Nothing to review!"
  else

  ([$prs[] | select(.effective_tier <= 3)]) as $actionable |
  ($prs | rank_map) as $ranks |
  ($prs | group_by_area) as $groups |

  # Header
  "## Open PRs — openshift-hyperfleet\n\n" +
  "**Generated:** \($meta.generated_at // $meta.scored_at) | **\($total) PRs** across \($meta.repos_with_prs) repos | Grouped by area, ranked by priority score | `/open-prs --explain` for full analysis\n" +

  (if $meta.component_filter != null then "**Filter:** component=\($meta.component_filter)\n" else "" end) +
  (if ($meta.jira_available | not) then "**Note:** JIRA unavailable — GitHub-only mode, confidence reduced.\n" else "" end) +

  # Area tables
  ([$groups[] |
    "\n### \(area_heading | escape_md) (\(.prs | length | pr_count_label))\n\n" +
    "| # | PR | Tier | Status | Reviewers |\n|---|----|------|--------|-----------|\n" +
    ([.prs[] |
      ($ranks["\(.repo)#\(.number)"] // "-") as $rank |
      (if .effective_tier == 4 then override_status else compact_status + flags_text end) as $status |
      "| \($rank) | [\(.repo)#\(.number)](\(.url)) — \(title_with_jira_link)\(other_areas_md) | \(.effective_tier | tier_emoji) T\(.effective_tier) | \($status) | \(reviewers_text) |"
    ] | join("\n")) + "\n"
  ] | join("")) +

  # Recommendation
  "\n---\n\n" +
  (if ($actionable | length) > 0 then
    $actionable[0] as $top |
    "**Start with:** [\($top.repo)#\($top.number)](\($top.url)) — \($top.override_info.reason // "highest priority score")"
  else
    "**No actionable PRs right now** — all open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback."
  end)

  end;

# ===== SLACK MODE =====

def format_slack:
  .metadata as $meta |
  (.scored_prs | map(. + {effective_tier: effective_tier})) as $prs |
  ($prs | length) as $total |
  ([$prs[] | select(.effective_tier == 1)]) as $t1 |
  ([$prs[] | select(.effective_tier == 2)]) as $t2 |
  ([$prs[] | select(.effective_tier == 3)]) as $t3 |
  ([$prs[] | select(.effective_tier == 4)]) as $t4 |

  # Tier visibility rules
  ($total > 10) as $hide_t3 |
  (($t1 | length) == 0 and ($t2 | length) == 0) as $fallback_to_t3 |

  # Show Tier 3 if total <= 10 OR if no T1/T2 PRs exist
  ($hide_t3 | not or $fallback_to_t3) as $show_t3 |

  # PRs that make it into the message, grouped by area
  ([$prs[] | select(.effective_tier <= 2 or ($show_t3 and .effective_tier == 3))]) as $shown |
  ($shown | group_by_area) as $groups |

  # Header emoji based on highest tier with PRs
  (if ($t1 | length) > 0 then "🚨"
   elif ($t2 | length) > 0 then "🟡"
   else "🟢" end) as $hdr_emoji |

  # Zero PRs edge case
  if $total == 0 then
    "🟢 No open PRs found across the openshift-hyperfleet organization. 🎉"
  # All Tier 4 edge case
  elif ($t1 + $t2 + $t3 | length) == 0 then
    "🟢 Open PRs — openshift-hyperfleet\n_\($meta.generated_at // $meta.scored_at) | \($total) PRs across \($meta.repos_with_prs) repos_\n📋 <\(board_url)|PRs Dashboard>\n\nNo actionable PRs right now — all \($total) open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback."
  else
    # Main header
    "\($hdr_emoji) *Open PRs — openshift-hyperfleet*\n" +
    "_\($meta.generated_at // $meta.scored_at) | \($total) PRs across \($meta.repos_with_prs) repos | grouped by area_\n" +
    "📋 <\(board_url)|PRs Dashboard>\n" +

    (if $meta.component_filter != null then "_Filter: component=\($meta.component_filter)_\n" else "" end) +
    (if ($meta.jira_available | not) then "_⚠️ JIRA unavailable — GitHub-only mode, confidence reduced_\n" else "" end) +

    # One section per area, each PR a single bullet with its tier emoji
    ([$groups[] |
      "\n\(.best_tier | tier_emoji) *\(area_heading | escape_slack) (\(.prs | length | pr_count_label))*\n\n" +
      ([.prs[] |
        "• \(.effective_tier | tier_emoji) <\(.url)|`\(.repo) #\(.number)`> : \(title_with_jira_link_slack) — _\(compact_status)_ · 👀 \(reviewers_text)\(flags_text)\(other_areas_slack)"
      ] | join("\n")) + "\n"
    ] | join("")) +

    # Summary line
    (
      (if $hide_t3 and ($fallback_to_t3 | not) then ($t3 | length) else 0 end) as $hidden_t3 |
      ($t4 | length) as $hidden_t4 |
      ($hidden_t3 + $hidden_t4) as $total_hidden |
      if $total_hidden > 0 then
        if $hidden_t3 > 0 then
          "\n_\($total_hidden) more PRs in Tier 3-4 (not shown). Run `/open-prs` for full list._"
        else
          "\n_\($hidden_t4) PRs in Tier 4 not shown (drafts, CI failing, merge conflicts, waiting on author)._"
        end
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
