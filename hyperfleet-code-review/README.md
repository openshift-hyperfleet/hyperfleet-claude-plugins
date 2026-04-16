# HyperFleet Code Review Plugin

A Claude Code plugin that provides a standardized, interactive PR review workflow for the HyperFleet team.

## Features

### Skills
- **`/review-pr <PR>`** - Comprehensive PR review with interactive recommendations

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
- Supports non-interactive CI mode (`CI=true`) — posts inline comments directly on the PR
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

- **CI mode**: Activated when `CI=true` is set in the environment. Posts all recommendations as inline comments on the PR without interactive prompts. See [CI Integration](#ci-integration) for details.
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
```

## CI Integration

The `/review-pr` skill supports non-interactive CI mode for automated PR reviews in Prow jobs or other CI systems. When `CI=true` is set, the skill posts all recommendations directly as inline comments on the PR instead of using interactive pagination.

### How It Works

1. The skill detects `CI=true` in the environment
2. All analysis steps run as normal (JIRA validation, architecture checks, mechanical checks, etc.)
3. Each recommendation is posted as an **inline review comment** on the exact file and line in the PR diff
4. Impact warnings are posted as a single **general PR comment**
5. If no issues are found, a "no issues found" comment is posted
6. The skill exits without any interactive prompts

### Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CI` | Yes | Set to `true` to enable CI mode |
| `ANTHROPIC_VERTEX_PROJECT_ID` | Yes | GCP project ID for Vertex AI (e.g., `itpc-gcp-hcm-pe-eng-claude`) |
| `ANTHROPIC_MODEL` | Yes | Claude model for review (e.g., `claude-opus-4-6@default`) |
| `ANTHROPIC_SMALL_FAST_MODEL` | Yes | Claude model for sub-agents (e.g., `claude-sonnet-4@20250514`) |
| `GH_TOKEN` | Yes | GitHub token with `repo` scope for posting PR comments |
| `JIRA_API_TOKEN` | No | JIRA API token for ticket validation (skipped if jira CLI is not configured) |
| `JIRA_AUTH_TYPE` | No | Set to `bearer` when using `JIRA_API_TOKEN` |
| `JIRA_SERVER` | No | JIRA instance URL (e.g., `https://redhat.atlassian.net`). Required together with `JIRA_API_TOKEN` for JIRA validation |

### Example: Prow Job

```yaml
- name: pr-review
  agent: kubernetes
  decorate: true
  always_run: true
  timeout: 15m
  spec:
    containers:
    - image: <claude-code-image>
      command:
      - /bin/sh
      args:
      - -c
      - |
        claude -p "/review-pr $(REPO_OWNER)/$(REPO_NAME)#$(PULL_NUMBER)" \
          --output-format stream-json --verbose | \
          jq -r '
            if .type == "assistant" then
              .message.content[] |
              if .type == "text" then .text
              elif .type == "tool_use" then
                "⚙ \(.name): \(.input.description // .input.prompt // .input.file_path // .input.skill // .input.command // .input.pattern // "" | split("\n")[0] | .[0:120])"
              else empty
              end
            else empty
            end
          ' || echo "CI review failed (non-blocking)"
      env:
      - name: CI
        value: "true"
      - name: ANTHROPIC_VERTEX_PROJECT_ID
        value: "itpc-gcp-hcm-pe-eng-claude"
      - name: ANTHROPIC_MODEL
        value: "claude-opus-4-6@default"
      - name: ANTHROPIC_SMALL_FAST_MODEL
        value: "claude-sonnet-4@20250514"
      - name: GH_TOKEN
        valueFrom:
          secretKeyRef:
            name: github-token
            key: token
      - name: JIRA_SERVER
        value: "https://redhat.atlassian.net"
      - name: JIRA_API_TOKEN
        valueFrom:
          secretKeyRef:
            name: jira-credentials
            key: api-token
      - name: JIRA_AUTH_TYPE
        value: bearer
```

### Testing CI Mode Locally

Plain `-p` buffers all output until the end. Use `--output-format stream-json --verbose` piped through `jq` to see streaming progress:

```bash
CI=true claude -p "/review-pr openshift-hyperfleet/some-repo#123" \
  --output-format stream-json --verbose | \
  jq -r '
    if .type == "assistant" then
      .message.content[] |
      if .type == "text" then .text
      elif .type == "tool_use" then
        "⚙ \(.name): \(.input.description // .input.prompt // .input.file_path // .input.skill // .input.command // .input.pattern // "" | split("\n")[0] | .[0:120])"
      else empty
      end
    else empty
    end
  '
```

Verify that:

1. Inline comments were posted on the PR (check the PR's "Files changed" tab)
2. No interactive prompts appeared in the terminal
3. The terminal shows progress lines like `⚙ Bash: Fetch PR details`, `⚙ Agent: Security checks`, etc.
4. The terminal shows: `CI review started: reviewing <PR-URL>...` and `CI review complete: N recommendations posted ...`

### Known Limitations

- **No self-review fixes** — the `fix` command is not available; CI mode is read-only and only posts comments
- **No comment posting confirmation** — all comments are posted automatically without user confirmation
- **No review comment responses** — existing reviewer comments are not processed or replied to
- **No follow-up ticket creation** — JIRA ticket creation for impact warnings is skipped
- **Inline comment failures** — if a line is not part of the diff (e.g., context-only lines), the comment falls back to a general PR comment with file and line reference
- **Testing** — since the plugin is Markdown-only with no compiled code, CI mode is tested manually by invoking the skill with `CI=true` set in the environment

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
