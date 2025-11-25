---
name: JIRA Ticket Creator
description: Creates well-structured JIRA tickets in the HYPERFLEET project with required fields including What/Why/Acceptance Criteria, story points, and activity type. Activates when users ask to create a ticket, story, task, or epic.
---

# JIRA Ticket Creator Skill

## ⚠️ CRITICAL: JIRA Uses Wiki Markup, NOT Markdown!

**YOU MUST USE JIRA WIKI MARKUP SYNTAX - NEVER USE MARKDOWN!**

| Element | ❌ WRONG | ✅ CORRECT |
|---------|----------|------------|
| **Header** | `### What` | `h3. What` (space required!) |
| **Bullets** | `- Item` or `• Item` | `* Item` |
| **Nested** | `  - Nested` | `** Nested` |
| **Inline Code** | `` `code` `` | `{{code}}` |
| **Bold** | `**text**` | `*text*` |
| **Path Params** | `/api/{id}` | `/api/:id` or `/api/ID` |
| **Placeholders** | `{customer-id}` | `CUSTOMER_ID` or `:customer_id` |

**If you use Markdown syntax, the ticket will render incorrectly in JIRA!**

See "CRITICAL: JIRA Wiki Markup Formatting" section below for complete reference.

---

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

### 1. **What** (Required)
Clear, concise description of what needs to be done. Should be 2-4 sentences explaining the work.

### 2. **Why** (Required)
Business justification and context. Explain:
- Why this work matters
- Who benefits (users, team, system)
- What problem it solves or value it delivers

### 3. **Acceptance Criteria** (Required)
Minimum 2-3 clear, testable criteria that define "done":
- Must be objective and verifiable
- Should cover functional requirements and edge cases
- Use bullet format with specific details

### 4. **Story Points** (Required for Stories/Tasks/Bugs)
All Stories, Tasks, and Bugs must have story points:
- Use scale: 0, 1, 3, 5, 8, 13
- Follow the team's estimation guide (see Story Points section)

### 5. **Activity Type** (Required for Stories/Tasks/Bugs)
Must set activity type for capacity planning. Valid types:
- `Associate Wellness & Development`
- `Incidents & Support`
- `Security & Compliance`
- `Quality / Stability / Reliability`
- `Future Sustainability`
- `Product / Portfolio Work`

### 6. Optional Context
Additional sections can be added as needed:
- **Technical Notes**: High-level implementation plan
- **Dependencies**: Linked tickets or external dependencies
- **Out of Scope**: Explicitly state what's NOT included

## CRITICAL: JIRA Wiki Markup Formatting

**JIRA uses wiki markup, NOT Markdown!**

### Headers
```
h3. What              ✅ Correct (space after period!)
h3. Why               ✅ Correct
**What**              ❌ Wrong (Markdown syntax)
### What              ❌ Wrong (Markdown syntax)
```

### Bullets
```
* Item 1              ✅ Correct
** Nested item        ✅ Correct (two asterisks)
- Item 1              ❌ Wrong (Markdown syntax)
• Item 1              ❌ Wrong (Unicode bullet)
  - Nested            ❌ Wrong (indentation + dash)
```

**Real Example - HYPERFLEET-255 (WRONG):**
```
### Summary        ❌ Markdown header - won't render!

• POST /api/...    ❌ Unicode bullet - won't render!
```

**Should Have Been:**
```
h3. Summary        ✅ JIRA wiki header

* POST /api/...    ✅ JIRA wiki bullet
```

### Inline Code
```
{{package/path}}              ✅ Correct
{{variable_name}}             ✅ Correct
`package/path`                ❌ Wrong (Markdown syntax)
```

### Bold/Italic
```
*bold text*           ✅ Correct
_italic text_         ✅ Correct
**bold**              ❌ Wrong (Markdown syntax)
```

### Code Blocks
**DO NOT use code blocks in CLI-created tickets!** They don't render properly.

```
{code:go}             ❌ Don't use via CLI (renders as empty gray box)
package main
{/code}
```

**Instead:**
- Use inline code: `{{package_name}}`
- Add code examples manually via web UI after creation
- Or use descriptive text with inline code references

### API Endpoints
```
*POST* /api/v1/clusters/:id                   ✅ Correct (bold HTTP method, colon notation)
*GET* /api/v1/clusters/CLUSTER_ID             ✅ Correct (placeholder text)
*POST* /api/v1/clusters/{id}                  ❌ Wrong - curly braces break rendering!
{{POST /api/v1/clusters/{id}}}                ❌ Wrong (nested braces break rendering)
```

### Curly Braces Warning
**NEVER use curly braces `{}` in ticket descriptions - they break JIRA rendering!**

```
wif-{customer-id}-key                         ❌ Wrong - curly braces break rendering!
{{wif-{customer-id}-key}}                     ❌ Wrong - nested braces also break!
wif-CUSTOMER_ID-key                           ✅ Correct - use CAPS or other notation
/api/v1/clusters/{id}                         ❌ Wrong - path parameter braces break!
/api/v1/clusters/:id                          ✅ Correct - use colon notation
/api/v1/clusters/CLUSTER_ID                   ✅ Correct - use placeholder text
```

**Alternatives to curly braces:**
* Use SCREAMING_CASE: `wif-CUSTOMER_ID-key`
* Use colon notation: `/api/v1/clusters/:id`
* Use angle brackets: `wif-<customer-id>-key`
* Use square brackets: `wif-[customer-id]-key`

### YAML in Code Blocks
**NEVER include YAML comments in code blocks!** The `#` character is interpreted as `h1.` header.

**Wrong:**
```
{code:yaml}
# This is a comment
field: value
{/code}
```

**Correct Option 1 - Descriptive text:**
```
Configuration fields:
* {{field: value}} - Description of field
```

**Correct Option 2 - Code block without comments:**
```
{code:yaml}
field: value
{/code}

Explanation outside code block...
```

## Ticket Creation Workflow

### Step 1: Gather Requirements

Ask the user clarifying questions if needed:
- What type of ticket? (Epic, Story, Task, Bug)
- What needs to be done? (What)
- Why is this important? (Why)
- How will we know it's done? (Acceptance Criteria)
- How complex/large is this work? (for story points)
- What category of work is this? (for activity type)

### Step 2: Create Description File

**⚠️ CRITICAL: Always create a temporary file with JIRA wiki markup (NOT Markdown!):**

**DO NOT USE:**
- `### Headers` (Markdown)
- `- bullets` or `• bullets` (Markdown/Unicode)
- `` `inline code` `` (Markdown)
- `**bold**` (Markdown)

**USE ONLY:**
- `h3. Headers` (JIRA wiki - space required!)
- `* bullets` (JIRA wiki)
- `{{inline code}}` (JIRA wiki)
- `*bold*` (JIRA wiki)

**Template for Stories/Tasks (JIRA Wiki Markup):**
```
h3. What

Brief description paragraph.

Detailed explanation paragraph (optional).

h3. Why

* Reason 1
* Reason 2
* Reason 3

h3. Acceptance Criteria:

* {{Component}} created/implemented/configured
* Feature X works correctly:
** Detail 1
** Detail 2
* Tests achieve >80% coverage
* Documentation updated

h3. Technical Notes:

* Use {{package-name}} for implementation
* Configuration in {{/path/to/config.yaml}}
* Important consideration
* Reference {{AnotherComponent}}

h3. Out of Scope:

* Item not included
* Another exclusion
```

**Template for Epics:**
```
h1. Epic Title

h3. Overview

Brief overview paragraph.

h3. What

* Key deliverable 1
* Key deliverable 2
** Sub-item
* Key deliverable 3

h3. Why

Explanation of business value and impact.

h3. Scope

*In Scope*:
* Item 1
* Item 2

*Out of Scope*:
* Item 3
* Item 4

h3. Success Criteria

* Criterion 1
* Criterion 2
* Criterion 3
```

### Step 3: Determine Story Points

Use the estimation scale:

| Points | Meaning | Typical Scope |
|--------|---------|---------------|
| **0** | Tracking Only | Quick/easy task, negligible effort |
| **1** | Trivial | One-line change, extremely simple |
| **3** | Straightforward | Time consuming but straightforward |
| **5** | Medium | Requires investigation, design, collaboration |
| **8** | Large | Big task, investigation & design required, needs design doc |
| **13** | Too Large | MUST be broken down into smaller stories |

Consider:
- Scope (lines of code, files affected, integration points)
- Complexity (new patterns, unfamiliar tech)
- Risk (ambiguity, dependencies, unknowns)
- Testing effort

### Step 4: Assign Activity Type

Choose based on work category:

**Reactive Work (Non-Negotiable First):**
- `Associate Wellness & Development` - Training, onboarding, team growth
- `Incidents & Support` - Customer escalations, production issues
- `Security & Compliance` - CVEs, security patches, compliance

**Core Principles (Quality Focus):**
- `Quality / Stability / Reliability` - Bugs, tech debt, toil reduction, SLOs

**Proactive Work (Balance Capacity):**
- `Future Sustainability` - Tooling, automation, architecture improvements
- `Product / Portfolio Work` - New features, strategic product work

### Step 5: Create the Ticket via jira-cli

**IMPORTANT: Use the patterns that actually work!**

#### Creating a Story

```bash
# 1. Save description to temporary file
cat > /tmp/story-description.txt << 'EOF'
h3. What

Description of what needs to be done.

h3. Why

* Reason 1
* Reason 2

h3. Acceptance Criteria:

* Criterion 1
* Criterion 2
* Criterion 3

h3. Technical Notes:

* Use {{package-name}}
* Configuration in {{/path/to/config}}
EOF

# 2. Create story (NOTE: Do NOT use --custom for story points via CLI - set via web UI)
jira issue create --project HYPERFLEET --type Story \
  --summary "Story Title (< 100 chars)" \
  --no-input \
  -b "$(cat /tmp/story-description.txt)"

# 3. Note the ticket number from output (e.g., HYPERFLEET-123)

# 4. Set story points via web UI (jira-cli custom fields can be unreliable)
```

#### Creating a Task

```bash
# Same as Story, just change --type to Task
cat > /tmp/task-description.txt << 'EOF'
h3. What

Task description.

h3. Why

Justification.

h3. Acceptance Criteria:

* Criterion 1
* Criterion 2
EOF

jira issue create --project HYPERFLEET --type Task \
  --summary "Task Title" \
  --no-input \
  -b "$(cat /tmp/task-description.txt)"
```

#### Creating an Epic

**CRITICAL: Epics require the Epic Name field!**

```bash
# 1. Create description file
cat > /tmp/epic-description.txt << 'EOF'
h1. Epic Full Title

h3. Overview

Overview paragraph.

h3. What

* Deliverable 1
* Deliverable 2

h3. Why

Explanation.

h3. Success Criteria

* Criterion 1
* Criterion 2
EOF

# 2. Create epic with Epic Name (required field!)
jira issue create --project HYPERFLEET --type Epic \
  --summary "Epic: Full Title Here" \
  --custom epic-name="Short Name" \
  --template /tmp/epic-description.txt \
  --no-input

# Note: Use --custom epic-name="Name" (not epicName or customfield_12311141)
```

#### Creating a Bug

```bash
cat > /tmp/bug-description.txt << 'EOF'
h3. What

Description of the bug and its impact.

h3. Why

Why this needs to be fixed urgently.

h3. Acceptance Criteria:

* Bug is reproducible
* Root cause identified
* Fix is verified
* Regression test added
EOF

jira issue create --project HYPERFLEET --type Bug \
  --summary "Bug: Brief Description" \
  --no-input \
  -b "$(cat /tmp/bug-description.txt)"
```

### Step 6: Post-Creation Manual Steps

After creating a ticket via CLI, these must be done manually via web UI:

1. **Set Story Points**
   - Edit ticket → Story Points field
   - Custom fields via CLI are unreliable

2. **Set Activity Type**
   - Edit ticket → Activity Type field
   - Select from dropdown

3. **Link to Epic** (for Stories)
   - Edit ticket → Link → "is child of" → Epic ticket

4. **Add Labels**
   - Edit ticket → Labels field
   - Add relevant tags

5. **Add Code Examples** (if needed)
   - Edit description via web UI
   - Add `{code:language}...{/code}` blocks
   - Code blocks don't render properly via CLI

### Step 7: Verify and Return Details

```bash
# View created ticket
jira issue view HYPERFLEET-XXX --plain

# Check in web UI
# URL: https://issues.redhat.com/browse/HYPERFLEET-XXX
```

Return to user:
- Ticket key (e.g., HYPERFLEET-123)
- Link: https://issues.redhat.com/browse/HYPERFLEET-123
- Summary of what was created
- **List of manual steps needed** (story points, activity type, etc.)

## Output Format

When creating a ticket, provide this output to the user:

```
### Ticket Created: HYPERFLEET-XXX

**Type:** [Story/Task/Epic/Bug]
**Summary:** [Title]
**Link:** https://issues.redhat.com/browse/HYPERFLEET-XXX

---

#### Description Structure (✅ Created via CLI)

**What:**
[What description]

**Why:**
[Why description]

**Acceptance Criteria:**
* Criterion 1
* Criterion 2
* Criterion 3

---

#### Manual Steps Required (⚠️ Must be done via Web UI)

Please complete these steps in the JIRA web interface:

1. **Set Story Points**: [Recommended: X points based on complexity]
2. **Set Activity Type**: [Recommended: {activity type}]
3. **Link to Epic**: [If applicable: Link to HYPERFLEET-XXX]
4. **Add Labels**: [Suggested: label1, label2]
5. **Add Code Examples**: [If needed: Add via web UI description editor]

**Why manual?** Custom fields and code blocks don't render reliably via jira-cli.
```

## Common Pitfalls to Avoid

### ❌ DON'T:

**FORMATTING (Most Common Mistakes!):**
1. ❌ Use Markdown headers: `### What`, `## Summary`
2. ❌ Use Markdown/Unicode bullets: `- Item`, `• Item`
3. ❌ Use Markdown inline code: `` `code` ``
4. ❌ Use Markdown bold: `**text**`
5. ❌ Forget space after JIRA headers: `h3.What` (needs `h3. What`)

**TICKET EXAMPLES OF WRONG FORMATTING:**
- HYPERFLEET-255: Used `### Summary` and `• bullets` - headers didn't render!

**CURLY BRACES (Break JIRA Rendering!):**
6. ❌ Use curly braces `{}` anywhere - e.g., `{customer-id}`, `/api/{id}` - breaks rendering!
7. ❌ Use `{{}}` around content with braces - doubly broken!

**OTHER MISTAKES:**
8. ❌ Include code blocks with `{code}...{/code}` via CLI (renders as empty boxes)
9. ❌ Put YAML comments (`#`) in code blocks (breaks rendering)
10. ❌ Use `--custom` fields via CLI (unreliable for story points, activity type)
11. ❌ Use `--body-file` flag (doesn't exist!)
12. ❌ Mix Markdown and JIRA wiki markup in same ticket

**TICKET EXAMPLES OF CURLY BRACE ISSUES:**
- HYPERFLEET-258: Used `{customer-id}` - broke rendering! Fixed with CUSTOMER_ID

### ✅ DO:
1. Use JIRA wiki markup consistently
2. Save descriptions to temporary files: `-b "$(cat /tmp/file.txt)"`
3. Test with ONE ticket before creating multiple
4. Use `--no-input` for non-interactive creation
5. Set custom fields via web UI after creation
6. Add code examples via web UI
7. Use bold for HTTP methods: `*POST* /api/path`
8. Use inline code for paths: `{{/path/to/file}}`

## Troubleshooting

### Issue: Epic Name Required Error
```
Error: customfield_12311141: Epic Name is required.
```

**Solution:**
```bash
--custom epic-name="Short Name"  ✅ Correct
--custom epicName="Name"          ❌ Wrong
--custom customfield_12311141     ❌ Wrong
```

### Issue: Code Blocks Show as Empty Gray Boxes

**Solution:** Don't include code blocks via CLI. Add them manually via web UI after creation.

### Issue: Headers Not Rendering

**Solution:** Ensure space after period: `h3. What` (not `h3.What`)

### Issue: Bullets Not Working

**Solution:** Use `*` not `-`, and `**` for nested (not indentation)

### Issue: Custom Fields Won't Set

**Solution:** Set story points and activity type via web UI. The jira-cli custom field handling is unreliable.

## Best Practices

### 1. Always Test First
```bash
# Create ONE test ticket
jira issue create --project HYPERFLEET --type Story \
  --summary "TEST - Delete Me" \
  -b "$(cat /tmp/test-description.txt)" \
  --no-input

# Verify in CLI and web UI
jira issue view HYPERFLEET-XXX

# If good, create remaining tickets
# Delete test ticket when done
```

### 2. Store Description Files
Don't create tickets with inline strings. Always use files:
```bash
# Good
cat > /tmp/description.txt << 'EOF'
...
EOF
jira issue create ... -b "$(cat /tmp/description.txt)"

# Bad
jira issue create ... -b "h3. What\n\nLong description..."
```

### 3. Document Ticket Numbers
As tickets are created, track them:
```bash
# Epic created: HYPERFLEET-105
# Stories: HYPERFLEET-106, HYPERFLEET-107, HYPERFLEET-108
```

### 4. Batch Manual Steps
After creating multiple tickets via CLI:
1. List all ticket numbers
2. Open each in web UI
3. Batch set: story points, activity type, labels, epic links
4. More efficient than doing each individually

## Integration with Other Skills

This skill complements:
- **jira-story-pointer**: Use to refine story point estimates after creation
- **jira-hygiene**: Use to validate ticket quality after creation
- **jira-cli**: All operations use jira-cli under the hood

## Quick Reference Card

**Create Story:**
```bash
cat > /tmp/desc.txt << 'EOF'
h3. What
...
h3. Why
...
h3. Acceptance Criteria:
* ...
EOF

jira issue create --project HYPERFLEET --type Story \
  --summary "Title" --no-input \
  -b "$(cat /tmp/desc.txt)"
```

**Create Epic:**
```bash
jira issue create --project HYPERFLEET --type Epic \
  --summary "Epic: Title" \
  --custom epic-name="Short Name" \
  --template /tmp/epic-desc.txt \
  --no-input
```

**Manual Steps (Web UI):**
1. Story Points
2. Activity Type
3. Link to Epic
4. Labels
5. Code examples

**Formatting:**
- Headers: `h3. Text` (space!)
- Bullets: `*` and `**`
- Inline code: `{{code}}`
- Bold: `*text*`
- API endpoints: `*POST* /api/path/{id}`
