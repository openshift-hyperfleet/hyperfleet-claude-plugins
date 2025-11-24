---
description: Show current sprint and your assigned tasks
allowed-tools: Bash
---

# My Sprint

Show the current sprint information and the user's assigned tickets.

## Instructions

1. **Get current sprint overview:**
   ```bash
   jira sprint list --current --plain 2>/dev/null || echo "Error: Could not fetch sprint. Is jira-cli configured?"
   ```

2. **Get user's assigned tickets in current sprint:**
   ```bash
   jira sprint list --current -a$(jira me) --plain 2>/dev/null
   ```

3. **Get ticket status breakdown:**
   ```bash
   jira issue list -a$(jira me) --created-after "-30d" --plain 2>/dev/null
   ```

## Output Format

Summarize the results in a clear format:

### Sprint Overview
- Sprint name and goal (if available)
- Days remaining in sprint
- Sprint progress indicator

### Your Tickets
Group by status:
- **To Do**: List tickets not yet started
- **In Progress**: List tickets being worked on
- **In Review/QA**: List tickets awaiting review
- **Done**: List completed tickets

### Summary
- Total tickets assigned: X
- Story points assigned: X (if visible)
- Any blockers or high-priority items to highlight

If jira-cli is not installed or configured, inform the user they need to:
1. Install jira-cli: `brew install ankitpokhrel/jira-cli/jira-cli`
2. Configure it: `jira init`
