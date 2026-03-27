---
name: bugs-triage
description: Triage Jira bugs (New->Backlog) and GitHub issues for openshift-hyperfleet repos interactively.
allowed-tools: Bash, Read, Grep, Glob, AskUserQuestion, Skill
argument-hint: "[jira|github] (default: both)"
---

# Bug Triage Skill

## Dynamic context

- jira CLI: !`command -v jira >/dev/null 2>&1 && echo "available" || echo "NOT available"`
- gh CLI: !`command -v gh >/dev/null 2>&1 && echo "available" || echo "NOT available"`

## Arguments

- No argument: Run both Jira and GitHub triage
- `jira`: Run only Jira bug triage
- `github`: Run only GitHub issues triage

## References

Load these files as needed during triage:

- `references/owners.csv` — Component/domain owners for assignee suggestions
- `references/github-repos.md` — GitHub repositories in triage scope (skip issues from unlisted repos)

## Ticket Creation

When creating JIRA tickets (e.g., from accepted GitHub issues or RFE conversions), use the `hyperfleet-jira:jira-ticket-creator` skill via the Skill tool. This skill handles description formatting, Activity Type classification, Story Points estimation, and all ticket creation best practices. Pass the issue context (title, description, component, suggested priority) as the skill argument.

## Link Formatting

ALWAYS include clickable links in all tables, headings, and references:

- Jira: `[TICKET-KEY](https://redhat.atlassian.net/browse/TICKET-KEY)`
- GitHub: `[REPO#NUMBER](https://github.com/openshift-hyperfleet/REPO/issues/NUMBER)`

## Priority SLA Reference

| Priority | Triage SLA | Fix/Workaround SLA |
|----------|------------|---------------------|
| **Blocker** | Within 24 hours | Within 72 working hours |
| **Critical/Major** | Per Week | Within 5 working days |
| **Normal** | Per Sprint | Must be fixed in coming release |
| **Low** | Per Sprint | Planned per capacity; max 2 sprints, re-evaluate in 3rd |

---

## Part 1: Jira Bug Triage (New -> Backlog)

### Step 1: Fetch all bugs with status "New"

```bash
jira issue list -q"project = HYPERFLEET AND status = New AND issuetype = Bug" --plain --columns "KEY,SUMMARY,PRIORITY,STATUS,COMPONENT,ASSIGNEE,CREATED" 2>/dev/null
```

If no bugs found, report "No bugs in New status" and skip to Step 5.

### Step 2: Fetch bugs open for more than 3 sprints (approximately 6 weeks)

```bash
jira issue list -q"project = HYPERFLEET AND issuetype = Bug AND status not in (Closed, Done) AND created <= -42d" --plain --columns "KEY,SUMMARY,PRIORITY,STATUS,ASSIGNEE,CREATED" 2>/dev/null
```

### Step 3: Interactive triage of each "New" bug

**Skip bugs that already have an assignee** — they are already being handled.

For each remaining bug, do the following **one at a time**:

#### 3a. Fetch full details

```bash
jira issue view TICKET-KEY --plain 2>/dev/null
```

#### 3b. Present the bug and assess

Start with a heading: `### [TICKET-KEY](https://redhat.atlassian.net/browse/TICKET-KEY) - Summary`

Evaluate and present:

| Check | Status | Notes |
|-------|--------|-------|
| Sufficient info/logs | PASS/FAIL | Logs, steps to reproduce, environment details? |
| Priority set correctly | PASS/FAIL/MISSING | Based on SLA table |
| Component identified | PASS/FAIL/MISSING | Must be: API, Adapter, Sentinel, Broker, Architecture. If multiple components apply, add ALL |
| Target version | SET/MISSING | If MVP bug, set "MVP". Otherwise set planned fix version per release strategy (if field is available) |
| Valid bug | LIKELY/UNCLEAR | Real defect? Or actually a feature request (RFE)? |
| Hyperfleet scope | YES/NO | If not in Hyperfleet scope, move to the correct Jira Project |
| Assignee | SET/MISSING | If missing, suggest owner from `references/owners.csv` |

#### 3c. Recommend one action

1. **Move to Backlog** — valid, enough info, fields set
2. **Request more info** — missing logs/steps/environment
3. **Close as Won't Do** — valid bug/request but out of scope or low ROI
4. **Close as Rejected** — not a real bug (environmental issue, non-reproducible)
5. **Close as Duplicate** — search for duplicates first:
   ```bash
   jira issue list -q"project = HYPERFLEET AND issuetype = Bug AND summary ~ 'keyword'" --plain 2>/dev/null
   ```
6. **Convert to RFE** — if the bug is actually a feature request, create a Story/Task with `[RFE]` prefix and keep in "New" status
7. **Move to another Jira Project** — if not in Hyperfleet scope, move to the correct project
8. **Set missing fields first** — priority, component, or target version missing
9. **Escalate to tech leads** — if Blocker priority. The 24h goal is to deliver a fix/workaround OR provide a high-confidence RCA with next steps. Tag tech leads and managers in Slack immediately

#### 3d. Ask the user and execute

Use `AskUserQuestion` to confirm the action, then execute:

- Move to Backlog: `jira issue move TICKET-KEY "Backlog"`
- Set priority: `jira issue edit TICKET-KEY --priority "Normal" --no-input` — **always add a comment explaining why** the priority was changed
- Set component: `jira issue edit TICKET-KEY --component "Name" --no-input` — if multiple components apply, add all of them
- Set target version: `jira issue edit TICKET-KEY --custom target-version="MVP" --no-input` (if the field is available in the project)
- Request info: `jira issue comment add TICKET-KEY "..."`
- Close: `jira issue move TICKET-KEY "Closed" --resolution "<Resolution>"` — valid resolutions: `Won't Do`, `Rejected`, `Duplicate`
- Duplicate link: `jira issue link TICKET-KEY DUPLICATE-KEY "Duplicate"`
- Convert to RFE: Change type to Story/Task, add `[RFE]` prefix to summary, keep in "New" status
- Move to another project: Ask user which project, then move the ticket
- Escalate Blocker: Inform user to notify tech leads AND managers via Slack. Goal: fix/workaround or RCA within 24h

### Step 4: Report bugs open > 3 sprints

Present in a table and ask the user to re-evaluate or close each one:

```markdown
| Ticket | Priority | Status | Assignee | Created |
```

**Low priority rule:** Bugs with Low priority can be held for max 2 sprints. In the 3rd sprint, recommend re-evaluating — either fix or close them. Do not defer indefinitely.

### Step 5: Jira Triage Summary

```markdown
| Metric | Count |
|--------|-------|
| Bugs triaged | X |
| Moved to Backlog | X |
| Closed (Won't Do/Rejected/Duplicate) | X |
| Info requested | X |
| Skipped | X |
| Bugs open > 3 sprints | X |
```

---

## Part 2: GitHub Issues Triage

### Step 1: Fetch untriaged issues

First, read `references/github-repos.md` to get the list of repos in scope. Build the `repo:` filter dynamically from that file — extract each repo name and prepend `repo:openshift-hyperfleet/`. The query fetches issues that are either unlabeled or have `hf-needs-triage` but NOT already triaged labels:

```bash
# Example with 3 repos (build dynamically from references/github-repos.md):
gh api search/issues -X GET \
  -f q="is:issue is:open -label:hf-triaged/accepted -label:hf-triaged/rejected -label:hf-triaged/duplicate repo:openshift-hyperfleet/REPO1 repo:openshift-hyperfleet/REPO2 repo:openshift-hyperfleet/REPO3" \
  -f per_page=50 \
  --jq '.items[] | "\(.repository_url | split("/") | .[-1])|\(.number)|\(.title)|\(.state)|\(.labels | map(.name) | join(","))|\(.created_at[:10])"' 2>/dev/null
```

If none found, report "No untriaged GitHub issues" and skip to summary.

### Step 2: Fetch issues open > 3 sprints (6 weeks)

Query the same scoped repos (built dynamically from `references/github-repos.md`):

```bash
DATE=$(date -d '42 days ago' '+%Y-%m-%d' 2>/dev/null || date -v-42d '+%Y-%m-%d')
# Use the same dynamically-built repo filter as Step 1
gh api search/issues -X GET \
  -f q="is:issue is:open created:<$DATE repo:openshift-hyperfleet/REPO1 repo:openshift-hyperfleet/REPO2 repo:openshift-hyperfleet/REPO3" \
  -f per_page=50 \
  --jq '.items[] | "\(.repository_url | split("/") | .[-1])|\(.number)|\(.title)|\(.created_at[:10])|\(.labels | map(.name) | join(","))"' 2>/dev/null
```

### Step 3: Interactive triage of each issue

For each untriaged issue, do the following **one at a time**:

#### 3a. Fetch full details

```bash
gh issue view NUMBER --repo openshift-hyperfleet/REPO_NAME 2>/dev/null
```

#### 3b. Check if already tracked or resolved

Before assessing, search for existing Jira tickets and merged PRs:

```bash
jira issue list -q"project = HYPERFLEET AND summary ~ 'keyword'" --plain --columns "KEY,SUMMARY,STATUS" 2>/dev/null
```

```bash
gh pr list --repo openshift-hyperfleet/REPO_NAME --state merged --search "keyword" --limit 5 2>/dev/null
```

- If Jira ticket exists but no merged PR found: comment on GitHub linking to the Jira ticket, add `hf-triaged/accepted` label, **keep the issue open** (a Closed/Done Jira ticket alone does not prove the fix is in the repo), skip
- If code already fixed (merged PR found): comment referencing the PR, add `hf-triaged/accepted` label, close the issue, skip

Always add the appropriate triage label (`hf-triaged/accepted`, `hf-triaged/rejected`, or `hf-triaged/duplicate`) when closing or resolving an issue.

#### 3c. Present the issue and assess

Start with: `### [REPO#NUMBER](https://github.com/openshift-hyperfleet/REPO/issues/NUMBER) - Title`

| Check | Status | Notes |
|-------|--------|-------|
| Sufficient info | PASS/FAIL | Clear description, steps, context? |
| Labels present | PASS/FAIL | Existing labels? |
| Category | Bug/RFE/Help Request | Classify the issue |
| Hyperfleet scope | YES/NO/UNCLEAR | Within Hyperfleet's scope? |

#### 3d. Recommend one action

1. **Accept as Bug** — create Jira Bug, label `hf-triaged/accepted`
2. **Accept as RFE** — create Jira Story with `[RFE]` prefix, label `hf-triaged/accepted`
3. **Provide help** — answer on GitHub, label `hf-triaged/accepted`
4. **Reject** — close with explanation, label `hf-triaged/rejected`
5. **Mark as Duplicate** — link to existing issue, label `hf-triaged/duplicate`
6. **Request info** — comment requesting details, label `hf-needs-info`

#### 3e. Ask the user and execute

Use `AskUserQuestion` to confirm, then execute. Adding labels may fail due to repo permissions — handle gracefully and report.

**For accepted bugs/RFEs — create Jira ticket:**

Use the `hyperfleet-jira:jira-ticket-creator` skill via the Skill tool, passing the issue context (title, description, component, suggested priority). The skill handles description formatting, Activity Type, Story Points, and all creation best practices.

After creating the Jira ticket, comment on the GitHub issue and add label. **Keep the GitHub issue open** until the fix is available in the repository:

```bash
gh issue comment NUMBER --repo openshift-hyperfleet/REPO_NAME --body "This issue has been accepted and is being tracked in JIRA as [HYPERFLEET-XXX](https://redhat.atlassian.net/browse/HYPERFLEET-XXX). We will update this issue when there is progress." 2>/dev/null
```

```bash
gh issue edit NUMBER --repo openshift-hyperfleet/REPO_NAME --add-label "hf-triaged/accepted" 2>&1
```

### Step 4: Report issues open > 3 sprints

Present in a table and ask the user to re-evaluate or close each one:

```markdown
| Issue | Title | Created | Labels |
```

### Step 5: GitHub Triage Summary

```markdown
| Metric | Count |
|--------|-------|
| Issues triaged | X |
| Accepted (Bug) | X |
| Accepted (RFE) | X |
| Help provided | X |
| Rejected | X |
| Duplicate | X |
| Info requested | X |
| Skipped | X |
| Issues open > 3 sprints | X |
```

---

## Final Summary

Present a combined summary of all triage actions taken during the session.

## Important Rules

- Use `jira` CLI for Jira and `gh` CLI for GitHub; do not use other external CLIs, but allowed-tools (AskUserQuestion, Read, Skill) may be used as declared
- Process tickets **one at a time** — never batch without user confirmation
- Always provide a clear reason when closing tickets
- **Skip Jira bugs that already have an assignee** — they are already being handled
- **When changing priority**, always add a comment explaining the rationale
- **If a bug applies to multiple components**, add ALL related components
- **If a bug is not in Hyperfleet scope**, move it to the correct Jira Project
- **If a bug is really a feature request**, convert to Story/Task with `[RFE]` prefix in "New" status
- **For Blocker bugs**, immediately tag tech leads AND managers in Slack. 24h goal: fix/workaround OR high-confidence RCA + next steps
- When creating Jira tickets from GitHub issues, always link back to the original issue
- **Keep accepted GitHub issues open** until the fix is available in the repository
- Use the `hyperfleet-jira:jira-ticket-creator` skill when creating Jira tickets (handles formatting, Activity Type, and Story Points)
- Consult `references/owners.csv` to suggest assignees based on component
- Output in English
- ALWAYS include clickable links for every ticket/issue reference
