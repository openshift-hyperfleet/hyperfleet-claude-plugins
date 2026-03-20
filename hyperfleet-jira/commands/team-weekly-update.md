---
description: "Weekly team update - a list of closed issues(Story,Task,Bug) in the last 7 days with a nested display in one team"
allowed-tools: Bash
argument-hint: "[project-key] [team-key]"
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

For each activity type below, follow this three-step process to fetch issues and their parent Epic information:

**Step 1**: Get list of closed issue keys
**Step 2**: For each issue, fetch full details including parent epic (fields.parent) and summary
**Step 3**: Group issues by their parent Epic and fetch Epic details

### Activity Types to Process:

Loop through these activity types using a bash array:

```bash
ACTIVITY_TYPES=(
    "Quality / Stability / Reliability"
    "Product / Portfolio Work"
    "Associate Wellness & Development"
    "Future Sustainability"
    "Incidents & Support"
    "Security & Compliance"
)

# For each activity type, fetch closed issues:
for activity_type in "${ACTIVITY_TYPES[@]}"; do
    jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and resolution = Done AND status changed to closed during (-7d, now()) and customfield_10464 = "'"$activity_type"'" ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
    # Process each issue as described in "For Each Issue Retrieved" section below
done
```

Also check for issues without an activity type:

```bash
# Issues without activity type
jira issue list -q 'project = ${1:-HYPERFLEET} and type in (Story,Task,Bug) and resolution = Done AND status changed to closed during (-7d, now()) and customfield_10464 is EMPTY ${2:+and Team = $2}' --columns KEY --plain --no-headers 2>/dev/null
```

### For Each Issue Retrieved:

Get full issue details including parent epic:
```bash
jira issue view <ISSUE_KEY> --raw 2>/dev/null | jq -r '{key: .key, summary: .fields.summary, epicKey: .fields.parent.key, epicSummary: .fields.parent.fields.summary, epicStatus: .fields.parent.fields.status.name, status: .fields.status.name, type: .fields.issuetype.name}'
```

Note: If parent is null, the issue has no parent epic.

### For Each Unique Epic Key:

1. Get epic details:
```bash
jira issue view <EPIC_KEY> --raw 2>/dev/null | jq -r '{key: .key, summary: .fields.summary, status: .fields.status.name, type: .fields.issuetype.name}'
```
2. Calucate the Epic complete_ratio:
complete_ratio = the number of Done childeren issues / total number of children issue * 100 

## Output Format

**Weekly [Team: team-key] Update - [Start Date] to [End Date]**

### Summary Stats
- Total number of closed issues

### Issues Grouped by Activity Type, then by Parent Epic

For each activity type, please group issues by their parent Epic and display in this nested structure: Activity type -> Epic -> Story/Task/Bug 

**Activity Type Name** (count)

  **Epic: [EPIC-KEY] - [Epic Summary]** (Status: [Epic Status], Done/Total, complete_ratio)
    - [ISSUE-KEY]: [Issue Summary]
    - [ISSUE-KEY]: [Issue Summary]

  **Epic: [EPIC-KEY2] - [Epic Summary]** (Status: [Epic Status],Done/Total, complete_ratio)
    - [ISSUE-KEY]: [Issue Summary]
    - [ISSUE-KEY]: [Issue Summary]
    

  **No Parent Epic**
    - [ISSUE-KEY]: [ISSUE-TYPE]: [Issue Summary]
    - [ISSUE-KEY]: [ISSUE-TYPE]: [Issue Summary]
    
Example:

**Quality / Stability / Reliability** (21 issues)

  **Epic: HYPERFLEET-402 - E2E Test Automation Framework for CLM Components - MVP** (Status: Closed, 90%)
    - HYPERFLEET-680: Migrate from kubectl CLI to Kubernetes client-go Library for E2E Testing
    - HYPERFLEET-532: E2E Test Case Automation Run Strategy and Resource Management

  **No Parent Epic**
    - HYPERFLEET-682: [Bug] Adapter1 and Adapter2 not reporting correct conditions and status
    - HYPERFLEET-672: [Story] Adapter Helm chart: RabbitMQ exchange_type missing from broker config
