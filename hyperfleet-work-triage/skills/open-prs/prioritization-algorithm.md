# Prioritization Algorithm

This document defines the 8-factor weighted scoring system used to rank open PRs by review priority.

## Overview

Each PR is scored on 8 independent factors, each producing a raw score from 0-10. Factors are weighted to produce a composite **Priority Score** from 0-100. A separate **Confidence Score** (0-100%) indicates how certain the ranking is.

```text
Priority Score = Σ (factor_raw_score × factor_weight × 10)
```

## Factor Weights

| # | Factor | Weight | Rationale |
|---|--------|--------|-----------|
| 1 | JIRA Priority & Urgency | 20% | Business priority is the strongest signal — it reflects decisions made by the team about what matters |
| 2 | Blocking Impact | 18% | Unblocking others has outsized value — one idle PR can stall multiple people |
| 3 | Staleness & Age | 16% | Long-waiting PRs represent accumulated opportunity cost and context decay |
| 4 | Risk & Content Analysis | 14% | Understanding what the PR actually does reveals urgency that fields don't capture |
| 5 | Review Progress | 12% | PRs close to completion deserve a final push; PRs waiting on author shouldn't burden reviewers |
| 6 | PR Size & Complexity | 8% | Small PRs are quick wins — clearing them first reduces the queue efficiently |
| 7 | CI/Check Status | 7% | Passing CI means the PR is ready for human review; failing CI means fix that first |
| 8 | Story Points & Impact | 5% | Higher-point work sitting idle represents more wasted effort, but points alone don't determine review order |

**Total: 100%**

---

## Factor 1: JIRA Priority & Urgency (Weight: 20%)

Measures the business priority assigned to the work, including ticket priority level, activity type, SLA proximity, and sprint deadline pressure.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | Blocker priority AND SLA breach imminent or already breached (>24h for Blocker) |
| 9 | Blocker priority, within SLA window |
| 8 | Critical priority OR Security & Compliance activity type OR Incidents & Support activity type |
| 7 | High/Major priority, approaching SLA (>3 working days for Critical/Major) |
| 6 | High/Major priority, within SLA |
| 5 | Normal priority, ticket is in the current sprint (`customfield_10020` has an entry with `state: "active"` — regardless of the ticket's own status field) |
| 4 | Normal priority, ticket is NOT in the current sprint (no active sprint entry in `customfield_10020`, or only `"future"`/`"closed"` entries) |
| 3 | Low/Minor priority |
| 2 | JIRA ticket exists but priority is "Undefined" or not explicitly set (treat as unknown urgency) |
| 1 | No JIRA ticket linked, but PR title/labels suggest low-priority work (docs, chores) |
| 0 | No JIRA ticket linked, no other priority signals available |

### SLA Reference

| JIRA Priority | Triage SLA | Fix/Workaround SLA |
|---------------|------------|---------------------|
| Blocker | Within 24 hours | Within 72 working hours |
| Critical/Major | Per week | Within 5 working days |
| Normal | Per sprint | Must be fixed in coming release |
| Low | Per sprint | Max 2 sprints |

### Sprint Proximity Boost

After computing the base score from the rubric above, apply a sprint proximity boost for tickets that are in the **current active sprint**.

**How to determine sprint membership and end date:** Check `fields.customfield_10020` in the ticket's raw JSON for an entry with `state: "active"`. If found, the ticket is in the current sprint — use the `endDate` field from that entry. No separate sprint list command is needed. **Ignore** entries with `state: "future"` or `state: "closed"` — only `"active"` qualifies for the boost.

| Business Days Until Sprint End | Boost | Rationale |
|--------------------------------|-------|-----------|
| ≤ 0 (sprint overrun — end date has passed but sprint still active) | +3 | Sprint has OVERRUN — this work should have been done already |
| 1-3 business days | +2 | Sprint is closing — unreviewed PRs risk carry-over |
| 4-7 business days | +1 | Sprint is in the second half — review soon to avoid end-of-sprint crunch |
| > 7 business days | +0 | Sprint has plenty of time remaining |
| Ticket NOT in current sprint | +0 | No sprint pressure (already reflected in base score: 5 for in-sprint vs 4 for backlog) |

**Cap:** The total Factor 1 score (base + boost) is capped at **10**. A Normal-priority in-sprint ticket (base 5) with 2 days left gets boosted to 7. A Critical ticket (base 8) in sprint overrun gets 8 + 3 = 11, capped to 10.

**Note on base score vs boost:** The base rubric already distinguishes "in sprint" (5) from "not in sprint" (4) — this is a static recognition of sprint membership. The boost adds *deadline pressure* on top, which increases as the sprint end approaches. This is intentional double-weighting: being in a sprint matters a little, being in a sprint that's about to end matters a lot.

### When JIRA is unavailable

If jira CLI is not available, this factor defaults to a score of **5** for all PRs (midpoint — truly neutral, no bias toward high or low urgency). Sprint proximity boost is not applied. Confidence is reduced (see Confidence Score section).

---

## Factor 2: Blocking Impact (Weight: 18%)

Measures how much other work is stalled waiting on this PR.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | Blocks 3+ other JIRA tickets or PRs, including cross-team dependencies |
| 9 | Blocks 2 other tickets/PRs, at least one is high priority |
| 8 | Blocks 1 high-priority ticket/PR OR is blocking a release/milestone |
| 7 | Blocks 1-2 normal-priority tickets/PRs |
| 6 | Part of a cross-repo PR chain (e.g., API + Sentinel changes for the same feature) |
| 5 | JIRA ticket has "blocks" links but blocked tickets are low priority or in backlog |
| 4 | PR title or JIRA comments mention "blocking" or "prerequisite" informally |
| 3 | No explicit blocking relationships found, but ticket is a dependency based on content analysis |
| 2 | No blocking relationships detected |
| 1 | PR is itself blocked by another PR (cannot merge yet anyway) |
| 0 | PR is itself blocked AND the blocker has no clear resolution timeline |

### How to detect blocking relationships

1. **JIRA linked issues**: Check `issuelinks` in the raw JSON for "blocks" and "is blocked by" relationships
2. **JIRA comments**: Scan last 5 comments for phrases like "blocking", "prerequisite", "waiting on this", "need this before"
3. **Related PRs**: If multiple PRs reference the same JIRA ticket, they may form a dependency chain
4. **PR labels**: Check for labels like `blocking`, `prerequisite`, `release-blocker`

### When JIRA is unavailable

If jira CLI is not available, only methods 3 and 4 above are usable. Default to score **2** (no blocking detected) unless PR labels or related PRs provide evidence otherwise. Confidence is reduced.

---

## Factor 3: Staleness & Age (Weight: 16%)

Measures how long the PR has been waiting for review attention, combining both absolute age and time since last meaningful activity.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | Open >14 days AND no reviews at all |
| 9 | Open >14 days with some reviews, OR open 7-14 days with no reviews |
| 8 | Open 7-14 days with some reviews, OR no activity (no new commits, no comments) in >7 days |
| 7 | Open 5-7 days |
| 6 | Open 3-5 days |
| 5 | Open 2-3 days |
| 4 | Open 1-2 days |
| 3 | Open 12-24 hours |
| 2 | Open 4-12 hours |
| 1 | Open 1-4 hours |
| 0 | Just opened (< 1 hour) |

### Age calculation

```text
age_days = (current_utc_time - PR.createdAt) / 86400
```

**Important:** Do NOT rely on `updatedAt` as a staleness signal. GitHub updates this timestamp for ANY activity — bot comments, CI status changes, label changes, dependabot interactions — not just meaningful human activity. A PR can have `updatedAt = today` while no human has looked at it in weeks.

Instead, use `createdAt` (PR age) as the primary staleness signal, combined with review state from Factor 5. The rubric entries for "no reviews at all" vs "with some reviews" account for whether humans have engaged.

### SLA breach detection

Flag any PR that has been open for an extended period without a review. The default threshold is **3 business days** (a reasonable starting point based on industry benchmarks — the team has not yet defined an official SLA target). When calculating business days, exclude weekends (Saturday and Sunday). A PR opened Friday at 5pm and checked Monday at 9am is ~0.5 business days, NOT 2.5 calendar days.

---

## Factor 4: Risk & Content Analysis (Weight: 14%)

Measures the actual risk and urgency of the changes based on reading the PR content, diff summary, and JIRA ticket description — not just field values.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | Security vulnerability fix, CVE patch, or production incident hotfix |
| 9 | Data integrity fix (database migration, data corruption prevention) |
| 8 | Bug fix for user-facing functionality in production |
| 7 | Bug fix for internal/non-user-facing functionality OR feature critical for an upcoming milestone |
| 6 | Feature implementation that is actively needed (based on JIRA description/comments) |
| 5 | Feature implementation for future sprint/roadmap work |
| 4 | Refactoring that improves reliability or reduces technical debt |
| 3 | Infrastructure/CI improvements, developer tooling |
| 2 | Documentation updates, test additions |
| 1 | Minor cleanup, formatting, typo fixes |
| 0 | Experimental/exploratory changes, spikes |

### Risk Label Integration (HYPERFLEET-1168)

The Prow risk scoring job (HYPERFLEET-991) applies `risk/low`, `risk/medium`, `risk/high` labels to PRs based on deterministic signals (lines changed, sensitive file paths, test coverage). These labels provide a **floor score** for Factor 4 — the LLM classification can only raise the score, never lower it below the label floor.

| Risk Label | Floor Score | Rationale |
|------------|-------------|-----------|
| `risk/high` (4+ points) | 8 | Sensitive paths + large size + missing tests = high-risk change |
| `risk/medium` (2-3 points) | 6 | Some risk signals present — warrants careful review |
| `risk/low` (0-1 points) | No floor | LLM classification alone is sufficient |
| No label | No floor | Fallback to LLM-only classification — no regression |

**Final Factor 4 score = max(label_floor, LLM_classification)**

This means:
- A `risk/high` PR classified by the LLM as "feature" (score 5) still gets Factor 4 = 8 (the label floor wins)
- A `risk/low` PR classified by the LLM as "security fix" (score 10) gets Factor 4 = 10 (the LLM wins)
- PRs without a risk label use LLM classification only (backward compatible)

The risk labels are already available in the PR metadata collected in Step 1 (`collect-data.sh`) — no additional API call is needed.

### How to classify (LLM)

The LLM reads the **full PR diff** (not truncated) to classify the changes. For very large PRs (>3000 lines), the diff stat + file list is used instead.

1. **PR labels**: `security`, `hotfix`, `bug`, `feature`, `refactor`, `docs`
2. **Branch name**: `hotfix/`, `bugfix/`, `fix/`, `feat/`, `docs/`, `refactor/`
3. **JIRA ticket type**: Bug, Story, Task, Spike
4. **JIRA activity type**: Security & Compliance → score 10, Incidents & Support → score 9-10
5. **PR diff content**: Read the full diff to classify. If diff touches security-sensitive files (auth, crypto, permissions), boost score
6. **JIRA description**: Read for urgency signals ("production issue", "customer-facing", "blocking release")

### Deterministic signals (pre-computed by `score.jq`)

The scoring script pre-computes deterministic signals from labels, branch name, JIRA type, and activity type. These are combined with the risk label floor to produce a `deterministic_floor` for Factor 4. The LLM classification is compared against this floor, and the maximum wins.

**Non-determinism note:** The LLM classification component of this factor may produce slightly different scores across runs. However, the deterministic floor from risk labels ensures that high-risk PRs are never under-scored, even if the LLM classification varies. PRs near tier boundaries (e.g., score 74 vs 76) could still shift between tiers on consecutive runs, but this is limited to the LLM-classified portion only. Override rules (CI failing, waiting on author, Blocker boost, etc.) remain fully deterministic.

---

## Factor 5: Review Progress (Weight: 12%)

Measures where the PR is in the review lifecycle and whether it needs reviewer attention or author attention.

### Scoring Rubric

**Note:** Reviewers are auto-assigned in this organization, so `reviewRequests` being populated does NOT mean someone consciously asked for a review. The key signal is whether anyone has actually **engaged** (commented, reviewed, approved) — not whether reviewers are assigned.

| Score | Criteria |
|-------|----------|
| 10 | Zero engagement — no reviews or comments from anyone (not counting bots), PR open >2 days |
| 9 | Zero engagement, PR open 1-2 days |
| 8 | Zero engagement, PR open <1 day |
| 7 | Has reviews but needs more approvals to meet merge requirements |
| 6 | Re-review needed — author pushed new commits after changes were requested |
| 5 | Approved by some reviewers, needs one more approval |
| 4 | Active review discussion — comments going back and forth between author and reviewer |
| 3 | Has reviewer comments, author has responded (committed or commented after) — re-review needed |
| 2 | Has reviewer comments, author has partially responded — some feedback may still be outstanding |
| 1 | Has unresolved reviewer comments with no author response — waiting on author (Tier 4 override applies, see below) |
| 0 | Fully approved, ready to merge — no reviewer action needed |

### Review state detection

Determine review state from `latestReviews` and `reviewDecision` — these show what reviewers actually did.

1. `latestReviews`: State of each reviewer's latest review (APPROVED, CHANGES_REQUESTED, COMMENTED). This is the most reliable signal.
2. `reviewDecision`: Overall decision (APPROVED, REVIEW_REQUIRED, CHANGES_REQUESTED). This is the aggregate status.

**Do NOT rely on `reviewRequests`** for determining whether a PR needs review attention. Reviewers are auto-assigned in this organization, so this field is always populated for new PRs. It does not indicate a conscious request for review.

**To detect "author addressed changes":** Fetch the latest commit date via:
```bash
gh api --paginate repos/openshift-hyperfleet/REPO/pulls/NUMBER/commits --jq '.[-1].commit.committer.date' 2>/dev/null
```
Compare against the timestamp of the `CHANGES_REQUESTED` review in `latestReviews`. If the latest commit is newer → author has responded (score 6). If older → author has NOT responded (score 1, Tier 4 override).

### Reviewer comments with no author response → Waiting on author

If a reviewer (not the PR author, not a bot) has left comments on the PR and the author has not responded, the PR has already received review attention. The ball is in the author's court. This PR should be **deprioritized** in favor of PRs that have received zero attention.

**How to detect outstanding reviewer feedback:** Review comments and general PR comments are collected by `collect-data.sh` (Step 1). From the combined results:
1. Filter out comments by the PR author and known bots (`coderabbitai`, `openshift-ci[bot]`, `openshift-ci`, `dependabot[bot]`, `renovate[bot]`, `github-actions[bot]`)
2. Find the most recent reviewer comment date
3. Find the author's latest activity (most recent commit date OR most recent comment by the author)
4. If the most recent reviewer comment is NEWER than the author's latest activity → author has NOT responded

If the API calls fail, default to "no outstanding feedback" (no penalty applied).

**Note:** The REST API does not expose per-thread `isResolved` or `isOutdated` status (those require GraphQL, which is excluded from approved commands for security — it allows mutations). Instead, we use timestamp comparison: if the author has been active after the reviewer's comment, they have effectively responded. When PreToolUse hooks are implemented (HYPERFLEET-1066), GraphQL can be re-enabled with deterministic mutation blocking.

**Scoring impact:**
- Reviewer comments exist AND author has NOT responded → score **1** (waiting on author) and the **Tier 4 override** applies (see below)
- Reviewer comments exist AND author HAS responded (comment or commit after the reviewer's comment) → score **2-3** depending on the recency and volume of feedback
- No reviewer comments, or all feedback addressed → score based on the standard rubric above

**In `--explain` mode:** Mention the reviewer comment and the fact that the author hasn't responded. E.g., "Reviewer comment from @rafabene (May 4) with no author response — PR deprioritized, waiting on author."

### Override: Waiting on author

This PR moves to **Tier 4** regardless of other scores — even for Blocker tickets — if EITHER of these conditions is true:

1. `reviewDecision` is `CHANGES_REQUESTED` and the author has NOT pushed commits since the review was submitted
2. A reviewer (non-bot, non-author) has commented on the PR AND the author's latest activity (commit or comment) is older than the most recent reviewer comment

In both cases, the reviewer has done their job; the author needs to respond. See `apply_overrides` in `score.jq` for the override precedence order.

---

## Factor 6: PR Size & Complexity (Weight: 8%)

Smaller PRs should generally be reviewed first — they're quick wins that reduce the queue and are less likely to have defects.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | Tiny: 1-10 lines changed, 1-2 files |
| 9 | Small: 11-50 lines, 1-3 files |
| 8 | Moderate-small: 51-100 lines, 2-5 files |
| 7 | Moderate: 101-200 lines, 3-8 files |
| 6 | Medium: 201-300 lines, 5-10 files |
| 5 | Medium-large: 301-500 lines, 5-15 files |
| 4 | Large: 501-800 lines, 10-20 files |
| 3 | Very large: 801-1200 lines |
| 2 | Extremely large: 1201-2000 lines |
| 1 | Massive: >2000 lines |
| 0 | Auto-generated or bulk changes (>3000 lines, likely generated code) |

### Size calculation

```text
total_lines_changed = PR.additions + PR.deletions
```

### Large PR warning

Flag PRs with >500 lines changed in the Flags & Warnings section with a suggestion to consider splitting, unless the changes are:
- Auto-generated (OpenAPI spec, vendor directory, go.sum)
- A single large file addition (new module, migration)
- Primarily test code

---

## Factor 7: CI/Check Status (Weight: 7%)

PRs with passing CI are ready for review. PRs with failing CI should fix checks before requesting human review time.

### Scoring Rubric

Any CI failure triggers a Tier 4 override, so the rubric is binary:

| Score | Criteria |
|-------|----------|
| 10 | All checks passing — CI is green, ready for human review |
| 6 | Checks pending/running or no checks configured — may resolve soon |
| 0 | Any check failing — Tier 4 override applies (see below) |

### Check status detection

Gather all checks and statuses from **both** `statusCheckRollup` (GitHub Checks) and the commit status API (Prow, external CI) — collected by `collect-data.sh` and scored by `score.jq`'s `score_factor7`. Combine into one list.

**Exclusions:** Do not count `tide` (merge-readiness gate) or all-null entries (checks not configured). Do not count PRs with `needs-ok-to-test` label as failing (process gate, score as pending).

Then classify:
- All passing → score 10
- All pending → score 6
- **Any failure → score 0 and Tier 4 override** (see below)
- No checks at all → score 6 (pending)

**Special case — `needs-ok-to-test` label:** CI hasn't run because the PR needs `/ok-to-test` approval first. This is a process gate, NOT a code quality failure. Score as 6 (pending), not 0 (failing). Do not trigger the Tier 4 override.

### Override: Any CI failing

If **any** CI check or commit status is failing, the PR moves to **Tier 4** regardless of other scores — even for Blocker tickets. One failing check is enough. The author needs to fix CI before reviewers spend time on it. See `apply_overrides` in `score.jq` for the override precedence order.

---

## Factor 8: Story Points & Impact (Weight: 5%)

Higher story points indicate more impactful work sitting idle, though story points alone don't determine review order.

### Scoring Rubric

| Score | Criteria |
|-------|----------|
| 10 | 13 story points (should have been split — flag this, but it's high-impact work) |
| 8 | 8 story points |
| 6 | 5 story points |
| 4 | 3 story points |
| 3 | 1 story point |
| 2 | 0 story points (tracking only) |
| 1 | Story points not set on ticket |
| 0 | No JIRA ticket linked |

### When JIRA is unavailable

If jira CLI is not available, this factor defaults to a score of **2** for all PRs. Confidence is reduced.

---

## Tier Assignment

The final weighted score maps to a tier. Overrides take precedence over score-based assignment.

### Score-based thresholds

| Tier | Score Range | Meaning |
|------|------------|---------|
| Tier 1 — Immediate Attention | ≥ 75 | Drop what you're doing |
| Tier 2 — Should Review Soon | 50–74 | Today or tomorrow |
| Tier 3 — This Week | 25–49 | This week |
| Tier 4 — Informational | < 25 | Not actionable for reviewers right now |

### Override-based assignment

Applied by `score.jq`'s `apply_overrides` in this precedence order (first match wins):

1. CI failing → Tier 4
2. Waiting on author → Tier 4
3. Merge conflicts → Tier 4
4. Draft → Tier 4
5. JIRA Blocker/Critical → Tier 1
6. No JIRA ticket → capped at Tier 3

---

## Confidence Score

The confidence score is a separate metric (0-100%) that indicates how reliable the priority ranking is. It does NOT affect the priority score directly but helps the user assess which rankings are solid vs. speculative.

### Formula

```text
confidence = (data_completeness × 0.4) + (signal_agreement × 0.4) + (clarity × 0.2)
```

Each component ranges 0-100. The weighted sum produces a confidence score of 0-100.

### Components

#### Data Completeness (0-100, contributes 40% to confidence)

What percentage of available data sources were successfully queried?

| Available Data | Points |
|----------------|--------|
| GitHub PR metadata fetched | +25 |
| JIRA ticket fetched (with all fields) | +25 |
| CI/check status available | +15 |
| PR diff stat fetched | +15 |
| JIRA comments fetched | +10 |
| Blocking relationships checked | +10 |

**If JIRA CLI is unavailable:** Maximum data completeness is 55/100. This automatically caps overall confidence.

#### Signal Agreement (0-100, contributes 40% to confidence)

Do the independent factors agree on the PR's priority level?

| Agreement Level | Score |
|-----------------|-------|
| All 8 factors point to the same tier | 100 |
| 6-7 factors agree, 1-2 are neutral or slightly divergent | 80 |
| 5 factors agree, 3 are divergent | 60 |
| Factors split roughly evenly between high and low priority | 40 |
| Factors strongly contradict each other | 20 |

**Example of contradiction:** JIRA says Blocker, but PR is a tiny docs change with zero engagement. The JIRA priority might be misset, or the docs change IS critical — hard to tell.

#### Clarity (0-100, contributes 20% to confidence)

Is the priority determination clear-cut or a judgment call?

| Clarity Level | Score |
|---------------|-------|
| Unambiguous: Blocker + old + no reviews = clearly urgent | 100 |
| Fairly clear: most signals point one direction | 75 |
| Moderate: requires weighing competing signals | 50 |
| Ambiguous: could reasonably be ranked several positions higher or lower | 25 |

### Confidence Labels

| Range | Label | Meaning |
|-------|-------|---------|
| 85-100% | Very High | Ranking is highly reliable — multiple strong signals agree |
| 70-84% | High | Ranking is solid — minor data gaps or one divergent signal |
| 50-69% | Medium | Ranking is reasonable but could shift with more information |
| < 50% | Low | Ranking is speculative — significant data gaps or conflicting signals |

---

## Edge Cases and Tiebreakers

### Tiebreakers (when two PRs have the same priority score)

1. **Higher confidence**: PR with higher confidence score wins (more reliable ranking should appear first)
2. **Age**: Older PR wins (FIFO within the same score and confidence)
3. **Smaller size**: Smaller PR wins (quicker to clear)

### Special cases

- **PR references multiple JIRA tickets**: Use the highest-priority ticket for scoring
- **Same JIRA ticket across multiple PRs**: Note them as related in the output; score each independently but flag the relationship
- **JIRA ticket is Done/Closed but PR is still open**: Flag as a potential stale PR — the work may have been completed differently
- **Bot-authored PRs** (dependabot, renovate): Score normally but note the author type; security dependency updates should score high on Factor 4
- **PRs with the `needs-rebase` label**: Flag in warnings — author needs to rebase before review makes sense
- **PRs with the `needs-ok-to-test` label**: Flag in warnings — CI cannot run until approved. Score CI factor as 6 (pending), not 0 (failing). These are reviewable but untested.
- **PRs with merge conflicts**: → Tier 4 override (rule 3). Flag in warnings — author needs to rebase. Code will change after conflict resolution, so reviewing now is wasteful.
- **Auto-generated PRs (large diffs)**: If the diff is dominated by generated files (OpenAPI specs, `go.sum`, vendor directories), adjust Factor 6 (Size) upward — the human-reviewable portion is smaller than the line count suggests. Look at the file list to determine if the bulk is generated.
