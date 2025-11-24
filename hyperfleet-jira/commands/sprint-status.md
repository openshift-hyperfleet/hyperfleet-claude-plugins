---
description: Sprint health overview for team leads - progress, blockers, and risks
allowed-tools: Bash
argument-hint: [project-key]
---

# Sprint Status (Team Lead View)

Comprehensive sprint health report for team leads and scrum masters.

## Arguments
- `$1` (optional): Project key (e.g., HYPERFLEET). If not provided, uses HYPERFLEET as default.

## Instructions

1. **Get current sprint info:**
   ```bash
   jira sprint list --current -p HYPERFLEET --plain 2>/dev/null
   ```

2. **Get all tickets in current sprint:**
   ```bash
   jira sprint list --current -p HYPERFLEET --plain 2>/dev/null
   ```

3. **Get tickets by status - To Do:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND status = 'To Do'" --created-after "-30d" --plain 2>/dev/null
   ```

4. **Get tickets by status - In Progress:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND status = 'In Progress'" --plain 2>/dev/null
   ```

5. **Get tickets by status - Done (this sprint):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND status = Done" --updated-after "-14d" --plain 2>/dev/null
   ```

6. **Find blockers (high priority not done):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND priority = Highest AND status != Done" --plain 2>/dev/null
   jira issue list -q"project = HYPERFLEET AND priority = High AND status != Done" --plain 2>/dev/null
   ```

7. **Find unassigned tickets:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND assignee is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

## Output Format

### Sprint Overview
```
Sprint: [Sprint Name]
Duration: [Start Date] - [End Date]
Days Remaining: X days
```

### Progress Summary
| Status | Count | Story Points |
|--------|-------|--------------|
| To Do | X | X pts |
| In Progress | X | X pts |
| Done | X | X pts |
| **Total** | **X** | **X pts** |

Progress: [=========>    ] 65% complete

### Risk Assessment

#### Blockers & High Priority
- TICKET-1: [Summary] - Assigned to [Name] - [X days in status]
- TICKET-2: [Summary] - **UNASSIGNED**

#### At-Risk Items
- Tickets in progress > 5 days without update
- Tickets without story points
- Unassigned tickets

#### Carry-Over Risk
- Tickets likely to spill: X
- Story points at risk: X

### Team Workload
| Team Member | To Do | In Progress | Done |
|-------------|-------|-------------|------|
| [Name] | X | X | X |

### Recommendations
- List actionable items for the team lead
- Highlight tickets needing attention
- Suggest re-assignments if workload is unbalanced
