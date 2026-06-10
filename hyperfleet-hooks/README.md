# HyperFleet Hooks Plugin

Automated quality checks for Claude Code sessions. Adds checks within the AI-assisted workflow.

## Installation

```bash
/plugin install hyperfleet-hooks@openshift-hyperfleet/hyperfleet-claude-plugins
```

Verify with `/hooks` after restarting Claude Code.

## Hooks

### Go Lint (PostToolUse)

Runs `golangci-lint` after any `*.go` file is edited or created. Lint errors are reported back to Claude as context.
