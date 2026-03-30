# HyperFleet JIRA Plugin

A Claude Code plugin that integrates JIRA with your development workflow using [jira-cli](https://github.com/ankitpokhrel/jira-cli).

## Features

### For Engineers
- **`/my-sprint`** - View current sprint and your assigned tickets
- **`/my-tasks`** - List all your assigned tasks across projects
- **`/new-comments`** - Find tickets with comments you may have missed

### For Team Leads
- **`/sprint-status`** - Comprehensive sprint health overview
- **`/team-weekly-update`** - Weekly team progress report grouped by activity type and epic
- **`/triage`** - Audit tickets for missing fields and quality issues

### Skills (Auto-Activated)
- **JIRA Ticket Creator** - Creates well-structured tickets with What/Why/Acceptance Criteria
- **JIRA Triage** - Validates ticket quality when you ask about readiness
- **Story Point Estimator** - Helps estimate tickets using complexity analysis
- **Is Ticket Implemented?** - Validates whether a ticket's requirements are implemented in the codebase

## Prerequisites

### Install jira-cli

**macOS (Homebrew):**
```bash
brew install ankitpokhrel/jira-cli/jira-cli
```

**Linux:**
```bash
# Download from releases
curl -LO https://github.com/ankitpokhrel/jira-cli/releases/latest/download/jira_linux_amd64.tar.gz
tar -xzf jira_linux_amd64.tar.gz
sudo mv jira /usr/local/bin/
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
   /plugin install hyperfleet-jira@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Commands

#### `/my-sprint`
Shows your current sprint at a glance:
```
/my-sprint
```
Output includes:
- Sprint name and days remaining
- Your tickets grouped by status
- Story points summary
- Blockers or high-priority items

#### `/my-tasks`
Lists all your assigned tickets:
```
/my-tasks
```

#### `/new-comments`
Find tickets with recent comments:
```
/new-comments
```

#### `/sprint-status` (Team Leads)
Comprehensive sprint health report:
```
/sprint-status
/sprint-status HF    # Specific project
```
Output includes:
- Progress by status and story points
- Blockers and at-risk items
- Team workload distribution
- Carry-over risk assessment

#### `/team-weekly-update` (Team Leads)
Weekly progress report for team updates:
```
/team-weekly-update                    # All teams in HYPERFLEET
/team-weekly-update HYPERFLEET         # Specific project
/team-weekly-update HYPERFLEET 6278    # Specific team
/team-weekly-update "" 6278            # Default project with team filter
```
Output includes:
- Closed issues from the last 7 days (Story, Task, Bug)
- Grouped by activity type → Epic → Story/Task/Bug hierarchy
- Summary statistics by activity type
- Epic status tracking
- Issues without parent epics highlighted

#### `/triage` (Team Leads)
Audit tickets for quality:
```
/triage
/triage backlog    # Check backlog instead of sprint
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
- **What/Why/Acceptance Criteria** structure
- Story points assignment
- Activity type categorization
- All required fields populated

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
Check if a ticket's requirements are implemented:
```
/is-ticket-implemented HYPERFLEET-123          # local codebase
/is-ticket-implemented HYPERFLEET-123 github   # remote (infers repo from ticket)
```
Or ask naturally: "Is HYPERFLEET-123 implemented?" / "Check if this ticket is done"

Generates an acceptance report with:
- Completion percentage
- Implemented items with file:line references
- Partially implemented and missing items
- Manual verification needed
- Recommended next actions

## Story Points Reference

| Points | Meaning | Example |
|--------|---------|---------|
| 1 | Trivial | Config change, typo fix |
| 2 | Small | Well-understood, few files |
| 3 | Medium-Small | Clear scope, limited testing |
| 5 | Medium | Multiple components |
| 8 | Large | Significant work, dependencies |
| 13 | Very Large | Consider breaking down |

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
