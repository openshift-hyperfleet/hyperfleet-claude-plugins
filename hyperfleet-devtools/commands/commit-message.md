---
description: "Generate commit message following HyperFleet commit standard"
allowed-tools: Bash, Read
argument-hint: "[type] [HYPERFLEET-XXX]"
---

# Commit Message Generator

Generate a standardized commit message following the HyperFleet Commit Standard.

## Arguments

- `$1` (optional): Commit type (e.g., feat, fix, refactor, docs). If not provided, AI will infer from changes.
- `$2` (optional): JIRA ticket number (e.g., HYPERFLEET-456). If not provided, will attempt to extract from branch name.

## Instructions

1. **Read commit standard** from GitHub:
   ```bash
   curl -s https://raw.githubusercontent.com/openshift-hyperfleet/architecture/main/hyperfleet/standards/commit-standard.md
   ```

2. **Extract JIRA ticket** (priority: `$2` argument → branch name → none)
   - From branch: extract `HYPERFLEET-[0-9]+` pattern
   - If not found: warn but continue

3. **Analyze changes** (prefer staged, fallback to unstaged)
   - Exit with friendly message if no changes
   - Show file count being analyzed

4. **Determine commit type**:
   - If `$1` provided: use that type (validate against standard)
   - If not provided: infer from changes based on standard's type definitions

5. **Generate message and save to temporary file**:
   - Generate message following standard format:
     - Subject line:
       - With ticket: `HYPERFLEET-XXX - <type>: <subject>`
       - Without ticket: `<type>: <subject>`
     - Body (REQUIRED - always generate):
       - First paragraph: Brief summary (1-2 sentences explaining what and why)
       - Blank line
       - Detailed changes as bullet points: `- Change 1`, `- Change 2`
       - Each bullet point on a new line
       - Separate from subject with blank line
     - Apply all constraints from commit-standard.md
     - Do NOT add Co-Authored-By footer
   - Write message to temporary file:
     - File path: `/tmp/commit-msg-<JIRA-ticket>.txt` (or `/tmp/commit-msg.txt` if no ticket)
     - Use Bash tool to write the file

6. **Present with details**:
   - Show the complete generated message (subject + body with bullet points)
   - Display: subject character count, type, JIRA status
   - Confirm temporary file location: `/tmp/commit-msg-<ticket>.txt`
   - Provide TWO git commit commands:
     - **Recommended**: Full message with body from file
       ```bash
       git commit -F /tmp/commit-msg-HYPERFLEET-XXX.txt
       ```
     - **Quick option**: Subject only
       ```bash
       git commit -m "subject"
       ```
   - Warn if no JIRA ticket
   - Suggest shorter subject if exceeds limit from standard

## Notes

- Only generates message, user commits manually
- Works with staged or unstaged changes
