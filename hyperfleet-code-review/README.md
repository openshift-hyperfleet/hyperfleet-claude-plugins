# HyperFleet Code Review Plugin

A Claude Code plugin that provides a standardized, interactive PR review workflow for the HyperFleet team.

## Features

### Commands
- **`/review-pr <PR>`** - Comprehensive PR review with interactive recommendations

### What It Does

- Fetches PR details, diff, and existing reviewer comments via GitHub CLI
- Validates PR against JIRA ticket requirements (title, description, acceptance criteria, and comment-thread refinements)
- Checks consistency with HyperFleet architecture documentation
- Runs impact analysis to detect breaking changes for consumers
- Traces call chains to verify consistency across the codebase
- Cross-references documentation and code for mismatches
- Runs mechanical code pattern checks (error handling, resource lifecycle, concurrency safety, nil/bounds safety, and more)
- Deduplicates findings against CodeRabbit, human reviewers, and prior conversation context
- Presents recommendations one at a time with GitHub-ready comments

### Review Prioritization (most to least critical)

1. Bugs and logic issues
2. Security issues
3. Inconsistencies with HyperFleet architecture docs
4. JIRA requirements not met
5. Internal contradictions
6. Outdated/deprecated versions
7. Project pattern violations
8. Mechanical checklist findings
9. Clarity and maintainability improvements

## Prerequisites

### Required Tools

- **[GitHub CLI (`gh`)](https://cli.github.com/)** - Must be installed and authenticated
- **[jira-cli](https://github.com/ankitpokhrel/jira-cli)** - Required for JIRA ticket validation

### Required Plugins

- **`hyperfleet-architecture`** - Used for architecture documentation validation. Install it from the same marketplace:
  ```text
  /plugin install hyperfleet-architecture@openshift-hyperfleet/hyperfleet-claude-plugins
  ```

## Installation

1. **Add the HyperFleet marketplace (if not already added):**
   ```text
   /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. **Install the code review plugin:**
   ```text
   /plugin install hyperfleet-code-review@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Basic Usage

```text
/review-pr https://github.com/org/repo/pull/123
```

Or using the short format:

```text
/review-pr org/repo#123
```

### Interactive Navigation

After the initial recommendation is shown:

| Command | Action |
|---------|--------|
| `next` or `n` | Show the next recommendation |
| `all` or `list` | Show a summary table of all recommendations |
| `1` to `N` | Jump to a specific recommendation |

### Output

Each recommendation includes:
- File path and line number
- Priority level
- Problem description
- GitHub-ready comment (copy-paste to PR)

## Troubleshooting

### "gh: command not found"
Install GitHub CLI following the [official instructions](https://cli.github.com/).

### "jira: command not found"
Install jira-cli:
```bash
brew install ankitpokhrel/jira-cli/jira-cli
```

### "Permission denied" or "Not Found" on PR
Ensure `gh` is authenticated and has access to the repository:
```bash
gh auth status
```

### Architecture checks not running
Ensure the `hyperfleet-architecture` plugin is installed:
```text
/plugin install hyperfleet-architecture@openshift-hyperfleet/hyperfleet-claude-plugins
```

## Contributing

See the main [HyperFleet Claude Plugins README](../README.md) for contribution guidelines.

## Maintainers

- Rafael Benevides (@rafabene)
- Ciaran Roche (@ciaranRoche)
