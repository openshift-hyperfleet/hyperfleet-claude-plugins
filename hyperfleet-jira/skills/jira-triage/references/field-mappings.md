# JIRA Custom Field Mappings

The `--plain` output does NOT show Story Points or Activity Type. When using `--raw`, use these field IDs — do NOT guess or use other field IDs.

## Field ID Reference

| Field | Raw JSON Path | Type |
|-------|---------------|------|
| Story Points | `.fields.customfield_10028` | number |
| Activity Type | `.fields.customfield_10464.value` | string |
| Epic Link | `.fields.customfield_10014` | string (ticket key) |
| Components | `.fields.components[].name` | string array |
| Fix Versions | `.fields.fixVersions[].name` | string array |
| Labels | `.fields.labels` | string array |
| Priority | `.fields.priority.name` | string |
| Assignee | `.fields.assignee.displayName` | string (null → "Unassigned") |
| Sprint | `.fields.customfield_10020[-1].name` | string |

## Single Ticket Extraction

Pipe directly to jq — do NOT store raw JSON in a shell variable (control characters in descriptions get corrupted).

```bash
jira issue view TICKET-KEY --raw 2>/dev/null | jq '{
  key: .key,
  type: .fields.issuetype.name,
  summary: .fields.summary,
  status: .fields.status.name,
  summaryLen: (.fields.summary | length),
  descLen: ((.fields.description // "" | tostring) | length),
  storyPoints: .fields.customfield_10028,
  components: [.fields.components[]?.name],
  activityType: .fields.customfield_10464?.value,
  priority: .fields.priority?.name,
  labels: .fields.labels,
  epicLink: (.fields.customfield_10014 // null),
  fixVersions: [.fields.fixVersions[]?.name],
  assignee: (.fields.assignee.displayName // "Unassigned")
}' || echo '{"error": "TICKET-KEY"}'
```

## Bulk Extraction (compact)

```bash
for key in KEY1 KEY2 KEY3; do
  jira issue view "$key" --raw 2>/dev/null | jq -c '{
    key: .key,
    type: .fields.issuetype.name,
    summary: .fields.summary,
    status: .fields.status.name,
    summaryLen: (.fields.summary | length),
    descLen: ((.fields.description // "" | tostring) | length),
    storyPoints: .fields.customfield_10028,
    components: [.fields.components[]?.name],
    activityType: .fields.customfield_10464?.value,
    priority: .fields.priority?.name,
    epicLink: (.fields.customfield_10014 // null),
    fixVersions: [.fields.fixVersions[]?.name],
    assignee: (.fields.assignee.displayName // "Unassigned")
  }' || echo "{\"error\": \"$key\"}"
done
```

## Acceptance Criteria

The dedicated AC custom field is typically unused. Check for acceptance criteria embedded in the description body (look for headings like "Acceptance Criteria" or checkbox lists). Use `--plain` to read the rendered description content.
