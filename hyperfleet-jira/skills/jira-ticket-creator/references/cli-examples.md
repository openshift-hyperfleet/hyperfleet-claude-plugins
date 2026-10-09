# JIRA CLI Ticket Creation Examples

Every Story, Task, and Bug command passes `--priority`, `-C`, and `-P EPIC-KEY`. A Task or Bug with no applicable epic passes `-l no-epic-needed` instead of `-P`; a Story always needs `-P`. Epics take neither. Jira has no default priority, so leaving out `--priority` creates the ticket as `Undefined`.

## Creating a Story

```bash
# 1. Save description to temporary file (use Markdown)
cat > /tmp/story-description.txt << 'EOF'
### What

Description of what needs to be done.

### Why

- Reason 1
- Reason 2

### Acceptance Criteria

- Criterion 1
- Criterion 2
- Criterion 3

### Technical Notes

- Use `package-name` for implementation
- Configuration in `/path/to/config`
EOF

# 2. Create story with all fields
jira issue create --project HYPERFLEET --type Story \
  --summary "Story Title (< 100 chars)" \
  --custom story-points=5 \
  --custom activity-type="Product / Portfolio Work" \
  --priority Normal \
  -C "Sentinel" \
  -l feature \
  -P HYPERFLEET-100 \
  --no-input \
  -b "$(cat /tmp/story-description.txt)"

# Note: -C = component, -l = label (repeatable), -P = parent epic
```

## Creating a Task

```bash
cat > /tmp/task-description.txt << 'EOF'
### What

Task description.

### Why

Justification.

### Acceptance Criteria

- Criterion 1
- Criterion 2
EOF

jira issue create --project HYPERFLEET --type Task \
  --summary "Task Title" \
  --custom story-points=3 \
  --custom activity-type="Future Sustainability" \
  --priority Normal \
  -C "CICD" \
  -l no-epic-needed \
  --no-input \
  -b "$(cat /tmp/task-description.txt)"

# no-epic-needed: the user confirmed no epic applies (Tasks and Bugs only). Otherwise use -P EPIC-KEY
```

## Creating a Bug

```bash
cat > /tmp/bug-description.txt << 'EOF'
### What

Description of the bug.

### Steps to Reproduce

1. Step one
2. Step two
3. Observe the failure

### Expected Behavior

What should happen.

### Actual Behavior

What happens instead, including the error message if there is one.

### Impact

Who is affected and how (users, CI, other teams), and whether there is a workaround.

### Why

Why this needs to be fixed now.

### Acceptance Criteria

- Root cause identified and fixed
- Regression test added
- Fix verified in the environment where the bug was found
EOF

jira issue create --project HYPERFLEET --type Bug \
  --summary "Bug: Brief Description" \
  --custom story-points=3 \
  --custom activity-type="Quality / Stability / Reliability" \
  --priority Major \
  -C "API" \
  -P HYPERFLEET-100 \
  --no-input \
  -b "$(cat /tmp/bug-description.txt)"

# Choose the priority from the bug's impact; do not default to Normal
```

## Creating a Spike

A spike is a Story whose summary starts with `[SPIKE]`. Its acceptance criteria name the deliverable, and the Time Box caps the effort.

```bash
cat > /tmp/spike-description.txt << 'EOF'
### What

Research question: the question this spike answers.

### Why

The decision or work this unblocks.

### Acceptance Criteria

- Deliverable published: ADR, design doc, POC, or written recommendation (say which and where)
- Options considered and trade-offs documented
- Follow-up tickets filed for the chosen approach

### Time Box

N days. If the question is not answered by then, report findings so far and re-plan.
EOF

jira issue create --project HYPERFLEET --type Story \
  --summary "[SPIKE] Choose the approach for X" \
  --custom story-points=3 \
  --custom activity-type="Future Sustainability" \
  --priority Normal \
  -C "Applier" -C "Architecture" \
  -P HYPERFLEET-100 \
  --no-input \
  -b "$(cat /tmp/spike-description.txt)"

# A design spike in the Applier domain gets Applier + Architecture (one domain + one cross-cutting component)
```

## Creating an Epic

Epic Name (`customfield_10011`) is optional on Jira Cloud, so there is no need to pass `--custom epic-name`.

```bash
cat > /tmp/epic-description.txt << 'EOF'
### Goal

What the epic delivers when it is complete.

### Why

Business value and the problem it solves.

### Scope

**In Scope:**
- Item 1
- Item 2

**Out of Scope:**
- Item 3

### Success Criteria

- Criterion 1
- Criterion 2

### Dependencies

- Other epics, teams, or external work this depends on

### Risks

- Known risks and how they will be handled
EOF

jira issue create --project HYPERFLEET --type Epic \
  --summary "Epic Title" \
  --custom activity-type="Product / Portfolio Work" \
  --priority Normal \
  -C "Operator" \
  --no-input \
  -b "$(cat /tmp/epic-description.txt)"

# Story points are optional for epics; component and activity type SHOULD be set
```

## Description Templates (Markdown)

The Bug, Spike, and Epic templates are in the CLI examples above.

### Story/Task Template

```markdown
### What

Brief description paragraph.

Detailed explanation paragraph (optional).

### Why

- Reason 1
- Reason 2
- Reason 3

### Acceptance Criteria

- `component` created/implemented/configured
- Feature X works correctly:
  - Detail 1
  - Detail 2
- Tests achieve >80% coverage
- Documentation updated

### Technical Notes

- Use `package-name` for implementation
- Configuration in `/path/to/config.yaml`
- Important consideration

### Out of Scope

- Item not included
- Another exclusion
```

## Linking Tickets (Blocks Relationship)

```bash
# NEW_TICKET blocks EXISTING_TICKET
jira issue link HYPERFLEET-NEW HYPERFLEET-EXISTING "Blocks"

# EXISTING_TICKET blocks NEW_TICKET (new ticket is blocked by existing)
jira issue link HYPERFLEET-EXISTING HYPERFLEET-NEW "Blocks"
```

The first argument is always the outward (blocking) ticket. Getting the order wrong inverts the link direction.

## Important Reminders

- Fenced code blocks (triple backticks) work correctly via CLI
- Prefer `-b "$(cat /tmp/file.md)"` consistently for all issue types
