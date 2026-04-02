# HyperFleet DevTools Plugin

Your AI-powered development companion for building HyperFleet projects with confidence.

## Overview

HyperFleet DevTools is a comprehensive development assistance plugin that helps you throughout the entire software development lifecycle. From writing code to reviewing changes, from maintaining standards to ensuring quality, DevTools provides intelligent automation and analysis to boost your productivity and code quality.

**What DevTools Does**:
- 🤖 **Automates repetitive tasks** so you can focus on solving problems
- 📋 **Enforces team standards** consistently across all repositories
- 🔍 **Analyzes code changes** for quality, impact, and compliance
- 💡 **Provides intelligent suggestions** based on HyperFleet best practices
- 🔗 **Keeps code and documentation in sync** automatically
- ✅ **Ensures readiness** before commits, PRs, and releases

## Quick Start

**Zero setup required!** Just invoke the tools you need:

```bash
# Generate a standardized commit message
/hyperfleet-devtools:commit-message

# Analyze architecture documentation impact
/hyperfleet-devtools:architecture-impact
```

DevTools automatically detects your repository context and provides relevant assistance. See the [Development Tools](#development-tools) section below for detailed usage.

## Development Tools

The following tools are currently available. More tools will be added in future releases to cover the full development lifecycle.

### 💬 Commit Message Generator

**Status**: ✅ Production Ready

Generates standardized commit messages following the [HyperFleet Commit Standard](https://github.com/openshift-hyperfleet/architecture/blob/main/hyperfleet/standards/commit-standard.md).

**What It Does**:
- Auto-detects JIRA ticket from branch name
- Suggests appropriate commit type based on code changes
- Validates message format (72 character limit)
- Ensures consistency across the team

**Usage**:

```bash
# Auto-detect everything
/hyperfleet-devtools:commit-message

# Specify commit type
/hyperfleet-devtools:commit-message refactor

# Specify both type and ticket
/hyperfleet-devtools:commit-message refactor HYPERFLEET-456
```

See [commands/commit-message.md](./commands/commit-message.md) for detailed documentation.

---

### 🏗️ Architecture Impact Analyzer

**Status**: ✅ Production Ready

Analyzes code changes and determines if architecture documentation needs to be updated.

**What It Does**:
- Detects when your code changes require documentation updates
- Prioritizes documentation gaps (MUST/SHOULD/COULD/WON'T)
- Identifies breaking changes and suggests version bumps
- Works with all HyperFleet component repositories

**Usage**:

```bash
# Analyze uncommitted changes
/hyperfleet-devtools:architecture-impact

# Analyze a git commit range
/hyperfleet-devtools:architecture-impact --range main..HEAD

# Analyze last N commits
/hyperfleet-devtools:architecture-impact --last 5
```

See [skills/architecture-impact/SKILL.md](./skills/architecture-impact/SKILL.md) for detailed documentation.

---

### 🧪 E2E Test Case Designer

**Status**: ✅ Production Ready

Designs black-box E2E test cases for HyperFleet features using systematic test design techniques.

**What It Does**:
- Builds traceability matrices mapping acceptance criteria to existing test coverage
- Identifies coverage gaps with risk-based prioritization (likelihood x blast radius)
- Applies formal test design techniques (State Transition, Decision Table, Failure Mode Analysis)
- Filters false positive candidates using 4-stage pre-filter (scope boundary, implicit coverage, third-party internals, design-time guarantees)
- Generates Jira-ready gap specifications for uncovered acceptance criteria

**Usage**:

```bash
# Design test cases for a Jira epic
"design E2E test cases for HYPERFLEET-559"
```

See [skills/e2e-test-design/SKILL.md](./skills/e2e-test-design/SKILL.md) for detailed documentation.

---

### ⚙️ E2E Test Automation

**Status**: ✅ Production Ready

Implements E2E test automation code from designed test case documents. Generates Ginkgo/Gomega test code following project conventions.

**What It Does**:
- Reads designed test case documents (markdown with manual test commands)
- **Prefers to translate commands to API client calls** (kubectl → client-go, curl → HTTP client, etc.)
- Generates production-ready Ginkgo/Gomega test code following best practices
- Uses existing helper utilities and follows project patterns
- Ensures generated code compiles successfully
- Handles setup, teardown, assertions, and error handling
- **Asks user when operations are complex**: create helper, use API directly, or use command

**Usage**:

```bash
# Implement test from test case document
"implement test from test-design/testcases/cluster.md"

# Implement specific test by title
"implement the 'Basic Workflow Validation' test from cluster.md"

# Update existing automated test when test case steps changed
"update the automated test for 'Basic Workflow Validation' from cluster.md"

# Add test to existing file
"add the adapter failure test to e2e/cluster/adapter_failure.go"
```

**Best Practice Workflow**:
1. Design test cases using `e2e-test-design` skill
2. Review and approve the test case document
3. Use this skill to implement the test automation
4. Review generated code and run tests
5. Commit both test design and implementation together

See [skills/e2e-test-automation/SKILL.md](./skills/e2e-test-automation/SKILL.md) for detailed documentation.

## Installation

This plugin is part of the HyperFleet Claude Plugins marketplace and is automatically available when you install the marketplace.

**Prerequisites**:
- Claude Code CLI
- Access to HyperFleet repositories
- Git installed

**Verify Installation**:

```bash
# List available tools
/help

# You should see:
# - hyperfleet-devtools:commit-message
# - hyperfleet-devtools:architecture-impact
# - hyperfleet-devtools:e2e-test-design
# - hyperfleet-devtools:e2e-test-automation
```

## Configuration

**Zero configuration required!** All tools work out of the box.

## Integration with Other HyperFleet Skills

**Recommended Development Workflow**:

1. **Before Coding**: Use `hyperfleet-architecture` skill to understand current architecture
   ```
   "explain hyperfleet API versioning policy"
   ```

2. **During Development**: Make code changes as usual

3. **Before Committing**: Check architecture impact and generate commit message
   ```bash
   # Check if documentation needs updates
   /hyperfleet-devtools:architecture-impact

   # Generate standardized commit message
   /hyperfleet-devtools:commit-message
   ```

4. **Create Tracking Tickets**: Ask to create tickets for any documentation updates — the `jira-ticket-creator` skill auto-activates when you request ticket creation

5. **Commit & PR**: Submit linked PRs for code and documentation

## Roadmap

### v0.5.0 - Current Release
- ✅ **E2E Test Automation**: Generate Ginkgo/Gomega test code from designed test case documents
- ✅ **E2E Test Case Designer**: Systematic E2E test case design with traceability, risk assessment, and coverage verification
- ✅ **Commit Message Generator**: Auto-generate standardized commit messages with JIRA ticket detection
- ✅ **Architecture Impact Analyzer**: Detect when code changes require documentation updates

## Contributing

Contributions are welcome! This plugin follows HyperFleet plugin development standards.

**File Structure**:
```
hyperfleet-devtools/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── OWNERS                        # Maintainers
├── README.md                     # This file
├── commands/                     # Command definitions
├── agents/                       # Agent definitions
└── skills/                       # Skill definitions
```

**Adding New Tools**:
1. Create command/skill directory under appropriate folder
2. Add definition file with frontmatter and instructions
3. Update this README
4. Test in a real HyperFleet repository

## Support

**Issues**: Report bugs and feature requests in the HyperFleet DevTools issue tracker

**Questions**: Ask in the HyperFleet developer Slack channel

## License

Copyright Red Hat, Inc. - Internal tool for HyperFleet development

## Maintainers

See [OWNERS](./OWNERS) file for current maintainers and reviewers.

---

**Version**: 0.5.0
**Last Updated**: 2026-04-02
**Status**: ✅ Production Ready
