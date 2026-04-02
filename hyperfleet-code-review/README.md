# HyperFleet Code Review Plugin

A Claude Code plugin that provides a standardized, interactive PR review workflow for the HyperFleet team.

## Features

### Skills
- **`/review-pr <PR>`** - Comprehensive PR review with interactive recommendations

### What It Does

- Fetches PR details, diff, existing reviewer comments, and HyperFleet standards in parallel
- Detects drift between fetched standards and mechanical pass definitions — warns if the plugin's checks are out of date with the architecture repo
- Validates PR against JIRA ticket requirements (title, description, acceptance criteria, and comment-thread refinements)
- Checks consistency with HyperFleet architecture documentation
- Runs impact and call chain analysis to detect breaking changes and verify consistency across the codebase
- Cross-references documentation and code for mismatches, including link and anchor validation
- Runs 10 groups of mechanical code pattern checks in parallel:
  - **Error handling & wrapping** — ignored errors, log-and-continue, HTTP handler missing return, error wrapping (%w), sentinel errors (Go)
  - **Concurrency** — shared state safety, goroutine lifecycle, loop variable capture (Go)
  - **Exhaustiveness & guards** — switch/select completeness, nil/bounds safety (Go)
  - **Resource & context lifecycle** — cleanup verification, context propagation, time.After leaks (Go)
  - **Code quality & struct completeness** — constants/magic values, struct field initialization (Go)
  - **Testing & coverage** — test coverage for new code, test structure patterns, test isolation and cleanup (Go)
  - **Naming & code organization** — stuttering, acronym casing, getter naming, function complexity (Go)
  - **Security** — injection vulnerabilities, secrets exposure, path traversal, input validation (all languages)
  - **Code hygiene** — TODOs/FIXMEs without ticket, log level appropriateness, typo detection (all languages)
  - **Performance** — allocation/preallocation patterns, defer in loops, N+1 queries (Go)
- Checks intra-PR consistency against HyperFleet coding standards
- Deduplicates findings against CodeRabbit, human reviewers, and prior conversation context
- Presents recommendations one at a time with GitHub-ready comments
- Sends cross-platform desktop notifications (OSC 9/777/99 + native fallback)

### Review Prioritization (most to least critical)

1. Bugs and logic issues
2. Security issues
3. Inconsistencies with HyperFleet architecture docs
4. JIRA requirements not met
5. Deviations from HyperFleet coding standards
6. Internal contradictions
7. Outdated/deprecated versions
8. Project pattern violations
9. Mechanical checks and intra-PR consistency findings
10. Clarity and maintainability improvements

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

After each recommendation, the skill uses `AskUserQuestion` to prompt for the next action. Available commands depend on the review mode:

| Command | Mode | Action |
|---------|------|--------|
| `next` or `n` | All | Show the next recommendation |
| `all` or `list` | All | Show a summary table of all recommendations |
| `1` to `N` | All | Jump to a specific recommendation |
| `fix` | Self-review only | Apply the suggested fix directly using Edit/Write tools |
| `comment` | Comment mode only | Post the recommendation as an inline review comment on the PR |
| `ticket` | After review | Create follow-up JIRA tickets for impact warnings via `jira-ticket-creator` |

### Review Modes

- **Self-review mode**: Activated when the current GitHub user is the PR author AND the current branch matches the PR head branch. Offers the "fix" option to apply changes directly.
- **Comment mode**: Activated when reviewing someone else's PR. Offers the "comment" option to post inline review comments on the exact file and line in GitHub.

### Output

Each recommendation includes:
- File path and line number
- Priority level
- Problem description
- GitHub-ready comment (copy-paste to PR)

## Skill Structure

```text
skills/review-pr/
├── SKILL.md                 # Main instructions and workflow
├── mechanical-passes.md     # 10 grouped mechanical code pattern checks
└── output-format.md         # Output format and interactive behavior
```

## Troubleshooting

### "gh: command not found"
Install GitHub CLI following the [official instructions](https://cli.github.com/).

### "jira: command not found"
Install jira-cli:
```bash
brew install ankitpokhrel/jira-cli/jira-cli
```
Then configure it for HyperFleet — see the [hyperfleet-jira README](../hyperfleet-jira/README.md#configure-jira-cli) for the setup command.

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
