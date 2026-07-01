# HyperFleet Hooks Plugin

Automated quality checks for Claude Code sessions. Adds checks within the AI-assisted workflow.

## Installation

```bash
/plugin install hyperfleet-hooks@openshift-hyperfleet/hyperfleet-claude-plugins
```

Verify with `/hooks` after restarting Claude Code.

## Hooks

### Go Lint (PostToolUse)

Runs `golangci-lint` after any `*.go` file is edited or created. Only reports issues on lines changed since the last commit (`--new-from-rev=HEAD`), so pre-existing lint issues don't block Claude. Falls back to full-package linting if no git baseline is available.
