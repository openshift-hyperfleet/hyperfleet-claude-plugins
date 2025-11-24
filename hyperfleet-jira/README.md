# HyperFleet JIRA Plugin

A Claude Code plugin that integrates JIRA with your development workflow using [jira-cli](https://github.com/ankitpokhrel/jira-cli).

## Features

### For Engineers
- **`/my-sprint`** - View current sprint and your assigned tickets
- **`/my-tasks`** - List all your assigned tasks across projects
- **`/new-comments`** - Find tickets with comments you may have missed

### For Team Leads
- **`/sprint-status`** - Comprehensive sprint health overview
- **`/hygiene-check`** - Audit tickets for missing fields and quality issues

### Skills (Auto-Activated)
- **JIRA Hygiene Checker** - Validates ticket quality when you ask about readiness
- **Story Point Estimator** - Helps estimate tickets using complexity analysis

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

3. **Initialize jira-cli:**
   ```bash
   jira init
   ```
   - Select "Cloud" for Atlassian Cloud
   - Enter your JIRA URL (e.g., `https://yourcompany.atlassian.net`)
   - Enter your email
   - Select your default project

4. **Verify setup:**
   ```bash
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

#### `/hygiene-check` (Team Leads)
Audit tickets for quality:
```
/hygiene-check
/hygiene-check backlog    # Check backlog instead of sprint
```
Checks for:
- Missing story points
- Empty descriptions
- Unassigned tickets
- Missing components
- Stale tickets (no updates in 7+ days)

### Skills (Automatic)

#### Ticket Hygiene
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

- Alex Vulaj (@AlexVulaj)
- Ciaran Roche (@ciaranRoche)
