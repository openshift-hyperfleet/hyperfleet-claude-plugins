# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A Claude Code **plugin marketplace** for the HyperFleet team. Each top-level directory (except `.claude-plugin/`) is a standalone plugin that gets installed by team members via `/plugin install <name>@openshift-hyperfleet/hyperfleet-claude-plugins`.

There is no build system, no tests, no compiled code. The codebase is entirely Markdown (SKILL.md, AGENT.md, command files) and JSON (plugin.json, marketplace.json).

## Repository Architecture

```
.claude-plugin/marketplace.json   <- marketplace registry (lists all plugins)
hyperfleet-<name>/                <- each plugin
├── .claude-plugin/plugin.json    <- plugin metadata (name, version, description)
├── skills/                       <- skill definitions (SKILL.md with frontmatter)
├── commands/                     <- slash command definitions (.md files)
├── agents/                       <- agent definitions (AGENT.md)
└── README.md
```

### Plugin Types

| Plugin | Purpose | Has Skills | Has Commands | Has Agents |
|--------|---------|:---:|:---:|:---:|
| `hyperfleet-code-review` | Local and PR review workflows | `/review-pr, /review-local` | - | - |
| `hyperfleet-jira` | JIRA integration | 3 skills | 5 commands | - |
| `hyperfleet-architecture` | Architecture docs Q&A | 1 skill | - | - |
| `hyperfleet-standards` | Standards audit with deep-dive reviews | 1 skill | - | - |
| `hyperfleet-operational-readiness` | Operational readiness audit | 1 skill | - | - |
| `hyperfleet-devtools` | Dev productivity | 1 skill | 1 command | 1 agent |
| `hyperfleet-adapter-authoring` | Adapter authoring | 1 skill | - | - |
| `hyperfleet-work-triage` | Work triage (bugs, issues, PR prioritization) | 2 skills | - | - |

### Key Plugin: `hyperfleet-code-review`

- **`/review-pr`** — full PR review with 6 steps: input validation, data gathering, JIRA check, parallel analysis (10 groups of mechanical code checks), consistency check, interactive output. Uses `output-format.md` and `group-01` through `group-10` check definitions.
- **`/review-local`** — local branch review against HyperFleet standards. Uses check definitions from `checks/` and reference data from `config/`.

### Key Plugin: `hyperfleet-work-triage`

- **`/bugs-triage`** — interactive JIRA bug triage (New→Backlog) and GitHub issue triage for openshift-hyperfleet repositories. Uses shared `references/github-repos.md` for repo scope.
- **`/open-prs`** — surfaces and prioritizes open PRs across the org using 8-factor weighted scoring (JIRA priority, blocking impact, staleness, risk, review progress, size, CI status, story points) with confidence levels. Uses `prioritization-algorithm.md` for scoring rubrics and `output-format.md` for tiered presentation. Shares `references/github-repos.md` with `/bugs-triage`.

## Conventions

### Skill Format (Skills 2.0)

Skills use `SKILL.md` with YAML frontmatter:

```yaml
---
name: skill-name
description: What it does
allowed-tools: Bash, Read, Grep, Glob, Agent, Skill
argument-hint: <arg-description>
---
```

Dynamic context uses `!` backtick syntax to run shell commands at skill load time (NOT at Bash tool runtime).

### Versioning

Each plugin has its own version in `.claude-plugin/plugin.json` following semver. **Always bump the version when making changes to a plugin.** The marketplace registry (`.claude-plugin/marketplace.json`) does not track versions.

### Branch Convention

Use JIRA ticket IDs as branch names (e.g., `HYPERFLEET-703`). Include the ticket ID in commit messages.

### OWNERS

k8s-style OWNERS files control PR approval. Approvers comment `/approve` to merge.

## Common Operations

### Adding a new plugin

1. Create the directory structure under `hyperfleet-<name>/`
2. Add `.claude-plugin/plugin.json` with name, version, description
3. Add the plugin entry to `.claude-plugin/marketplace.json`
4. Add an `OWNERS` file

### Modifying an existing plugin

1. Edit the relevant files (SKILL.md, command .md, etc.)
2. Bump the version in that plugin's `.claude-plugin/plugin.json`
3. Update the plugin's README.md if features changed

### Testing a plugin locally

There is no test suite. To test, install the plugin locally in Claude Code and invoke the skill/command manually.
