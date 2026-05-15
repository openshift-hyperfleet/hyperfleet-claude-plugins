# hyperfleet-work-triage

Work triage skills for HyperFleet: bug/issue triage and PR prioritization.

## Installation

```bash
/install hyperfleet-work-triage@openshift-hyperfleet/hyperfleet-claude-plugins
```

## Skills

### `/bugs-triage` — Bug & Issue Triage

```bash
/bugs-triage            # Triage both JIRA bugs and GitHub issues
/bugs-triage jira       # Triage only JIRA bugs
/bugs-triage github     # Triage only GitHub issues
```

**What it does:**

- **JIRA Bug Triage:** Fetches all bugs with status "New" in HYPERFLEET, skips assigned ones, and for each bug recommends an action (move to Backlog, request info, close, convert to RFE, escalate)
- **GitHub Issues Triage:** Fetches untriaged issues across all repos, checks if already tracked in JIRA or resolved by PRs, and recommends an action (accept as Bug/RFE, help, reject, duplicate)
- Reports bugs/issues open for more than 3 sprints (6 weeks)

### `/open-prs` — Intelligent PR Review Queue

```bash
/open-prs                           # Compact ranked list (default)
/open-prs --explain                 # Full reasoning + factor breakdowns
/open-prs --repo hyperfleet-api     # Scope to one repo
/open-prs --component Adapter       # Filter by JIRA component
```

**What it does:**

- Scans all repos in the org for open PRs (parallel queries)
- Cross-references with JIRA: priority, sprint deadlines, story points, blocking chains
- Reads PR diffs and ticket descriptions to understand actual urgency
- Checks CI status from all sources (GitHub Actions + Prow)
- Detects unresolved reviewer comments and author responsiveness
- Applies 8-factor weighted scoring with confidence levels
- Groups PRs into 4 tiers: Immediate Attention, Should Review Soon, When You Have Time, Informational
- Works without JIRA CLI (graceful degradation with reduced confidence)

## Prerequisites

- [GitHub CLI](https://cli.github.com/) (`gh`) — authenticated with access to openshift-hyperfleet repos (required)
- [jira-cli](https://github.com/ankitpokhrel/jira-cli) — configured for the HYPERFLEET project (required for `/bugs-triage`, optional for `/open-prs`)
- [jq](https://jqlang.github.io/jq/) — JSON processor (required for `/open-prs`). Install via `brew install jq` or `apt-get install jq`

## Shared Reference Data

| File | Used by | Purpose |
|------|---------|---------|
| `references/github-repos.md` | Both skills | Repositories in scope |
| `skills/bugs-triage/references/owners.csv` | `/bugs-triage` | Component/domain owners for assignee suggestions |

Ticket creation (formatting, Activity Types, Story Points) is delegated to the `hyperfleet-jira:jira-ticket-creator` skill.
