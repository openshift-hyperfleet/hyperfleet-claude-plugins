---
description: Generate commit message following HyperFleet commit standard
allowed-tools: Bash, Read
argument-hint: [type] [HYPERFLEET-XXX]
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

5. **Generate message** following standard format:
   - With ticket: `HYPERFLEET-XXX - <type>: <subject>`
   - Without ticket: `<type>: <subject>`
   - Apply all constraints from commit-standard.md

6. **Present with details**:
   - Show the generated message
   - Display: length/72, type, JIRA status
   - Provide git commit command
   - Warn if no JIRA ticket
   - Suggest shorter version if over 72 chars

## Notes

- Only generates message, user commits manually
- Works with staged or unstaged changes
