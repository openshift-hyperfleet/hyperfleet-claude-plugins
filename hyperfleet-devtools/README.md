# HyperFleet DevTools Plugin

Developer productivity tools for the HyperFleet team, designed to streamline development workflows and maintain consistency between code and architecture documentation.

## Overview

The HyperFleet DevTools plugin provides intelligent analysis and automation tools for HyperFleet developers. The current release focuses on architecture documentation impact analysis using a two-stage analysis approach for high accuracy and stability.

## Quick Start

**Zero setup required!** Just run the analyzer in any HyperFleet component repository:

```bash
/architecture-impact
```

The plugin will automatically:
1. Clone the architecture repository to cache (first run only)
2. Update architecture repository to latest (every run)
3. Analyze your code changes using two-stage analysis
4. Generate a detailed impact report with priorities

## Skills

### 🏗️ Architecture Impact Analyzer

**Status**: ✅ Production Ready (v0.1.0)

Analyzes code changes in all HyperFleet component repositories and determines if architecture documentation needs to be updated.

**Key Features**:
- ✅ **Zero Setup**: No configuration needed, works out of the box
- ✅ **Auto-Managed Architecture Repo**: Automatically clones and updates to cache
- ✅ **Two-Stage Analysis**: High recall (Stage 1) + high precision (Stage 2) = stable results
- ✅ **All Components Supported**: API, Sentinel, Adapter, Broker
- ✅ **Priority Classification**: MUST/SHOULD/COULD/WON'T (clear actionable priorities)
- ✅ **Git Commit Range Analysis**: Analyze PRs and feature branches
- ✅ **Breaking Change Detection**: Identifies API, config, and interface changes (7 patterns)
- ✅ **Change Classification**: Distinguishes refactoring from feature changes (8 types)
- ✅ **Severity Levels**: CRITICAL/HIGH/MEDIUM breaking change classification
- ✅ **Versioning Guidance**: Semantic version bump recommendations (MAJOR/MINOR/PATCH)
- ✅ **Specific Recommendations**: Actionable update suggestions with clear priorities

**Usage**:

In any HyperFleet component repository (hyperfleet-api, hyperfleet-sentinel, hyperfleet-adapter, hyperfleet-broker):

```bash
# Analyze uncommitted changes (default)
/architecture-impact

# Analyze a git commit range (e.g., your PR branch)
/architecture-impact --range main..HEAD

# Analyze last 5 commits
/architecture-impact --last 5
```

Or conversationally:
```
"analyze architecture impact"
"analyze impact --range main..feature-branch"
"check if docs need update for last 3 commits"
"should I update architecture docs?"
```

**Two-Stage Analysis Process** (v0.1.0):

1. **Stage 1 - Broad Search (High Recall)**
   - Extracts keywords from code changes using LLM
   - Grep searches all architecture documents
   - Finds all candidate documents (~15-20 documents)

2. **Stage 2a - Relevance Filtering (Cost Optimization)**
   - Reads first 200 lines of each candidate document
   - Fast LLM classification: RELEVANT / NOT_RELEVANT / UNCERTAIN
   - Filters to ~5-7 truly relevant documents

3. **Stage 2b - Deep Gap Analysis (High Precision)**
   - Full document analysis for RELEVANT documents only
   - 3 gap types: Implementation Added, Documentation Outdated, Inconsistency
   - Priority classification: MUST / SHOULD / COULD / WON'T
   - Detailed, actionable recommendations

**Output Example**:

```markdown
# Architecture Impact Analysis Report

**Repository**: hyperfleet-api
**Component**: API Service
**Analysis Method**: Two-Stage Analysis (v0.1.0)
**Changes Analyzed**: 1 file, 8 lines changed

**Analysis Statistics**:
- Stage 1 (Broad Search): 59 candidate documents found
- Stage 2a (Relevance Filter): 3 relevant documents identified
- Stage 2b (Deep Analysis): 3 documents analyzed for gaps

## Summary

**Impact Level**: LOW (Non-breaking change)
**Documentation Updates Required**: YES (1 document)

## Documentation Impact (MUST/SHOULD/COULD/WON'T Priority)

### 1. architecture-summary.md

**Priority**: SHOULD
**Gap Type**: Documentation Outdated (schema listing incomplete)

**Recommended Action**: Add Description field to clusters table schema
**Location**: Line 163 in architecture-summary.md

### 2. status-guide.md

**Priority**: COULD
**Gap Type**: Implementation Added (examples outdated)

**Note**: Document has disclaimer that examples are illustrative.
Updating is optional, not strictly required.

### 3. api-versioning.md

**Priority**: WON'T
**Gap Type**: None (policy already covers this case)

**Reason**: Existing policy already covers optional field additions in MINOR versions.
No update needed.
```

**When to Use**:
- ✅ Before submitting a PR that changes public APIs or interfaces
- ✅ After making data model or config schema changes
- ✅ When adding/removing endpoints or changing execution flows
- ✅ When modifying database schemas or Helm charts
- ✅ Before major refactorings that affect architecture
- ✅ During PR review to understand documentation impact
- ✅ When reviewing a feature branch before merging

**Works In All HyperFleet Repositories**:
- ✅ **hyperfleet-api**: REST API service (data models, endpoints, migrations)
- ✅ **hyperfleet-sentinel**: Polling/reconciliation service (config, decision engine, events)
- ✅ **hyperfleet-adapter**: Event-driven adapter framework (config, executors, status)
- ✅ **hyperfleet-broker**: Messaging library (interfaces, providers, config)

See [skills/architecture-impact/SKILL.md](./skills/architecture-impact/SKILL.md) for detailed documentation.

### Example Workflow

**Scenario**: You're adding a new field to `ClusterResponse` in the API

```bash
# 1. Make your code changes
vim pkg/api/cluster_types.go
# Add new field: Description string `json:"description,omitempty"`

# 2. Run impact analysis before committing
/architecture-impact
# Automatic architecture repo management + two-stage analysis

# 3. Review the report
# Output shows:
# - Stage 1: Found 59 candidate documents
# - Stage 2a: Filtered to 3 relevant documents
# - Stage 2b: 1 SHOULD update (architecture-summary.md)

# 4. Update architecture documentation
cd ~/.claude/plugins/cache/hyperfleet-devtools/architecture
vim hyperfleet/architecture/architecture-summary.md
# Add the new field to clusters table schema

# 5. Commit and submit PR
git add .
git commit -m "Add Description field to Cluster"
```

## Installation

This plugin is part of the HyperFleet Claude Plugins marketplace and is automatically available when you install the marketplace.

**Prerequisites**:
- Claude Code CLI
- Access to HyperFleet repositories
- Git installed
- Network access to clone architecture repository (first run only)

**Verify Installation**:

```bash
# List available skills
/help

# You should see:
# - hyperfleet-devtools:architecture-impact
```

## Configuration

**Zero configuration required!** The plugin automatically manages the architecture repository.

**Architecture Repository**:
- Location: `~/.claude/plugins/cache/hyperfleet-devtools/architecture/`
- First run: Automatically clones from GitHub
- Every run: Automatically updates (git pull) to latest

## Integration with Other HyperFleet Skills

**Recommended Workflow**:

1. **Before Coding**: Use `hyperfleet-architecture` skill to understand current architecture
   ```
   "explain hyperfleet API versioning policy"
   ```

2. **During Development**: Make code changes as usual

3. **Before Committing**: Use `architecture-impact` to check documentation impact
   ```
   /architecture-impact
   ```

4. **Create Tracking Tickets**: Use `hyperfleet-jira:jira-ticket-creator` for doc updates
   ```
   /create-ticket
   # Based on the analysis report recommendations
   ```

5. **Commit & PR**: Submit linked PRs for code and documentation

## Troubleshooting

### Error: "Not a HyperFleet repository"

**Cause**: You're not in a recognized HyperFleet component repository.

**Solution**:
```bash
# Navigate to a supported repository
cd /path/to/hyperfleet-api

# Try again
/architecture-impact
```

### Error: "Component not supported"

**Cause**: You're in a repository that's not a recognized HyperFleet component.

**Supported components**:
- hyperfleet-api
- hyperfleet-sentinel
- hyperfleet-adapter
- hyperfleet-broker

**Solution**: Navigate to one of the supported repositories and try again.

### Error: "No changes to analyze"

**Cause**: There are no uncommitted changes in the repository.

**Solution**: Make some code changes first, then run the analysis before committing.

Or use alternative analysis modes:
```bash
# Analyze a commit range
/architecture-impact --range main..HEAD

# Analyze last N commits
/architecture-impact --last 5
```

### Warning: "Architecture repository clone failed"

**Cause**: Network issue or GitHub access problem.

**Solution**:
```bash
# Ensure you have GitHub access
ssh -T git@github.com

# Try cloning manually
mkdir -p ~/.claude/plugins/cache/hyperfleet-devtools
cd ~/.claude/plugins/cache/hyperfleet-devtools
git clone https://github.com/openshift-hyperfleet/architecture.git

# Run analysis again
/architecture-impact
```

## Performance

**Two-Stage Analysis** optimizes for both quality and efficiency:
- **Stage 1 (Broad Search)**: Fast grep searches across all architecture documents
- **Stage 2a (Relevance Filter)**: Lightweight classification (reads first 200 lines only)
- **Stage 2b (Deep Analysis)**: Thorough analysis of relevant documents only

**What affects analysis scope**:
- Number of changed files and complexity
- Number of candidate documents found in Stage 1
- Number of RELEVANT documents identified in Stage 2a

**Optimization strategies**:
- Architecture repo is cached at `~/.claude/plugins/cache/hyperfleet-devtools/architecture/`
- Auto git pull ensures latest documentation
- Two-stage analysis focuses deep analysis on relevant documents only (typically 5-7 documents analyzed in depth)

## Roadmap

### v0.1.0 - ✅ Current Release (Initial Release)
- ✅ **All Components Supported**: API, Sentinel, Adapter, Broker
- ✅ **Zero Setup**: Automatic architecture repository management to cache
- ✅ **Two-Stage Analysis**: Stage 1 (Broad Search) → Stage 2a (Relevance Filter) → Stage 2b (Deep Analysis)
- ✅ **Priority Classification**: MUST/SHOULD/COULD/WON'T for clear action priorities
- ✅ **Consistent Results**: High recall (90%+) and precision (85%+) across multiple runs
- ✅ **Cost Optimization**: Deep analysis only on relevant documents (typically 5-7 documents)
- ✅ **Change Classification**: Distinguishes refactoring from feature changes (8 types)
- ✅ **Breaking Change Detection**: Identifies 7 breaking change patterns with CRITICAL/HIGH/MEDIUM severity
- ✅ **Versioning Guidance**: Semantic version bump recommendations (MAJOR/MINOR/PATCH)
- ✅ **Git Commit Range Analysis**: Support for `--range` and `--last` parameters

### v0.2.0 - 📋 Planned Q2 2026 (Workflow Integration)
- JIRA integration (auto-create doc update tickets)
- Plan Mode integration (draft documentation updates)
- Optional pre-commit hook
- GitHub Actions CI/CD integration

## Contributing

Contributions are welcome! This plugin follows HyperFleet plugin development standards.

**File Structure**:
```
hyperfleet-devtools/ (72KB, 6 files)
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── OWNERS                        # Maintainers
├── README.md                     # This file
├── agents/
│   └── architecture-doc-analyzer/
│       └── AGENT.md              # Two-stage analysis agent logic
└── skills/
    └── architecture-impact/
        ├── SKILL.md              # Skill definition
        └── ensure_arch_repo.sh   # Architecture repo management script
```

**Adding New Skills**:
1. Create skill directory under `skills/`
2. Add `SKILL.md` with frontmatter and instructions
3. Add agent if needed under `agents/`
4. Update this README

**Testing Changes**:
1. Make changes to skill/agent definitions
2. Test in a real HyperFleet repository
3. Verify output quality and accuracy
4. Check performance (analysis time)
5. Sync to cache: `rsync -av --delete . ~/.claude/plugins/cache/hyperfleet-claude-plugins/hyperfleet-devtools/0.5.0/`

## Support

**Issues**: Report bugs and feature requests in the HyperFleet DevTools issue tracker

**Questions**: Ask in the HyperFleet developer Slack channel

**Documentation**: See [skills/architecture-impact/SKILL.md](./skills/architecture-impact/SKILL.md) for detailed skill documentation

## License

Copyright Red Hat, Inc. - Internal tool for HyperFleet development

## Maintainers

See [OWNERS](./OWNERS) file for current maintainers and reviewers.

---

**Version**: 0.1.0 (Initial Release)
**Last Updated**: 2026-02-13
**Status**: ✅ Production Ready (All HyperFleet Components)
