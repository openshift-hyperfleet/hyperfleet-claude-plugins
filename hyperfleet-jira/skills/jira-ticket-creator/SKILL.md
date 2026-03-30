---
name: jira-ticket-creator
description: Creates well-structured JIRA tickets in the HYPERFLEET project with required What/Why/Acceptance Criteria for all tickets, and required story points/activity type for Stories/Tasks/Bugs. Activates when users ask to create a ticket, story, task, or epic.
---

# JIRA Ticket Creator Skill

## Language

All JIRA ticket content — summaries, descriptions, comments, and acceptance criteria — MUST be written in **English**, regardless of the language the user is communicating in.

## Formatting

The `jira-cli` accepts **Markdown** and converts it to ADF (Atlassian Document Format) for JIRA Cloud. Standard Markdown works correctly — headers, bullets, bold, inline code, fenced code blocks, and curly braces all render as expected.

## References

Load these files as needed:

- [references/formatting.md](references/formatting.md) — Formatting rules and known issues
- [references/cli-examples.md](references/cli-examples.md) — CLI commands and description templates for each ticket type
- [references/pitfalls.md](references/pitfalls.md) — Common pitfalls, troubleshooting, and best practices
- [references/activity-types.md](references/activity-types.md) — Activity type definitions and Sankey capacity allocation flow

## When to Use This Skill

Activate this skill when the user:
- Asks to "create a ticket" or "create a story/task/epic"
- Says "I need a JIRA ticket for..."
- Asks "can you create a ticket for [feature/bug/task]?"
- Wants to document work as a JIRA issue
- Asks to "file a ticket" or "add a story"
- Provides work that needs to be tracked

## Required Ticket Structure

Every ticket created MUST include:

### 1. What (Required)

Clear, concise description of what needs to be done. Should be 2-4 sentences explaining the work.

### 2. Why (Required)

Business justification and context. Explain:
- Why this work matters
- Who benefits (users, team, system)
- What problem it solves or value it delivers

### 3. Acceptance Criteria (Required)

Minimum 2-3 clear, testable criteria that define "done":
- Must be objective and verifiable
- Should cover functional requirements and edge cases
- Use bullet format with specific details

### 4. Story Points (Required for Stories/Tasks/Bugs)

All Stories, Tasks, and Bugs must have story points (scale: 0, 1, 3, 5, 8, 13).

### 5. Priority (Required)

Set priority via CLI using `--priority`:
- `Blocker` - Blocks development/testing, must be fixed immediately
- `Critical` - Crashes, data loss, severe memory leak
- `Major` - Major loss of function
- `Normal` - Default priority for most work
- `Minor` - Minor loss of function, easy workaround

### 6. Activity Type (Required for Stories/Tasks/Bugs)

See [references/activity-types.md](references/activity-types.md) for the full definition and Sankey capacity allocation flow.

### 7. Optional Context

Additional sections can be added as needed:
- **Technical Notes**: High-level implementation plan
- **Dependencies**: Linked tickets or external dependencies
- **Out of Scope**: Explicitly state what's NOT included

## Ticket Creation Workflow

### Step 1: Gather Requirements

Ask the user clarifying questions if needed:
- What type of ticket? (Epic, Story, Task, Bug)
- What needs to be done? (What)
- Why is this important? (Why)
- How will we know it's done? (Acceptance Criteria)
- How complex/large is this work? (for story points)
- What category of work is this? (for activity type)

### Step 2: Check for Duplicates

Before creating, search for existing tickets with similar scope:

```bash
jira issue list -q "project = HYPERFLEET AND summary ~ 'key words from title' AND statusCategory != Done" --plain --columns key,summary,status
```

Extract 2-3 key words from the intended title for the search. Evaluate the results:

- **No results** → proceed to Step 3
- **Similar tickets found** → show the candidates to the user with their key, summary, status, and link. Ask:
  - Is this a duplicate? (abandon creation)
  - Should the new ticket be linked to an existing one? (proceed and link)
  - Is it different enough to create separately? (proceed normally)

**Never block automatically** — always let the user decide.

### Step 3: Create Description File

Create a temporary file with the description in **Markdown**. The `jira-cli` converts Markdown to ADF automatically.

See [references/cli-examples.md](references/cli-examples.md) for description templates per ticket type.

### Step 4: Determine Story Points

For Stories, Tasks, and Bugs: invoke the `jira-story-pointer` skill via the Skill tool. Pass the ticket context (description, acceptance criteria, type) as the argument. The skill returns a recommended value — use it directly.

Valid story points: 0, 1, 3, 5, 8, 13. Tickets estimated at 13 should be split.

### Step 5: Assign Activity Type

Follow the Sankey flow defined in [references/activity-types.md](references/activity-types.md) — evaluate top-down, first match wins.

### Step 6: Validate Required Fields

**Do NOT create the ticket until all required fields are set.** For Stories, Tasks, and Bugs, verify:

- [ ] **Story Points** — must have a value from Step 4. If `jira-story-pointer` was not invoked, go back and invoke it now
- [ ] **Activity Type** — must have a value from Step 5
- [ ] **Priority** — must be set (default: `Normal`)

If any field is missing, resolve it before proceeding.

### Step 7: Create the Ticket via jira-cli

See [references/cli-examples.md](references/cli-examples.md) for complete CLI commands for each ticket type (Story, Task, Epic, Bug).

Key patterns:
- Always save descriptions to temporary files first
- Use `-b "$(cat /tmp/file.txt)"` to pass descriptions
- Use `--no-input` for non-interactive creation
- Use `--custom story-points=X` and `--custom activity-type="..."` for custom fields

### Step 8: Post-Creation Steps

All fields can be set via CLI during creation:
- **Link to Epic**: use `-P EPIC-KEY` (or `--parent EPIC-KEY`)
- **Add Labels**: use `-l label1 -l label2`
- **Add Component**: use `-C ComponentName`
- **Code blocks**: use fenced code blocks (triple backticks) in the description — they render correctly via CLI

### Step 9: Verify and Return Details

```bash
jira issue view HYPERFLEET-XXX --plain
```

Return to user:
- Ticket key (e.g., HYPERFLEET-123)
- Link: https://redhat.atlassian.net/browse/HYPERFLEET-123
- Summary of what was created
- **List of manual steps needed**

## Output Format

When creating a ticket, provide this output to the user:

```
### Ticket Created: HYPERFLEET-XXX

**Type:** [Story/Task/Epic/Bug]
**Summary:** [Title]
**Link:** https://redhat.atlassian.net/browse/HYPERFLEET-XXX

---

#### Description Structure

**What:**
[What description]

**Why:**
[Why description]

**Acceptance Criteria:**
- Criterion 1
- Criterion 2
- Criterion 3

**Story Points:** [X points - set via CLI]
**Priority:** [Priority - set via CLI]
**Activity Type:** [Activity type - set via CLI]

---

#### Post-Creation (if not set during creation)

1. **Link to Epic**: `jira issue edit HYPERFLEET-XXX --parent EPIC-KEY --no-input`
2. **Add Labels**: `jira issue edit HYPERFLEET-XXX -l label1 -l label2 --no-input`
3. **Add Component**: `jira issue edit HYPERFLEET-XXX -C "Sentinel" --no-input`
```

## Integration with Other Skills

This skill complements:
- **jira-story-pointer**: Used in Step 4 to estimate story points (complexity analysis, historical comparison)
- **jira-triage**: Use to validate ticket quality after creation
- **jira-cli**: All operations use jira-cli under the hood
