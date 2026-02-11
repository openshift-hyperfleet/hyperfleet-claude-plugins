---
description: Audit sprint tickets for missing required fields and quality issues
allowed-tools: Bash
argument-hint: [scope: sprint|backlog|all]
---

# Hygiene Check

Audit JIRA tickets for missing required fields and quality issues.

## Arguments
- `$1` (optional): Scope of check
  - `sprint` (default): Current sprint tickets only
  - `backlog`: Backlog items
  - `all`: All recent tickets

## Instructions

1. **Get tickets to audit (current sprint by default):**
   ```bash
   jira sprint list --current -p HYPERFLEET --raw 2>/dev/null
   ```

2. **Find tickets without story points:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND 'Story Points' is EMPTY AND sprint in openSprints() AND issuetype in (Story, Task, Bug)" --plain 2>/dev/null
   ```

3. **Find tickets with minimal description:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND sprint in openSprints() AND description is EMPTY" --plain 2>/dev/null
   ```

4. **Find unassigned tickets in sprint:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND assignee is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

5. **Find tickets without components:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND component is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

6. **Find stale tickets (no updates in 7+ days):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND sprint in openSprints() AND status != Done AND updated < -7d" --plain 2>/dev/null
   ```

7. **Find tickets without labels:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND labels is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

8. **For detailed ticket inspection, view individual tickets:**
   ```bash
   jira issue view TICKET-KEY --plain 2>/dev/null
   ```

## Output Format

### Hygiene Report

#### Missing Story Points
| Ticket | Summary | Type | Assignee |
|--------|---------|------|----------|
| TICKET-1 | [Summary] | Story | [Name] |

**Action Required:** These tickets need estimation before sprint planning.

---

#### Missing/Inadequate Description
| Ticket | Summary | Description Length |
|--------|---------|-------------------|
| TICKET-1 | [Summary] | Empty |
| TICKET-2 | [Summary] | < 50 chars |

**Action Required:** Add detailed description with context and acceptance criteria.

---

#### Unassigned Tickets
| Ticket | Summary | Priority | Days in Sprint |
|--------|---------|----------|----------------|

**Action Required:** Assign owner or move to backlog.

---

#### Missing Components
| Ticket | Summary |
|--------|---------|

**Action Required:** Assign appropriate component for tracking.

---

#### Stale Tickets (No Update 7+ Days)
| Ticket | Summary | Status | Last Updated |
|--------|---------|--------|--------------|

**Action Required:** Update status or add comment on progress.

---

### Summary Score

| Check | Pass | Fail | Score |
|-------|------|------|-------|
| Story Points | X | X | X% |
| Description | X | X | X% |
| Assignee | X | X | X% |
| Component | X | X | X% |
| Freshness | X | X | X% |
| **Overall** | | | **X%** |

### Sprint Readiness
- **Ready for Sprint:** X tickets
- **Needs Work:** X tickets
- **Critical Issues:** X tickets

### Top Priority Fixes
1. [Most critical hygiene issue]
2. [Second priority]
3. [Third priority]
