# hyperfleet-bugs-triage

Interactive JIRA bug triage (New->Backlog) and GitHub issue triage for openshift-hyperfleet repositories.

## Installation

```bash
/install hyperfleet-bugs-triage@openshift-hyperfleet/hyperfleet-claude-plugins
```

## Usage

```bash
/bugs-triage            # Triage both JIRA bugs and GitHub issues
/bugs-triage jira       # Triage only JIRA bugs
/bugs-triage github     # Triage only GitHub issues
```

## What it does

### JIRA Bug Triage

1. Fetches all bugs with status "New" in the HYPERFLEET project
2. Skips bugs that already have an assignee
3. For each bug, presents an assessment and recommends an action:
   - Move to Backlog
   - Request more info
   - Close (Won't Do / Rejected / Duplicate)
   - Convert to RFE
   - Set missing fields
   - Escalate Blockers
4. Reports bugs open for more than 3 sprints (6 weeks)

### GitHub Issues Triage

1. Fetches untriaged issues across all openshift-hyperfleet repositories
2. Checks if issues are already tracked in JIRA or resolved by merged PRs
3. For each issue, presents an assessment and recommends an action:
   - Accept as Bug (creates JIRA ticket)
   - Accept as RFE (creates JIRA Story)
   - Provide help
   - Reject
   - Mark as Duplicate
   - Request info
4. Reports issues open for more than 3 sprints

## Prerequisites

- [jira-cli](https://github.com/ankitpokhrel/jira-cli) configured for the HYPERFLEET project
- [GitHub CLI](https://cli.github.com/) (`gh`) authenticated with access to openshift-hyperfleet repos

## Reference Data

The plugin includes reference files used during triage:

| File | Purpose |
|------|---------|
| `references/owners.csv` | Component/domain owners for assignee suggestions |
| `references/github-repos.md` | Repositories in triage scope |

Ticket creation (formatting, Activity Types, Story Points) is delegated to the `hyperfleet-jira:jira-ticket-creator` skill.
