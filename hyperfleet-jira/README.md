# HyperFleet JIRA Plugin

A Claude Code plugin that integrates JIRA with your development workflow using [jira-cli](https://github.com/ankitpokhrel/jira-cli).

## Features

### For Engineers
- **`/hyperfleet-jira:my-sprint`** - View current sprint and your assigned tickets
- **`/hyperfleet-jira:my-tasks`** - List all your assigned tasks across projects
- **`/hyperfleet-jira:new-comments`** - Find tickets with comments you may have missed

### For Team Leads
- **`/hyperfleet-jira:sprint-status`** - Comprehensive sprint health overview
- **`/hyperfleet-jira:sprint-pulse-check`** - Twice-weekly nudge queue for large work items (5 SP and above)
- **`/hyperfleet-jira:team-weekly-update`** - Weekly team progress report grouped by activity type and epic
- **`/hyperfleet-jira:triage`** - Audit tickets for missing fields and quality issues

### Skills (Auto-Activated)
- **jira-ticket-creator** - Creates well-structured tickets with What/Why/Acceptance Criteria, duplicate check, story points, activity type, component, parent epic, and validation gate
- **jira-triage** - Validates ticket quality and sprint readiness
- **jira-story-pointer** - Estimates story points using complexity analysis and historical comparison
- **Is Ticket Implemented?** - Validates whether a ticket's requirements are implemented in the codebase

## Prerequisites

### Install jira-cli

**macOS (Homebrew):**
```bash
brew install ankitpokhrel/jira-cli/jira-cli
```

**Linux:**
```bash
# Download latest release
VERSION=$(curl -sL https://api.github.com/repos/ankitpokhrel/jira-cli/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
if [ -z "$VERSION" ]; then
    echo "Error: Failed to fetch latest jira-cli version"
    exit 1
fi
curl -LO "https://github.com/ankitpokhrel/jira-cli/releases/download/${VERSION}/jira_${VERSION#v}_linux_x86_64.tar.gz"
tar -xzf "jira_${VERSION#v}_linux_x86_64.tar.gz"
sudo mv "jira_${VERSION#v}_linux_x86_64/bin/jira" /usr/local/bin/
rm -rf "jira_${VERSION#v}_linux_x86_64" "jira_${VERSION#v}_linux_x86_64.tar.gz"

```

**Other methods:** See [jira-cli installation docs](https://github.com/ankitpokhrel/jira-cli#installation)

### Configure jira-cli

1. **Get a JIRA API Token:**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new API token
   - Copy the token

2. **Set environment variable:**
   ```bash
   export JIRA_API_TOKEN="your-api-token"
   ```
   The collector scripts also use this token for the Jira REST API, because jira-cli does not expose the changelog. The changelog carries the exact status transition and the assignee change. Without it, movement falls back to the status category date and comments only, so an item can look older than it is.

3. **Initialize jira-cli for HyperFleet:**
   ```bash
   jira init --installation cloud \
     --server https://redhat.atlassian.net \
     --login your-email@redhat.com \
     --auth-type basic \
     --project HYPERFLEET
   ```
   It will prompt you for the API token and default board selection.

4. **Verify setup:**
   ```bash
   jira me
   jira issue list
   ```

## Installation

1. **Add the HyperFleet marketplace (if not already added):**
   ```
   /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. **Install the JIRA plugin:**
   ```
   /plugin install hyperfleet-jira@hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Commands

Commands are namespaced by plugin: invoke them as `/hyperfleet-jira:<command>`. The examples below spell the namespace out, because a command such as `/sprint-status` is common enough to collide with another installed plugin.

#### `/hyperfleet-jira:my-sprint`
Shows your current sprint at a glance:
```text
/hyperfleet-jira:my-sprint
```
Output includes:
- Sprint name and days remaining
- Your tickets grouped by status
- Story points summary
- Blockers or high-priority items

#### `/hyperfleet-jira:my-tasks`
Lists all your assigned tickets:
```text
/hyperfleet-jira:my-tasks
```

#### `/hyperfleet-jira:new-comments`
Find tickets with recent comments:
```text
/hyperfleet-jira:new-comments
```

#### `/hyperfleet-jira:sprint-status` (Team Leads)
Comprehensive sprint health report:
```text
/hyperfleet-jira:sprint-status
/hyperfleet-jira:sprint-status HF    # Specific project
```
Output includes:
- Progress by status, by story points and by item count
- Blocked items, highest-priority open items, and stale in-progress work
- Team workload distribution, including unassigned work
- Carry-over totals (items, story points, and reasons) and a capacity projection from the previous sprint's pace
- Every ticket key as a link, in every section, including the blocker keys inside a line
- The pull requests of the items in `Review`, read from Jira's development panel: the GitHub app's `dev-status` record for every repository, plus any link attached by hand

The numbers come from `scripts/sprint_status.py` (`--format json` or the rendered `--format markdown`), not from hand-written JQL: story points need `issue view --raw`, and `issue list` truncates at 100 issues without saying so.

Options: `--today YYYY-MM-DD` for a reproducible run, `--sprint <id>` for another sprint, `--stale-days`, `--blocker-priority`, `--link-style markdown|slack|bare`, `--no-baseline`, `--no-prs`.

These rules decide what the output is worth:

- **A pull request belongs to the ticket its title names**, and only to it. Jira attaches a pull request to every ticket its title mentions, so `architecture#255`, titled `HYPERFLEET-1636`, is `HYPERFLEET-1636`'s pull request and never `HYPERFLEET-1669`'s, even when the panel shows it on both. A link titled for another ticket, or for no ticket at all, is not printed on the ticket's line: the reviewer named there would open someone else's diff, and two stalls would read as one shared blocker.
- **Ownership is per pull request, by its own title.** A ticket can own several - the same work opened in two repositories, or a follow-up after a merge - and each is listed as its own. The `+N` on a long list is a width limit, not a ranking, and the report never asks anyone which one is the real work.
- **"No link" is not "no pull request".** The report reads Jira, not GitHub: an empty segment means no record in Jira, and the recommendation is about the link - attach the pull request, or move the ticket back. A lookup that was skipped, unavailable or failed leaves the ask neutral: an empty list from a read that did not answer is unknown, not none.
- **The state rides along when Jira reports one.** The panel has two kinds of record: the GitHub app's `dev-status` (every repository, with a state) and hand-attached remote links (no state). Both are read and deduplicated, so `PR [#181](url) (merged)` and `PR [#177](url)` stay distinguishable - one is a ticket waiting for its status, the other one waiting for a reviewer. `--no-prs` skips the lookup; a failed read is reported as a partial signal instead of a silent gap.

#### `/hyperfleet-jira:sprint-pulse-check` (Team Leads)
Nudge queue for the large items, run a couple of times per week:
```text
/hyperfleet-jira:sprint-pulse-check
/hyperfleet-jira:sprint-pulse-check HF    # Specific project
```
Output includes:
- Items >= 5 SP ranked by days without movement (last status change, last human comment, or assignment to the current owner)
- The specific ask per item, pointing at the blocker or the reviewer when the delay is not the owner's
- Assignment gap: large items with no owner, and which of them block other work
- Concentration: owners holding more than one large item
- The pull request of an item in `Review`, inside the ask, under the same ownership rule as `/sprint-status`
- The reviewers the ask names, never the author: `dev-status` reports every requested reviewer, and the ask names all of them: `Ask Tirth and Rafael to approve or reject PR [#257](url)`. Naming one would decide who reviews, and naming the assignee would point at the person who wrote the diff. The author, a reviewer who already approved and Jira's `User ` placeholder are dropped; a hand-attached link with no reviewer list falls back to `Ask a reviewer` instead of guessing.

#### `/hyperfleet-jira:team-weekly-update` (Team Leads)
Weekly progress report for team updates:
```text
/hyperfleet-jira:team-weekly-update                    # All teams in HYPERFLEET
/hyperfleet-jira:team-weekly-update HYPERFLEET         # Specific project
/hyperfleet-jira:team-weekly-update HYPERFLEET 6278    # Specific team
/hyperfleet-jira:team-weekly-update "" 6278            # Default project with team filter
```
Output includes:
- Closed issues from the last 7 days (Story, Task, Bug)
- Grouped by activity type → Epic → Story/Task/Bug hierarchy
- Summary statistics by activity type
- Epic status tracking
- Issues without parent epics highlighted

#### `/hyperfleet-jira:triage` (Team Leads)
Audit tickets for quality:
```text
/hyperfleet-jira:triage
/hyperfleet-jira:triage backlog    # Check backlog instead of sprint
```
Checks for:
- Missing story points
- Empty descriptions
- Unassigned tickets
- Missing components
- Stale tickets (no updates in 7+ days)

### Skills (Automatic)

#### Ticket Creation
Just ask naturally to create tickets:
- "Create a ticket for [feature/bug/task]"
- "I need a story for implementing X"
- "Can you create a JIRA ticket for this work?"

The creator ensures:
- Duplicate check before creating
- **What/Why/Acceptance Criteria** structure, plus type-specific sections for Bugs, Epics, and Spikes
- Story points via `jira-story-pointer` skill
- Activity type via Sankey capacity allocation flow
- Component, parent epic (Tasks and Bugs may use the `no-epic-needed` label instead), and an explicit priority
- Validation gate — blocks creation until all required fields are set
- Post-creation check that the fields actually landed on the ticket

#### Ticket Triage
Just ask naturally:
- "Is TICKET-123 ready for development?"
- "Does this ticket have enough information?"
- "Check if TICKET-456 is well-defined"

#### Story Point Estimation
Ask for estimates:
- "How many story points should TICKET-123 be?"
- "Estimate this ticket"
- "What should we point TICKET-456 at?"

The estimator analyzes:
- Scope and complexity
- Dependencies and risks
- Similar completed tickets
- Team velocity patterns

#### Ticket Implementation Validation
A skill, so it is triggered by asking rather than by a slash command:
```text
Is HYPERFLEET-123 implemented?
Is HYPERFLEET-123 implemented in the remote repo?   # infers the repo from the ticket
```

Generates an acceptance report with:
- Completion percentage
- Implemented items with file:line references
- Partially implemented and missing items
- Manual verification needed
- Recommended next actions

## Story Points Reference

| Points | Meaning | Example |
|--------|---------|---------|
| 0 | Tracking Only | Quick/easy task with stakeholder value |
| 1 | Trivial | Config change, typo fix |
| 3 | Straightforward | Time consuming but fairly straightforward |
| 5 | Medium | Requires investigation, design, collaboration |
| 8 | Large | Significant work, dependencies. Design doc required |
| 13 | Too Large | Must be broken down into smaller stories |

See [jira-story-pointer SKILL.md](./skills/jira-story-pointer/SKILL.md) for canonical definitions and estimation methodology.

## Troubleshooting

### "jira: command not found"
Install jira-cli following the Prerequisites section above.

### "Error: Could not fetch sprint"
1. Check jira-cli is configured: `jira init`
2. Verify API token is set: `echo $JIRA_API_TOKEN`
3. Test connection: `jira issue list`

### "No issues found"
- Ensure you're in the correct project
- Check your JIRA permissions
- Verify JQL syntax if using custom queries

### Custom Fields Not Working
If story points or other custom fields fail:
1. Re-run `jira init` to refresh field mappings
2. Check your JIRA instance's custom field names
3. See [jira-cli custom fields docs](https://github.com/ankitpokhrel/jira-cli#setting-custom-fields)

## Contributing

See the main [HyperFleet Claude Plugins README](../README.md) for contribution guidelines.

## Maintainers

- Ciaran Roche (@ciaranRoche)
