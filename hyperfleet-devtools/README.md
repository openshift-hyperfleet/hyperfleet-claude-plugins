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

4. **Create Tracking Tickets**: Use `hyperfleet-jira:jira-ticket-creator` for doc updates
   ```
   /create-ticket
   # Based on the analysis report recommendations
   ```

5. **Commit & PR**: Submit linked PRs for code and documentation

## Roadmap

### v0.1.0 - ✅ Current Release
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

**Version**: 0.1.0
**Last Updated**: 2026-03-02
**Status**: ✅ Production Ready
