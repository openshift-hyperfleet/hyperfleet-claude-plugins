# Output Format

This document defines the output format for the `/open-prs` skill. There are three modes:

- **Default (compact):** A ranked list grouped by tier. Shows PR title, URL, linked JIRA ticket, review status with age, and tier.
- **`--slack` (Slack-ready):** Paste-ready output for Slack channels. No markdown tables, Slack-native formatting. Shows Tier 1-2 (or 1-3 if ≤ 10 PRs). Tier 4 never shown.
- **`--explain` (detailed):** Full output with per-PR reasoning, factor breakdowns, flags & warnings, and summary statistics.

---

## Default (Compact) Output

### Header

```text
## Open PRs — openshift-hyperfleet

**Generated:** YYYY-MM-DD HH:MM UTC | **N PRs** across M repos | Sorted by priority score | `/open-prs --explain` for full analysis
```

If `--repo` or `--component` filters were applied, add:

```text
**Filter:** repo=hyperfleet-api | component=Adapter
```

If JIRA is unavailable:

```text
**Note:** JIRA unavailable — GitHub-only mode, confidence reduced.
```

### Tier tables

Show each non-empty tier as a compact table. Omit empty tiers entirely.

```text
### Tier 1 (N PRs)

| # | PR | Status |
|---|----|--------|
| 1 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | Approved, 2d |
| 2 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | No reviews, 5d |

### Tier 2 (N PRs)

| # | PR | Status |
|---|----|--------|
| 3 | [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | In review, 3d |

### Tier 3 (N PRs)

| # | PR | Status |
|---|----|--------|
| 6 | [repo#number](url) — PR title without ticket | No reviews, 1d |

### Tier 4 (N PRs)

| PR | Status |
|----|--------|
| [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | Draft |
| [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | Waiting on author |
| [repo#number](url) — PR title without ticket | CI failing |
| [repo#number](url) — [TICKET-KEY](jira-url) - type: PR title | Merge conflicts |
```

**Column definitions (compact):**

| Column | Content | Example |
|--------|---------|---------|
| # | Rank position (continuous across tiers 1-3) | `1` |
| PR | `[repo#number](url) — title`. The repo#number links to the GitHub PR. If a JIRA ticket key appears in the title, it is replaced with a link to the JIRA ticket. | `[hyperfleet-api#115](https://...) — [HYPERFLEET-856](https://redhat.atlassian.net/browse/HYPERFLEET-856) - fix: Deletion observability metrics` |
| Status | Review state and age. Tiers 1-3: `Approved, 2d`, `No reviews, 5d`, `In review, 3d`. Tier 4: reason for informational status (`Draft`, `Waiting on author`, `CI failing`, `Merge conflicts`) | `No reviews, 5d` |

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

**Tier emojis and labels:**
- Tier 1: `🚨 *Tier 1 — Immediate Attention (N PRs)*`
- Tier 2: `🟡 *Tier 2 — Should Review Soon (N PRs)*`
- Tier 3: `🟢 *Tier 3 — This Week (N PRs)*`

**Header emoji** — varies based on the highest tier with PRs:
- 🚨 if Tier 1 PRs exist
- 🟡 if Tier 2 is the highest
- 🟢 if only Tier 3

### Full template

```text
HEADER_EMOJI *Open PRs — openshift-hyperfleet*
_YYYY-MM-DD HH:MM UTC | N PRs across M repos_

🟡 *Tier 2 — Should Review Soon (N PRs)*

• <https://github.com/openshift-hyperfleet/hyperfleet-api-spec/pull/44|`hyperfleet-api-spec #44`> : <https://redhat.atlassian.net/browse/HYPERFLEET-978|HYPERFLEET-978> - feat: Add PUT for internal status endpoints — _In review, 3d_

• <https://github.com/openshift-hyperfleet/architecture/pull/137|`architecture #137`> : <https://redhat.atlassian.net/browse/HYPERFLEET-978|HYPERFLEET-978> - fix: Change status endpoint from POST to PUT — _No reviews, 5d_

• <https://github.com/openshift-hyperfleet/architecture/pull/122|`architecture #122`> : <https://redhat.atlassian.net/browse/HYPERFLEET-896|HYPERFLEET-896> - feat: Config Driven Generic Resource API Design — _Approved, 2d_

_N more PRs in Tier 3-4. Run `/open-prs` for full list._
```

### Per-PR format

Each PR is a single bullet line:

```text
• <PR_URL|`repo #number`> : <JIRA_URL|TICKET-KEY> - type: PR title — _review status, age_
```

- **PR link:** `<github-url|` `` `repo #number` `` `>` — inline code-styled clickable link
- **Title with inline JIRA link:** The JIRA ticket key in the title is replaced with a Slack link to the ticket. PRs without a ticket key show the title as-is.
- **Status suffix:** review state and age in italics — e.g., `_No reviews, 5d_`, `_Approved, 2d_`, `_In review, 3d_`

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
🔴 Open PRs — openshift-hyperfleet
_YYYY-MM-DD HH:MM UTC | N PRs across M repos_

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

| # | PR | JIRA | Priority | Age | Size | Reviews | CI | Score | Confidence |
|---|----|----- |----------|-----|------|---------|----|-------|------------|
| 1 | [repo#number](url) | TICKET-KEY (Priority) | Priority | Xd | +A/-D (F files) | Status | Status | XX/100 | Label (XX%) |
```

**Column definitions:**

| Column | Content | Example |
|--------|---------|---------|
| # | Rank position | `1` |
| PR | `[repo#number](url)` — linked to GitHub | `[hyperfleet-api#115](https://...)` |
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
**Author:** @login | **Assigned reviewers:** @reviewer1, @reviewer2
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

| # | PR | JIRA | Age | Size | Reviews | Score | Confidence | Reason |
|---|----|----- |-----|------|---------|-------|------------|--------|
| 8 | [repo#42](url) | HYPERFLEET-900 | 2d | +45/-10 | No reviews | 38/100 | High (75%) | Normal-priority feature, recently opened |
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

Note: Reviewers are auto-assigned. Status is based on actual engagement, not assignment.

| State | Display |
|-------|---------|
| Zero engagement — no one has reviewed or commented | `No reviews` |
| N of M reviewers approved | `N/M approved` |
| Changes requested (formally or via unresolved comments) | `Changes requested` |
| All required approvals received | `Approved` |
| Active discussion between author and reviewer | `In discussion` |

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
