---
description: Find tickets with new comments you may have missed
allowed-tools: Bash
---

# New Comments

Find JIRA tickets with recent comments that the user should be aware of.

## Instructions

1. **Find tickets you're involved with that have recent comments:**
   ```bash
   jira issue list -q"(assignee = currentUser() OR reporter = currentUser() OR watcher = currentUser()) AND updated >= -1d AND comment ~ '*'" --order-by updated --reverse --plain 2>/dev/null
   ```

2. **Alternative - find recently updated tickets you're assigned to:**
   ```bash
   jira issue list -a$(jira me) --updated-after "-1d" --order-by updated --reverse --plain 2>/dev/null
   ```

3. **View specific ticket to see comments (for each relevant ticket):**
   ```bash
   jira issue view TICKET-KEY --comments 5 --plain 2>/dev/null
   ```

## Output Format

### Tickets with Recent Activity

For each ticket with new comments:

**TICKET-KEY: Summary**
- Last updated: [timestamp]
- Latest comment by: [author]
- Comment preview: [first 100 chars of comment]

---

### Summary
- Tickets with new comments: X
- Comments requiring your response: X (where you were @mentioned)

## Notes
- Focus on tickets updated in the last 24 hours by default
- If user specifies a different timeframe (e.g., "last week"), adjust the JQL accordingly
- Highlight any comments that directly mention the user
- Flag urgent/blocking discussions
