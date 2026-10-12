# Output Format

This document defines the output format for the `/open-prs` skill. There are three modes:

- **Default (compact):** PRs grouped by area (`area/*` label), ranked by priority score inside each area. Shows PR title, URL, linked JIRA ticket, tier, review status with age and flags, and the requested reviewers with business days waiting.
- **`--slack` (Slack-ready):** Paste-ready output for Slack channels. No markdown tables, Slack-native formatting. Same area grouping; shows Tier 1-2 PRs (or 1-3 if ≤ 10 PRs). Tier 4 never shown.

**Area grouping (compact and Slack):** Prow applies `area/*` labels from OWNERS files and requests reviewers from the area's OWNERS pool, so the area is the ownership unit. A PR with several area labels appears under its first label with the others shown inline (`+area/contracts`). PRs with no area label go under `No area`, which is always the last group. Areas are ordered by their most urgent PR (best tier, then highest score). Inside an area, PRs keep their priority order.
- **`--explain` (detailed):** Full output with per-PR reasoning, factor breakdowns, flags & warnings, and summary statistics.

---

## Default (Compact) Output

### Header

```text
## Open PRs — openshift-hyperfleet

**Generated:** YYYY-MM-DD HH:MM UTC | **N PRs** across M repos | Grouped by area, ranked by priority score | `/open-prs --explain` for full analysis
```

If `--repo` or `--component` filters were applied, add:

```text
**Filter:** repo=hyperfleet-api | component=Adapter
```

If JIRA is unavailable:

```text
**Note:** JIRA unavailable — GitHub-only mode, confidence reduced.
```

### Area tables

Show one table per area. All tiers appear in the compact output; the tier is a column, and Tier 4 rows show the override reason instead of review status. Omit areas with no PRs.

```text
### area/api (N PRs)

| # | PR | Tier | Status | Reviewers |
|---|----|------|--------|-----------|
| 1 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | 🚨 T1 | No reviews, 5d ⚠️ overdue, SLA | @reviewer1, @reviewer2 (3bd) |
| 4 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title (+area/auth) | 🟡 T2 | In review, 3d | @reviewer1 (1bd) |
| - | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | 🔵 T4 | Draft | none requested |

### area/sentinel (N PRs)

| # | PR | Tier | Status | Reviewers |
|---|----|------|--------|-----------|
| 2 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | 🚨 T1 | Approved, 2d | none requested |

### No area (N PRs)

| # | PR | Tier | Status | Reviewers |
|---|----|------|--------|-----------|
| 6 | [repo#number](url) — PR title without ticket | 🟢 T3 | No reviews, 1d | @reviewer2 (1bd) |
| - | [repo#number](url) — PR title without ticket | 🔵 T4 | CI failing | none requested |
```

**Column definitions (compact):**

| Column | Content | Example |
|--------|---------|---------|
| # | Rank position by priority score across all areas (tiers 1-3 only; `-` for Tier 4) | `1` |
| PR | `[repo#number](url) — title`. The repo#number links to the GitHub PR. If a JIRA ticket key appears in the title, it is replaced with a link to the JIRA ticket. Extra area labels follow the title as `(+area/x, area/y)`. | `[hyperfleet-api#115](https://...) — [HYPERFLEET-856](https://redhat.atlassian.net/browse/HYPERFLEET-856) - fix: Deletion observability metrics (+area/auth)` |
| Tier | Tier emoji and number | `🚨 T1`, `🟡 T2`, `🟢 T3`, `🔵 T4` |
| Status | Review state and age, followed by flags when present (`⚠️ overdue, SLA, stale`). Tier 4: reason for informational status (`Draft`, `Waiting on author`, `CI failing`, `Merge conflicts`) | `No reviews, 5d ⚠️ overdue, SLA` |
| Reviewers | Requested reviewers still pending (the reviewer of record, requested from the area's OWNERS pool) and business days since the latest request, or `none requested` | `@kuudori, @pnguyen44 (3bd)` |

### Recommendation

End with a single actionable line:

```text
---

**Start with:** [repo#number](url) — [One sentence why]
```

If ALL PRs are Tier 4 (no actionable PRs in Tiers 1-3):

```text
---

**No actionable PRs right now** — all open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback.
```

---

## `--slack` (Slack-Ready) Output

When the user passes `--slack`, produce Slack mrkdwn output with inline links for PR and JIRA references.

**Critical:** Wrap the ENTIRE Slack output in a single code block (triple backticks) in your response. This preserves the Slack formatting characters (`*`, `_`, `<url|text>`) through Claude Code's terminal. The user copies the content from inside the code block and pastes it into Slack.

**Formatting rules:**
- Bold: `*text*` (single asterisk, NOT double)
- Italic: `_text_` (underscores)
- Inline links: `<URL|display text>` — Slack renders these as clickable text when sent via webhook/API. For manual paste, the raw syntax is visible but URLs are still clickable
- PR links: `` <https://github.com/openshift-hyperfleet/REPO/pull/NUMBER|`REPO #NUMBER`> `` — renders as inline code-styled clickable link
- JIRA links: `<https://redhat.atlassian.net/browse/TICKET-KEY|TICKET-KEY>` — renders as clickable underlined text
- No markdown tables — use bullet lists

**Tier visibility rules:**
- If total PRs > 10: show only Tier 1 and Tier 2 (unless neither has PRs — then show Tier 3 so the output isn't empty)
- If total PRs ≤ 10: show Tiers 1, 2, and 3
- NEVER show Tier 4 — not actionable, adds noise to the channel

**Area sections and tier emojis:**
- One section per area: `EMOJI *area/name (N PRs)*` where EMOJI is the best tier in that section (🚨 Tier 1, 🟡 Tier 2, 🟢 Tier 3). Unlabeled PRs go under `*No area (N PRs)*`, last.
- Each PR bullet starts with its own tier emoji (🚨, 🟡, 🟢) since tiers are no longer section headers.
- Tier visibility rules above decide which PRs are included; an area with no visible PRs is omitted.

**Header emoji** — varies based on the highest tier with PRs:
- 🚨 if Tier 1 PRs exist
- 🟡 if Tier 2 is the highest
- 🟢 if only Tier 3
- 🟢 if no Tier 1-3 PRs exist (all PRs are Tier 4 — nothing actionable)

**PRs Dashboard link** — the line immediately under the metadata line links to the HyperFleet org project board so readers can jump from the digest to the full board:

`📋 <https://github.com/orgs/openshift-hyperfleet/projects/1/views/1|PRs Dashboard>`

This link is Slack-only — it is not shown in compact or `--explain` output. It also appears in the all-Tier-4 edge case (below).

### Full template

```text
HEADER_EMOJI *Open PRs — openshift-hyperfleet*
_YYYY-MM-DD HH:MM UTC | N PRs across M repos | grouped by area_
📋 <https://github.com/orgs/openshift-hyperfleet/projects/1/views/1|PRs Dashboard>

🚨 *area/api (2 PRs)*

• 🚨 <https://github.com/openshift-hyperfleet/hyperfleet-api-spec/pull/44|`hyperfleet-api-spec #44`> : <https://redhat.atlassian.net/browse/HYPERFLEET-978|HYPERFLEET-978> - feat: Add PUT for internal status endpoints — _No reviews, 5d_ · 👀 @kuudori, @pnguyen44 (3bd) ⚠️ overdue, SLA
• 🟡 <https://github.com/openshift-hyperfleet/hyperfleet-api/pull/137|`hyperfleet-api #137`> : <https://redhat.atlassian.net/browse/HYPERFLEET-978|HYPERFLEET-978> - fix: Change status endpoint from POST to PUT — _In review, 3d_ · 👀 @mliptak0 (1bd) · _+area/auth_

🟡 *area/architecture (1 PR)*

• 🟡 <https://github.com/openshift-hyperfleet/architecture/pull/122|`architecture #122`> : <https://redhat.atlassian.net/browse/HYPERFLEET-896|HYPERFLEET-896> - feat: Config Driven Generic Resource API Design — _Approved, 2d_ · 👀 none requested

_N more PRs in Tier 3-4 (not shown). Run `/open-prs` for full list._
```

### Per-PR format

Each PR is a single bullet line:

```text
• TIER_EMOJI <PR_URL|`repo #number`> : <JIRA_URL|TICKET-KEY> - type: PR title — _review status, age_ · 👀 @reviewer1, @reviewer2 (Nbd) ⚠️ flags · _+area/other_
```

- **Tier emoji:** 🚨 Tier 1, 🟡 Tier 2, 🟢 Tier 3
- **PR link:** `<github-url|` `` `repo #number` `` `>` — inline code-styled clickable link
- **Title with inline JIRA link:** The JIRA ticket key in the title is replaced with a Slack link to the ticket. PRs without a ticket key show the title as-is.
- **Status suffix:** review state and age in italics — e.g., `_No reviews, 5d_`, `_Approved, 2d_`, `_In review, 3d_`
- **Reviewers:** `👀` followed by the requested reviewers still pending (GitHub logins) and business days since the latest request, e.g. `👀 @kuudori, @pnguyen44 (3bd)`; `👀 none requested` when no request is pending
- **Flags:** `⚠️` followed by any of `overdue` (requested reviewer waiting more than one business day), `SLA` (more than 3 days with no human review), `stale` (more than 7 days). Omitted when there are no flags.
- **Other areas:** `· _+area/x, area/y_` when the PR carries more than one area label. Omitted otherwise.

Each PR is one bullet point — no multi-line entries.

### Filters

If `--repo` or `--component` filters were applied, add after the header:

`_Filter: repo=hyperfleet-api_`

### JIRA unavailable

If JIRA CLI is not available, add after the header:

`_⚠️ JIRA unavailable — GitHub-only mode, confidence reduced_`

### Summary line

Always end with a summary of what was omitted:

- If PRs were omitted (Tier 3/4 not shown): `_N more PRs in Tier 3-4 (not shown). Run /open-prs for full list._`
- If all visible PRs were shown (total ≤ 10, Tiers 1-3 shown): `_N PRs in Tier 4 not shown (drafts, CI failing, waiting on author)._` — only if Tier 4 has PRs
- If no PRs were omitted: no summary line needed

### Edge cases

**Zero PRs:**

```text
🟢 No open PRs found across the openshift-hyperfleet organization. 🎉
```

**All PRs are Tier 4 (none actionable):**

```text
🟢 Open PRs — openshift-hyperfleet
_YYYY-MM-DD HH:MM UTC | N PRs across M repos_
📋 <https://github.com/orgs/openshift-hyperfleet/projects/1/views/1|PRs Dashboard>

No actionable PRs right now — all N open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback.
```

**No Tier 1 or 2 PRs but Tier 3 exists:**

Show Tier 3 regardless of total count (since there's nothing more urgent to show).

**Empty tier:**

Omit the tier entirely — do not show a tier heading with 0 PRs.

---

## `--explain` (Detailed) Output

When the user passes `--explain`, show the full output with all 8 sections:

1. Header
2. Tier 1
3. Tier 2
4. Tier 3
5. Tier 4
6. Flags & Warnings
7. Summary Statistics
8. Recommendation

Empty tiers are omitted entirely — do not show a tier heading with "0 PRs".

---

### 1. Header

```text
## Open PRs Awaiting Review — openshift-hyperfleet

**Generated:** YYYY-MM-DD HH:MM UTC
**PRs analyzed:** N across M repositories
**Needing immediate attention:** X
**JIRA data:** Available (enriched) | Not available (GitHub-only mode, confidence reduced)
```

If `--repo` or `--component` filters were applied, add:

```text
**Filter:** repo=hyperfleet-api | component=Adapter
```

---

### 2. Tier 1 (Score ≥ 75 or JIRA Blocker/Critical)

#### Tier table

```text
### Tier 1 (N PRs)

| # | PR | Area | JIRA | Priority | Age | Size | Reviews | CI | Score | Confidence |
|---|----|------|----- |----------|-----|------|---------|----|-------|------------|
| 1 | [repo#number](url) | area/api | TICKET-KEY (Priority) | Priority | Xd | +A/-D (F files) | Status | Status | XX/100 | Label (XX%) |
```

**Column definitions:**

| Column | Content | Example |
|--------|---------|---------|
| # | Rank position | `1` |
| PR | `[repo#number](url)` — linked to GitHub | `[hyperfleet-api#115](https://...)` |
| Area | First `area/*` label, with extra labels after a `+`; `No area` when unlabeled | `area/api +area/auth` |
| JIRA | `TICKET-KEY (Priority)` or `No ticket` | `HYPERFLEET-856 (High)` |
| Priority | Derived priority label from scoring | `High` |
| Age | Days since PR creation | `12d` or `4h` |
| Size | `+additions/-deletions (N files)` | `+234/-45 (8 files)` |
| Reviews | Human-readable review status | `No reviews`, `1/2 approved`, `Changes requested` |
| CI | Check status | `Passing`, `Failing (2)`, `Pending`, `None` |
| Score | Priority score out of 100 | `87/100` |
| Confidence | Confidence label and percentage | `Very High (92%)` |

#### Per-PR detail block (Tier 1 and 2 only)

After the table, show a detailed block for each PR:

```text
---

#### #1: repo#number — PR title
**Author:** @login | **Area:** area/api (+area/auth) | **Requested reviewers:** @reviewer1, @reviewer2 (3 business days waiting, overdue)
**JIRA:** [TICKET-KEY](jira-url) | **Type:** Bug | **Story Points:** 5 | **Component:** API
**Domain:** Security fix | Bug fix

**Why this is ranked #1:**
> [2-4 sentences explaining the reasoning. Reference specific signals: JIRA priority, age,
> blocking relationships, content analysis, review state, CI status. Explain why these signals
> combine to make this the top priority. Be concrete — "12 days without review breaches the
> 3-day SLA" is better than "this PR is old".]

**Confidence: Very High (92%)** — [Brief explanation: "JIRA data complete, all signals aligned, unambiguous priority" OR "JIRA unavailable — ranking based on GitHub signals only, moderate certainty"]

**Factor breakdown:**
| Factor | Raw (0-10) | Weighted |
|--------|-----------|----------|
| JIRA Priority & Urgency | 8 | 16.0 |
| Blocking Impact | 7 | 12.6 |
| Staleness & Age | 9 | 14.4 |
| Risk & Content Analysis | 8 | 11.2 |
| Review Progress | 10 | 12.0 |
| PR Size & Complexity | 7 | 5.6 |
| CI/Check Status | 10 | 7.0 |
| Story Points & Impact | 6 | 3.0 |
| **Total** | | **81.8/100** |
```

---

### 3. Tier 2 (Score 50-74)

Same format as Tier 1: table first, then per-PR detail blocks with reasoning and factor breakdown.

---

### 4. Tier 3 (Score 25-49)

Condensed format — table only, with a brief one-line reasoning per PR instead of full detail blocks.

```text
### Tier 3 (N PRs)

| # | PR | Area | JIRA | Age | Size | Reviews | Reviewers | Score | Confidence | Reason |
|---|----|------|----- |-----|------|---------|-----------|-------|------------|--------|
| 8 | [repo#42](url) | area/sentinel | HYPERFLEET-900 | 2d | +45/-10 | No reviews | @pnguyen44 (1bd) | 38/100 | High (75%) | Normal-priority feature, recently opened |
```

---

### 5. Tier 4

No scoring table. Group by reason:

```text
### Tier 4 — Informational

**Draft PRs:**
- [repo#XX](url) — TICKET-KEY: PR title (draft since Xd ago)

**Waiting on author** (reviewer feedback not addressed — formal changes requested OR unresolved reviewer comments with no author response):
- [repo#XX](url) — TICKET-KEY: PR title (feedback pending Xd ago)

**CI failing** (fix CI before requesting review):
- [repo#XX](url) — TICKET-KEY: PR title (X checks failing since Xd ago)

**Merge conflicts** (author needs to rebase):
- [repo#XX](url) — TICKET-KEY: PR title (conflicts detected)
```

If there are no Tier 4 PRs, omit this section entirely.

---

### 6. Flags & Warnings

```text
### Flags & Warnings

- **Review wait:** N PRs have been open >3 business days without a review
  - [repo#XX](url) — Xd without review
  - [repo#YY](url) — Xd without review

- **Waiting on requested reviewer:** N PRs have a review request pending for more than 1 business day
  - [repo#XX](url) — @reviewer1, @reviewer2 requested Xbd ago (area/api)

- **No area label:** N PRs carry no `area/*` label, so no OWNERS pool was asked to review
  - [repo#XX](url) — "PR title"

- **Large PRs (>500 lines):** N PRs may benefit from splitting
  - [repo#XX](url) — XXXX lines changed across XX files

- **Missing JIRA tickets:** N PRs have no JIRA ticket in the title
  - [repo#XX](url) — "PR title"

- **Stale PRs (no activity >7 days):** N PRs have gone quiet
  - [repo#XX](url) — last activity Xd ago

- **Needs rebase:** N PRs are flagged as needing a rebase
  - [repo#XX](url) — labeled `needs-rebase`

- **Related PR groups:** N groups of PRs reference the same JIRA ticket
  - TICKET-KEY: [repo-a#XX](url), [repo-b#YY](url) — consider reviewing together
```

Only show flag categories that have at least one entry. If no flags, omit the section.

---

### 7. Summary Statistics

```text
### Summary

| Metric | Value |
|--------|-------|
| Total open PRs | N |
| Repos with open PRs | N |
| Avg age | X.X days |
| Median age | X days |
| Oldest PR | [repo#XX](url) — Xd |
| PRs with no reviews | N (XX%) |
| PRs with passing CI | N (XX%) |
| PRs with failing CI | N (XX%) |
| PRs waiting >3d for first review | N (XX%) |
| PRs waiting >1 business day on a requested reviewer | N (XX%) |
| PRs with no area label | N (XX%) |
| JIRA-linked PRs | N/N (XX%) |
| Avg confidence score | XX% |
```

---

### 8. Recommendation

End with a single actionable line:

```text
---

**Start with:** [repo#number](url) — [One sentence explaining why this is the best PR to review next]
```

If ALL PRs are Tier 4 (no actionable PRs in Tiers 1-3):

```text
---

**No actionable PRs right now** — all open PRs are drafts, waiting on author, have failing CI, or have merge conflicts. Check back after authors address feedback.
```

---

## Shared Formatting Rules

### Age formatting

| Duration | Format |
|----------|--------|
| < 1 hour | `Xm` (minutes) |
| 1-24 hours | `Xh` |
| 1-30 days | `Xd` |
| > 30 days | `Xd` (with SLA breach flag) |

### Review status formatting

Note: Review status reflects actual engagement (reviews, comments, approvals). Pending review requests are shown separately (see "Reviewer and flag formatting" below).

| State | Display |
|-------|---------|
| Zero engagement — no one has reviewed or commented | `No reviews` |
| N of M reviewers approved | `N/M approved` |
| Changes requested (formally or via unresolved comments) | `Changes requested` |
| All required approvals received | `Approved` |
| Active discussion between author and reviewer | `In discussion` |

### Reviewer and flag formatting

Prow requests reviewers from the area's OWNERS pool, so a pending request names the reviewer of record. GitHub drops the request once that reviewer submits a review, so only reviewers who have not acted yet are listed.

| Item | Display |
|------|---------|
| Pending requested reviewers and business days since the latest request | `@login1, @login2 (Nbd)` |
| No pending request | `none requested` |
| Requested reviewer waiting more than 1 business day (non-draft) | flag `overdue` |
| More than 3 days with no human review | flag `SLA` |
| More than 7 days old | flag `stale` |
| Extra area labels beyond the first | `+area/x, area/y` |

Flags are rendered together after the status as `⚠️ overdue, SLA, stale` (only those that apply). Business days exclude Saturday and Sunday.

### CI status formatting

| State | Display |
|-------|---------|
| All checks passing | `Passing` |
| Some failing | `Failing (N)` |
| Pending/running | `Pending` |
| No checks configured/triggered | `None` |
| Mix of passing and pending | `Partial (N pending)` |

### Confidence display

Always show both the label and percentage:

| Range | Display |
|-------|---------|
| 85-100% | `Very High (XX%)` |
| 70-84% | `High (XX%)` |
| 50-69% | `Medium (XX%)` |
| < 50% | `Low (XX%)` |

**Confidence emoji** (used in `--explain` per-PR blocks):
- 🟢 for High / Very High (≥ 70%)
- 🟡 for Medium (50-69%)
- 🔴 for Low (< 50%)

---

## When there are zero PRs

```text
## Open PRs — openshift-hyperfleet

**Generated:** YYYY-MM-DD HH:MM UTC

No open PRs found across the openshift-hyperfleet organization. Nothing to review!
```

## When JIRA is unavailable (`--explain` mode only)

Add a notice after the header:

```text
> **Note:** JIRA CLI is not available. Running in GitHub-only mode. Priority scoring uses only
> GitHub signals (age, size, review state, CI status). JIRA-dependent factors (ticket priority,
> story points, blocking relationships, activity type) default to neutral scores. Data
> completeness is capped at 55/100, which reduces the confidence score — typical maximum
> confidence in this mode is ~75-82% even when all other signals agree strongly.
```
