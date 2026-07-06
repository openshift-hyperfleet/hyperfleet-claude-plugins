---
description: "Weekly team update - a list of closed issues(Story,Task,Bug) with a nested display in one team. Accepts an optional Monday date to pick a specific week."
allowed-tools: Bash
argument-hint: "[monday-date] [project-key] [team-key]"
---

# Team Weekly Update

Summary of team progress over a week, focusing on closed issues classified by activity type.

## Arguments
- `$1` (optional): Monday date of the desired week in `YYYY-MM-DD` format (e.g., `2026-06-29`). The skill will compute the range Monday 00:00 → Sunday 23:59 of that week. If not provided or empty, defaults to the last 7 days (`-7d, now()`).
- `$2` (optional): Project key (e.g., HYPERFLEET). If not provided, uses HYPERFLEET as default.
- `$3` (optional): Team name to filter issues. If provided, filters issues where Team field matches this value.

## Examples

- Get weekly update for the last 7 days (default):
  ```
  team-weekly-update
  ```

- Get weekly update for the week of June 29, 2026:
  ```
  team-weekly-update 2026-06-29
  ```

- Get weekly update for a specific week and project:
  ```
  team-weekly-update 2026-06-29 MYPROJECT
  ```

- Get weekly update for a specific week, project, and team:
  ```
  team-weekly-update 2026-06-29 MYPROJECT MYTEAMKEY
  ```

- Get weekly update for the last 7 days with project and team filter:
  ```
  team-weekly-update "" HYPERFLEET MYTEAMKEY
  ```

## Instructions

For each activity type below, follow this three-step process to fetch issues and their parent Epic information:

**Step 1**: Get list of closed issue keys
**Step 2**: For each issue, fetch full details including parent epic (fields.parent) and summary
**Step 3**: Group issues by their parent Epic and fetch Epic details

### Date Range Calculation

Before querying, compute the date range based on `$1`:

```bash
if [[ -n "$1" ]]; then
    # $1 is a Monday date (YYYY-MM-DD). Compute Sunday = Monday + 6 days.
    MONDAY="$1"
    SUNDAY=$(date -j -v+6d -f "%Y-%m-%d" "$MONDAY" "+%Y-%m-%d" 2>/dev/null || date -d "$MONDAY + 6 days" "+%Y-%m-%d")
    DATE_RANGE="\"$MONDAY\", \"$SUNDAY\""
else
    DATE_RANGE="-7d, now()"
fi
```

Use `$DATE_RANGE` in all JQL queries below in the `status changed to closed during (...)` clause.

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
    jira issue list -q 'project = ${2:-HYPERFLEET} and type in (Story,Task,Bug) and resolution = Done and status changed to closed during ('"$DATE_RANGE"') and "Activity Type" = "'"$activity_type"'" ${3:+and Team = $3}' --columns KEY --plain --no-headers 2>/dev/null
    # Process each issue as described in "For Each Issue Retrieved" section below
done
```

Also check for issues without an activity type:

```bash
# Issues without activity type
jira issue list -q 'project = ${2:-HYPERFLEET} and type in (Story,Task,Bug) and resolution = Done and status changed to closed during ('"$DATE_RANGE"') and "Activity Type" is EMPTY ${3:+and Team = $3}' --columns KEY --plain --no-headers 2>/dev/null
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

2. Get all children of the epic and their status and calculate the complete_ratio of the Epic:
```bash
jira issue list -q "parent = <EPIC_KEY>" --raw 2>/dev/null  | jq -r '.[] | {key: .key, status: .fields.status.name}'
```

complete_ratio = count(the number of Closed children issues) / count(the number of children issues) * 100 

## Output Format

CRITICAL: You MUST create a THREE-LEVEL NESTED STRUCTURE. Do NOT skip any level:

---

**Weekly Team Update - [Start Date] to [End Date]**
**Team: [team-key]**

### Summary Stats
- Total Done issues: [count]
---

**[Activity Type Name]** 
  **Epic: [EPIC-KEY] - [Epic Summary]** (Status: [Epic Status], [Closed]/[Total], [%]%)
    - [ISSUE-KEY]: [Issue Summary]
    - [ISSUE-KEY]: [Issue Summary]
    

  **Epic: [EPIC-KEY2] - [Epic Summary]** (Status: [Epic Status], [Closed]/[Total], [%]%)
    - [ISSUE-KEY]: [Issue Summary]
    
  **No Parent Epic**
    - [ISSUE-KEY]: [[TYPE]] [Issue Summary]
    - [ISSUE-KEY]: [[TYPE]] [Issue Summary]

---

Example:

**Quality / Stability / Reliability** 

  **Epic: HYPERFLEET-402 - E2E Test Automation Framework for CLM Components - MVP** (Status: Closed, 9/10, 90%)
    - HYPERFLEET-680: Migrate from kubectl CLI to Kubernetes client-go Library for E2E Testing
    - HYPERFLEET-532: E2E Test Case Automation Run Strategy and Resource Management

  **No Parent Epic**
    - HYPERFLEET-682: [Bug] Adapter1 and Adapter2 not reporting correct conditions and status
    - HYPERFLEET-672: [Story] Adapter Helm chart: RabbitMQ exchange_type missing from broker config
