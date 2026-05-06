# Output Format

This document defines the output format for the `/open-prs` skill. There are two modes:

- **Default (compact):** A ranked list grouped by tier. Shows PR title, URL, linked JIRA ticket, confidence score, and tier.
- **`--explain` (detailed):** Full output with per-PR reasoning, factor breakdowns, flags & warnings, and summary statistics.

---

## Default (Compact) Output

### Header

```text
## Open PRs — openshift-hyperfleet

**Generated:** YYYY-MM-DD HH:MM UTC | **N PRs** across M repos | `/open-prs --explain` for full analysis
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
### Immediate Attention (N PRs)

| # | PR | JIRA | Confidence |
|---|----|------|------------|
| 1 | [repo#number](url) — PR title | TICKET-KEY | Very High (92%) |
| 2 | [repo#number](url) — PR title | TICKET-KEY | High (78%) |

### Should Review Soon (N PRs)

| # | PR | JIRA | Confidence |
|---|----|------|------------|
| 3 | [repo#number](url) — PR title | TICKET-KEY | High (80%) |

### When You Have Time (N PRs)

| # | PR | JIRA | Confidence |
|---|----|------|------------|
| 6 | [repo#number](url) — PR title | No ticket | Medium (55%) |

### Informational (N PRs)

| PR | JIRA | Status |
|----|------|--------|
| [repo#number](url) — PR title | TICKET-KEY | Draft |
| [repo#number](url) — PR title | TICKET-KEY | Waiting on author |
| [repo#number](url) — PR title | TICKET-KEY | CI failing |
| [repo#number](url) — PR title | TICKET-KEY | Merge conflicts |
```

**Column definitions (compact):**

| Column | Content | Example |
|--------|---------|---------|
| # | Rank position (continuous across tiers 1-3) | `1` |
| PR | `[repo#number](url) — PR title` | `[hyperfleet-api#115](https://...) — Deletion observability metrics` |
| JIRA | `TICKET-KEY` or `No ticket` | `HYPERFLEET-856` |
| Confidence | Label and percentage | `Very High (92%)` |
| Status | Tier 4 only — reason for informational status | `Draft`, `Waiting on author`, `CI failing`, `Merge conflicts` |

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

## `--explain` (Detailed) Output

When the user passes `--explain`, show the full output with all 8 sections:

1. Header
2. Tier 1 — Immediate Attention
3. Tier 2 — Should Review Soon
4. Tier 3 — When You Have Time
5. Tier 4 — Informational
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

### 2. Tier 1 — Immediate Attention (Score ≥ 75 or JIRA Blocker/Critical)

#### Tier table

```text
### Immediate Attention (N PRs)

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

### 3. Tier 2 — Should Review Soon (Score 50-74)

Same format as Tier 1: table first, then per-PR detail blocks with reasoning and factor breakdown.

---

### 4. Tier 3 — When You Have Time (Score 25-49)

Condensed format — table only, with a brief one-line reasoning per PR instead of full detail blocks.

```text
### When You Have Time (N PRs)

| # | PR | JIRA | Age | Size | Reviews | Score | Confidence | Reason |
|---|----|----- |-----|------|---------|-------|------------|--------|
| 8 | [repo#42](url) | HYPERFLEET-900 | 2d | +45/-10 | No reviews | 38/100 | High (75%) | Normal-priority feature, recently opened |
```

---

### 5. Tier 4 — Informational

No scoring table. Group by reason:

```text
### Informational — Not Prioritized for Review

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

- **SLA breaches:** N PRs have exceeded the 3-day first-review target
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
| SLA breach rate (>3d no review) | XX% (target: <10%) |
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
