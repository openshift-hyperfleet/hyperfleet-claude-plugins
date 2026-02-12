---
description: Audit sprint tickets for triage - required fields, components, and duplicate detection
allowed-tools: Bash
argument-hint: [scope: sprint|backlog|all]
---

# Triage Check

Audit JIRA tickets for sprint readiness, including required fields, valid components, and potential duplicates.

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

2. **CRITICAL - Check for potential duplicates:**
   ```bash
   # Search backlog for similar titles - run for each ticket being triaged
   jira issue list -q"project = HYPERFLEET AND status != Done AND summary ~ 'keyword'" --plain 2>/dev/null
   ```

3. **Find tickets without story points:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND 'Story Points' is EMPTY AND sprint in openSprints() AND issuetype in (Story, Task, Bug)" --plain 2>/dev/null
   ```

4. **Find tickets with minimal description:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND sprint in openSprints() AND description is EMPTY" --plain 2>/dev/null
   ```

5. **Find tickets without valid components (must be Adapter, API, Architecture, or Sentinel):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND component is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

   Also check for invalid components:
   ```bash
   jira issue list -q"project = HYPERFLEET AND sprint in openSprints() AND component not in (Adapter, API, Architecture, Sentinel)" --plain 2>/dev/null
   ```

6. **Find tickets without Activity Type:**
   ```bash
   jira issue list -q"project = HYPERFLEET AND 'Activity Type' is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

7. **Find stale tickets (no updates in 7+ days):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND sprint in openSprints() AND status != Done AND updated < -7d" --plain 2>/dev/null
   ```

8. **Find tickets without labels (recommended):**
   ```bash
   jira issue list -q"project = HYPERFLEET AND labels is EMPTY AND sprint in openSprints()" --plain 2>/dev/null
   ```

9. **For detailed ticket inspection (check Title, Acceptance Criteria):**
   ```bash
   jira issue view TICKET-KEY --plain 2>/dev/null
   ```

   When inspecting individual tickets, verify:
   - **Title**: Clear, actionable, under 100 characters
   - **Acceptance Criteria**: At least 2 clear, testable criteria in description
   - **No ambiguous language**: Check for "maybe", "probably", "TBD", "possibly"

## Output Format

### Triage Report

#### CRITICAL: Potential Duplicates
| Ticket | Summary | Similar To | Similarity |
|--------|---------|------------|------------|
| TICKET-1 | [Summary] | TICKET-X | High/Medium |

**Action Required:** Review and close duplicates or link as related.

---

#### Missing Story Points
| Ticket | Summary | Type |
|--------|---------|------|
| TICKET-1 | [Summary] | Story |

**Action Required:** These tickets need estimation before sprint planning.

---

#### Missing/Inadequate Description
| Ticket | Summary | Description Length |
|--------|---------|-------------------|
| TICKET-1 | [Summary] | Empty |
| TICKET-2 | [Summary] | < 50 chars |

**Action Required:** Add detailed description with context and acceptance criteria.

---

#### Invalid or Missing Components
| Ticket | Summary | Current Component |
|--------|---------|-------------------|
| TICKET-1 | [Summary] | None |
| TICKET-2 | [Summary] | InvalidComponent |

**Valid Components:** Adapter, API, Architecture, Sentinel

**Action Required:** Assign valid component for tracking.

---

#### Missing Activity Type
| Ticket | Summary | Type |
|--------|---------|------|
| TICKET-1 | [Summary] | Story |

**Valid Activity Types:** Associate Wellness & Development, Incidents & Support, Security & Compliance, Quality / Stability / Reliability, Future Sustainability, Product / Portfolio Work

**Action Required:** Set Activity Type for capacity planning.

---

#### Stale Tickets (No Update 7+ Days)
| Ticket | Summary | Status | Last Updated |
|--------|---------|--------|--------------|

**Action Required:** Update status or add comment on progress.

---

### Summary Score (6 Required Fields)

| Check | Pass | Fail | Score |
|-------|------|------|-------|
| Title | X | X | X% |
| Description | X | X | X% |
| Acceptance Criteria | X | X | X% |
| Story Points | X | X | X% |
| Component (valid) | X | X | X% |
| Activity Type | X | X | X% |
| **Overall** | | | **X%** |

### Quality Checks

| Check | Pass | Fail |
|-------|------|------|
| **Not Duplicate (CRITICAL)** | X | X |
| No Ambiguous Language | X | X |
| Freshness (updated < 7d) | X | X |

### Sprint Readiness
- **Ready for Sprint:** X tickets
- **Needs Work:** X tickets
- **Critical Issues:** X tickets

### Top Priority Fixes
1. [Most critical triage issue - duplicates are highest priority]
2. [Second priority]
3. [Third priority]
