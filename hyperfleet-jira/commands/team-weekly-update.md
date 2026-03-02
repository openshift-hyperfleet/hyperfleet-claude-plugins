---
description: Weekly team update - a list of closed issues(Story,Task) in the last 7 days with a nested display : activity type -> Epic -> Story in one team.
allowed-tools: Bash
argument-hint: [project-key] [team-key]
---

# Team Weekly Update

Summary of team progress over the past week, focusing on closed issues classified by activity type.

## Arguments
- `$1` (optional): Project key (e.g., HYPERFLEET). If not provided, uses HYPERFLEET as default.
- `$2` (optional): Team name to filter issues. If provided, filters issues where Team field matches this value.

## Examples

- Get weekly update for default project (HYPERFLEET):
  ```
  team-weekly-update
  ```

- Get weekly update for specific project:
  ```
  team-weekly-update MYPROJECT
  ```

- Get weekly update for specific project and team:
  ```
  team-weekly-update MYPROJECT MYTEAMKEY
  ```

- Get weekly update for default project with team filter:
  ```
  team-weekly-update "" MYTEAMKEY
  ```

## Instructions

For each activity type below, follow this two-step process to fetch issues and their parent Epic information:

**Step 1**: Get list of closed issue keys
**Step 2**: For each issue, fetch full details including epic link (customfield_12311140) and summary
**Step 3**: Group issues by their parent Epic and fetch Epic details

### Activity Types to Process:

1. **Quality / Stability / Reliability**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Quality / Stability / Reliability" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

2. **Product / Portfolio Work**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Product / Portfolio Work" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

3. **Associate Wellness & Development**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Associate Wellness & Development" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

4. **Future Sustainability**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Future Sustainability" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

5. **Incidents & Support**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Incidents & Support" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

6. **Security & Compliance**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] = "Security & Compliance" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

7. **Without activity type**
   ```bash
   jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and status changed to "closed" during (-7d,now()) and cf[12320040] is EMPTY ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
   ```

### For Each Issue Retrieved:

Get full issue details including epic link:
```bash
jira issue view <ISSUE_KEY> --raw 2>/dev/null | jq -r '{key: .key, summary: .fields.summary, epicKey: .fields.customfield_12311140, status: .fields.status.name}'
```

### For Each Unique Epic Key:

Get epic details:
```bash
jira issue view <EPIC_KEY> --raw 2>/dev/null | jq -r '{key: .key, summary: .fields.summary, status: .fields.status.name, type: .fields.issuetype.name}'
```


## Output Format

**Weekly [Team: team-key] Update - [Start Date] to [End Date]**

### Summary Stats
- Total number of closed issues

### Issues Grouped by Activity Type, then by Parent Epic

For each activity type, group issues by their parent Epic and display in this nested structure:

**Activity Type Name** (count)

  **Epic: [EPIC-KEY] - [Epic Summary]** (Status: [Epic Status])
    - [ISSUE-KEY]: [Issue Summary]
    - [ISSUE-KEY]: [Issue Summary]

  **Epic: [EPIC-KEY2] - [Epic Summary]** (Status: [Epic Status])
    - [ISSUE-KEY]: [Issue Summary]

  **No Parent Epic**
    - [ISSUE-KEY]: [Issue Summary]

Example:

**Quality / Stability / Reliability** (21 issues)

  **Epic: HYPERFLEET-402 - E2E Test Automation Framework for CLM Components - MVP** (Status: Closed)
    - HYPERFLEET-680: Migrate from kubectl CLI to Kubernetes client-go Library for E2E Testing
    - HYPERFLEET-532: E2E Test Case Automation Run Strategy and Resource Management

  **No Parent Epic**
    - HYPERFLEET-682: Adapter1 and Adapter2 not reporting correct conditions and status
    - HYPERFLEET-672: Adapter Helm chart: RabbitMQ exchange_type missing from broker config
