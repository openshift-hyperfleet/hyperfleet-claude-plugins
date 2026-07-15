# JIRA Fix Commands

Commands for applying fixes via `jira issue edit`. Always use `--no-input` to skip interactive prompts. Always quote values that may contain spaces.

## Supported Operations

```bash
jira issue edit TICKET-KEY --custom story-points=X --no-input
jira issue edit TICKET-KEY --custom activity-type="VALUE" --no-input
jira issue edit TICKET-KEY -C "Component Name" --no-input
jira issue edit TICKET-KEY --priority Major --no-input
```

## Component Replacement

The `-C` flag **adds** a component without removing existing ones. To **replace**, combine add and remove in the same command. Quote all component names — several valid names contain spaces (`E2E Tests`, `Claude Plugins`, `Message Broker`):

```bash
jira issue edit TICKET-KEY -C "E2E Tests" --component "-Claude Plugins" --no-input
```

The `--component "-Name"` syntax (minus prefix inside quotes) removes a component.

## Label Operations

Same minus-prefix pattern applies to labels:

```bash
jira issue edit TICKET-KEY --label "new-label" --no-input
jira issue edit TICKET-KEY --label "-old-label" --no-input
```
