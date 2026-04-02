# Common Pitfalls, Troubleshooting, and Best Practices

## Common Pitfalls

### DON'T

1. Use `--body-file` flag — it doesn't exist! Use `-b "$(cat /tmp/file.txt)"` instead
2. Use raw field IDs like `--custom customfield_10028=3` — silently ignored! Use aliases
3. Use JIRA wiki markup for links (`[text|url]`) — the `jira-cli` expects Markdown (`[text](url)`) and wiki markup renders as malformed, duplicated links

### DO

1. Use standard Markdown for descriptions
2. Save descriptions to temporary files: `-b "$(cat /tmp/file.txt)"`
3. Test with ONE ticket before creating multiple
4. Use `--no-input` for non-interactive creation
5. Set story points via CLI: `--custom story-points=X`
6. Set priority via CLI: `--priority Normal`
7. Set activity type via CLI: `--custom activity-type="Product / Portfolio Work"`
8. Set component via CLI: `-C "Sentinel"`
9. Set labels via CLI: `-l label1 -l label2`
10. Link to epic via CLI: `-P EPIC-KEY`
11. Use **bold** for HTTP methods: `**POST** /api/path/:id`

## Troubleshooting

### Issue: Epic Name Required Error

```text
Error: customfield_12311141: Epic Name is required.
```

**Solution:**

```bash
--custom epic-name="Short Name"  # Correct
--custom epicName="Name"          # Wrong
--custom customfield_12311141     # Wrong
```

### Issue: Story Points Not Setting

**Solution:** Use the exact syntax `--custom story-points=X` where X is 0, 1, 3, 5, 8, or 13. Example:

```bash
jira issue create --project HYPERFLEET --type Story \
  --summary "Title" --custom story-points=5 --no-input \
  -b "$(cat /tmp/desc.txt)"
```

### Issue: Activity Type Not Setting

**Solution:** Use the exact syntax with quotes: `--custom activity-type="Quality / Stability / Reliability"`. Use field aliases, never raw IDs.

### Issue: Description is Empty After Creation

**Solution:** Sometimes `-b "$(cat ...)"` fails silently. Verify with `jira issue view HYPERFLEET-XXX --plain`. If empty, set via pipe:

```bash
cat /tmp/description.txt | jira issue edit HYPERFLEET-XXX --no-input
```

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
jira issue create ... -b "### What\n\nLong description..."
```

### 3. Document Ticket Numbers

As tickets are created, track them:

```bash
# Epic created: HYPERFLEET-105
# Stories: HYPERFLEET-106, HYPERFLEET-107, HYPERFLEET-108
```

### 4. Batch Post-Creation Edits

After creating multiple tickets via CLI, if any fields were missed:

```bash
# Link to epic
jira issue edit HYPERFLEET-XXX --parent HYPERFLEET-100 --no-input

# Add labels
jira issue edit HYPERFLEET-XXX -l label1 -l label2 --no-input

# Add component
jira issue edit HYPERFLEET-XXX -C "Sentinel" --no-input
```
