# HyperFleet Code Review Plugin

A Claude Code plugin that provides standardized code review workflows for the HyperFleet team — review local branch changes at any point in development, and review PRs with interactive recommendations.

## Features

### Skills

- **`/review-pr <PR>`** - Comprehensive PR review with interactive recommendations — use when a PR is already open on GitHub
- **`/review-local`** - Reviews local branch changes against HyperFleet standards — use at any point during development, before or after opening a PR

## Prerequisites

### Required Tools

- **[GitHub CLI (`gh`)](https://cli.github.com/)** - Must be installed and authenticated
- **[jira-cli](https://github.com/ankitpokhrel/jira-cli)** - Required for `/review-pr` JIRA ticket validation
- **[CodeRabbit CLI](https://coderabbit.ai/)** - Recommended for `/review-local` — runs automatically if installed

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

---

## `/review-pr` — PR Review

### What It Does

- Fetches PR details, diff, existing reviewer comments, and HyperFleet standards in parallel
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

### Usage

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
| `post` | Self-review only | Post a reply to an existing review comment (after preview) |
| `edit` | Self-review only | Provide custom reply text for an existing review comment |
| `ticket` | After review | Create follow-up JIRA tickets for impact warnings via `jira-ticket-creator` |

### Severity Levels

Each recommendation carries a severity:

- **Blocking** — must fix before merge. Default for Bug, Security, Architecture, JIRA, Standards, Inconsistency, Deprecated categories
- **nit:** — non-blocking suggestion. Default for Pattern, Improvement categories. Prefixed with `nit:` in both terminal output and GitHub comments

Blocking recommendations are always shown before nit recommendations within the same priority level.

### Confidence Levels

Each recommendation also carries a confidence level indicating how certain the analysis is that the finding is a real problem:

- **High** — strong evidence directly visible in the diff; almost certainly a real problem
- **Medium** — probable issue, but depends on context not fully visible in the diff
- **Low** — possible concern; reviewer should verify before acting

### Review Modes

- **Self-review mode**: Activated when the current GitHub user is the PR author AND the current branch matches the PR head branch. Offers the "fix" option to apply changes directly. After all recommendations, processes unresponded review comments from other reviewers — offering to fix, acknowledge, or respond with reasoning.
- **Comment mode**: Activated when reviewing someone else's PR. Offers the "comment" option to post inline review comments on the exact file and line in GitHub.

### Output

Each recommendation includes:

- File path and line number
- Severity level (**Blocking** — must fix before merge, or **nit:** — non-blocking suggestion)
- Confidence level (**High**, **Medium**, or **Low**)
- Category and priority level
- Problem description
- GitHub-ready comment (copy-paste to PR) with `nit:` prefix for non-blocking items

---

## `/review-local` — Local Review

Reviews all committed and uncommitted changes on the current branch against the upstream main branch.

```text
/review-local
```

No arguments needed — run from the repo you want to review.

### What It Does

Runs a comprehensive review of all local branch changes and produces a structured report. Checks include HyperFleet standards, architecture consistency,
mechanical code patterns (see `checks/`), impact analysis, doc/code cross-referencing,
and CodeRabbit if installed.

Output: a review setup block, findings grouped by category with AI-ready prompts,
warnings with inline context, and a review summary box.

---

## Skill Structure

```text
skills/review-pr/
├── SKILL.md                      # Main instructions and workflow
├── output-format.md              # Output format and interactive behavior
├── group-01-error-handling.md    # Error handling and wrapping (Go)
├── group-02-concurrency.md       # Concurrency and goroutine safety (Go)
├── group-03-exhaustiveness.md    # Exhaustiveness and guards (Go)
├── group-04-resource-lifecycle.md # Resource and context lifecycle (Go)
├── group-05-code-quality.md      # Code quality and struct completeness (Go)
├── group-06-testing.md           # Testing and coverage (Go)
├── group-07-naming.md            # Naming and code organization (Go)
├── group-08-security.md          # Security (all languages)
├── group-09-code-hygiene.md      # Code hygiene (all languages)
└── group-10-performance.md       # Performance (Go)

skills/review-local/              # Local review skill
└── ...

checks/             # Check definitions
config/             # Reference data
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

- Phuongnhat Nguyen (@pnguyen44)
- Rafael Benevides (@rafabene)
- Ciaran Roche (@ciaranRoche)
