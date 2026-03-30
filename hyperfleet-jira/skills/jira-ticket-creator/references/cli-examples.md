# JIRA CLI Ticket Creation Examples

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
  --no-input \
  -b "$(cat /tmp/task-description.txt)"
```

## Creating an Epic

**CRITICAL: Epics require the Epic Name field!**

```bash
cat > /tmp/epic-description.txt << 'EOF'
# Epic Full Title

### Overview

Overview paragraph.

### What

- Deliverable 1
- Deliverable 2

### Why

Explanation.

### Success Criteria

- Criterion 1
- Criterion 2
EOF

# Create epic with Epic Name (required field!)
jira issue create --project HYPERFLEET --type Epic \
  --summary "Epic: Full Title Here" \
  --custom epic-name="Short Name" \
  -b "$(cat /tmp/epic-description.txt)" \
  --no-input

# Note: Use --custom epic-name="Name" (not epicName or customfield_12311141)
```

## Creating a Bug

```bash
cat > /tmp/bug-description.txt << 'EOF'
### What

Description of the bug and its impact.

### Why

Why this needs to be fixed urgently.

### Acceptance Criteria

- Bug is reproducible
- Root cause identified
- Fix is verified
- Regression test added
EOF

jira issue create --project HYPERFLEET --type Bug \
  --summary "Bug: Brief Description" \
  --custom story-points=5 \
  --custom activity-type="Quality / Stability / Reliability" \
  --priority Major \
  -C "API" \
  --no-input \
  -b "$(cat /tmp/bug-description.txt)"
```

## Description Templates (Markdown)

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

### Epic Template

```markdown
# Epic Title

### Overview

Brief overview paragraph.

### What

- Key deliverable 1
- Key deliverable 2
  - Sub-item
- Key deliverable 3

### Why

Explanation of business value and impact.

### Scope

**In Scope:**
- Item 1
- Item 2

**Out of Scope:**
- Item 3
- Item 4

### Success Criteria

- Criterion 1
- Criterion 2
- Criterion 3
```

## Important Reminders

- Fenced code blocks (triple backticks) work correctly via CLI
- Prefer `-b "$(cat /tmp/file.md)"` consistently for all issue types
