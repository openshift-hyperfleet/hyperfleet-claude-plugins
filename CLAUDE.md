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
| `hyperfleet-code-review` | PR review workflow | `/review-pr` | - | - |
| `hyperfleet-jira` | JIRA integration | 3 skills | 5 commands | - |
| `hyperfleet-architecture` | Architecture docs Q&A | 1 skill | - | - |
| `hyperfleet-standards` | Standards audit with deep-dive reviews | 1 skill | - | - |
| `hyperfleet-operational-readiness` | Operational readiness audit | 1 skill | - | - |
| `hyperfleet-devtools` | Dev productivity | 1 skill | 1 command | 1 agent |
| `hyperfleet-adapter-authoring` | Adapter authoring | 1 skill | - | - |

### Key Plugin: `hyperfleet-code-review`

The most complex plugin. Its review-pr skill has three files that work together:
- `SKILL.md` — main workflow (6 steps: input validation, data gathering, JIRA check, parallel analysis, consistency check, output)
- `mechanical-passes.md` — 10 groups of automated code checks (error handling & wrapping, concurrency, exhaustiveness, resource lifecycle, code quality, testing & coverage, naming & organization, security, code hygiene, performance)
- `output-format.md` — interactive pagination format and notification behavior

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
