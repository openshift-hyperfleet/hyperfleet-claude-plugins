# HyperFleet Standards Plugin

A Claude Code plugin that audits HyperFleet repositories against team architecture standards.

## Features

### Standards Audit Skill (Auto-Activated)

The **HyperFleet Standards Audit** skill automatically activates when you ask about standards compliance:

- "audit this repo against standards"
- "does this repo follow hyperfleet standards?"
- "check standards compliance"
- "what standards gaps does this repo have?"
- "is this repo ready for production?"

### Key Capabilities

- **Dynamic Standards Discovery** - Fetches standards from the architecture repo (GitHub with local fallback), ensuring the skill stays current as standards evolve
- **Repository Type Detection** - Automatically identifies if the repo is an API, Sentinel, Adapter, Infrastructure, or Tooling project
- **Comprehensive Audit** - Checks against all applicable standards based on repo type
- **JIRA Integration** - Produces gap specifications in JIRA wiki markup, ready for use with `jira-ticket-creator`
- **Read-Only** - Never modifies any files in the audited repository

## Standards Checked

The skill dynamically fetches and audits against all standards in:
```
https://github.com/openshift-hyperfleet/architecture/tree/main/hyperfleet/standards/
```

Current standards include:
- Commit Message Standard
- Linting Standard (golangci-lint)
- Makefile Conventions
- Error Model (RFC 9457)
- Graceful Shutdown
- Health Endpoints
- Logging Specification
- Metrics Standard
- Generated Code Policy

## Installation

1. **Add the HyperFleet marketplace (if not already added):**
   ```
   /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. **Install the standards plugin:**
   ```
   /plugin install hyperfleet-standards@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Run a Standards Audit

Navigate to any HyperFleet repository and ask:

```
audit this repo against standards
```

The skill will:
1. Detect the repository type (API, Sentinel, Adapter, etc.)
2. Fetch the latest standards from the architecture repo
3. Run applicable checks
4. Generate a compliance report with gaps

### Output Format

The audit produces:

**Summary Table:**
```markdown
| Standard | Status | Severity | Gaps |
|----------|--------|----------|------|
| Linting  | PARTIAL | Major   | 1    |
```

**Detailed Findings:**
- Per-standard check results
- Specific gaps with file locations
- Remediation guidance

**JIRA-Ready Gap Specifications:**
- Pre-formatted ticket specs for `jira-ticket-creator`
- Includes What/Why/Acceptance Criteria
- Story points and priority recommendations

### Create Tickets for Gaps

After reviewing the audit report, create JIRA tickets:

```
create a ticket for GAP-LNT-001
```

Or bulk create:

```
create tickets for all critical gaps
```

## Repository Type Detection

The skill automatically detects repo type based on:

| Repository Type | Indicators |
|-----------------|------------|
| API Service | `pkg/api/`, OpenAPI spec, database code |
| Sentinel | Directory name contains "sentinel", reconciliation loops |
| Adapter | Directory starts with "adapter-", CloudEvents usage |
| Infrastructure | Helm charts, Terraform files |
| Tooling | Go CLI without service patterns |

## Applicability Matrix

Not all standards apply to all repository types:

| Standard | API | Sentinel | Adapter | Infra | Tooling |
|----------|-----|----------|---------|-------|---------|
| Commit Messages | Yes | Yes | Yes | Yes | Yes |
| Linting | Yes | Yes | Yes | No | Yes |
| Makefile | Yes | Yes | Yes | Yes | Yes |
| Error Model | Yes | Partial | Partial | No | No |
| Graceful Shutdown | Yes | Yes | Yes | No | No |
| Health Endpoints | Yes | Yes | Yes | No | No |
| Logging | Yes | Yes | Yes | No | Optional |
| Metrics | Yes | Yes | Yes | No | No |
| Generated Code | If applicable | If applicable | If applicable | No | No |

## Offline Mode

If GitHub is unavailable, the skill falls back to the local architecture repository:
```
/home/croche/Projects/hyperfleet/architecture/hyperfleet/standards/
```

Ensure your local architecture repo is up to date for offline use.

## Contributing

See the main [HyperFleet Claude Plugins README](../README.md) for contribution guidelines.

## Maintainers

- Ciaran Roche (@ciaranRoche)
- Alex Vulaj (@AlexVulaj)
