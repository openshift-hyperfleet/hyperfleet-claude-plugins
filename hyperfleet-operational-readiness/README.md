# HyperFleet Operational Readiness Plugin

A Claude Code plugin that audits HyperFleet repositories for operational readiness based on HYPERFLEET-539 requirements.

## Features

### Operational Readiness Audit Skill (Auto-Activated)

The **HyperFleet Operational Readiness Audit** skill automatically activates when you ask about operational readiness:

- "check operational readiness"
- "is this repo operationally ready?"
- "audit for production readiness"
- "what operational gaps does this repo have?"
- "is this service ready for production operations?"

### Key Capabilities

- **7 Operational Checks** - Comprehensive audit of production readiness requirements
- **Repository Type Detection** - Automatically identifies repo type and applies relevant checks
- **Severity Classification** - Critical, Major, and Minor severity levels
- **Read-Only** - Never modifies any files in the audited repository

## Operational Checks

Based on HYPERFLEET-539 requirements:

| Check | Severity | What it Verifies |
|-------|----------|------------------|
| Functional Health Probes | Critical | `/healthz`, `/readyz` verify actual dependencies (DB, broker) |
| Dead Man's Switch Metrics | Critical | Heartbeat/timestamp metrics for silent failure detection |
| Retry Logic with Backoff | Major | HTTP/broker clients use exponential backoff |
| PodDisruptionBudget | Major | PDB template exists in Helm chart |
| Resource Limits | Major | CPU/memory requests and limits in values.yaml |
| Graceful Shutdown | Critical | Signal handling, drain before stop |
| Reliability Documentation | Minor | Runbooks, metrics docs, operational guides |

## Applicability Matrix

Not all checks apply to all repository types:

| Check | API | Sentinel | Adapter | Infra | Tooling |
|-------|-----|----------|---------|-------|---------|
| Health Probes | Yes | Yes | Yes | No | No |
| Dead Man's Switch | Optional | **CRITICAL** | Yes | No | No |
| Retry Logic | Yes | Yes | Yes | No | No |
| PDB | Yes | Yes | Yes | Yes | No |
| Resource Limits | Yes | Yes | Yes | Yes | No |
| Graceful Shutdown | Yes | Yes | Yes | No | No |
| Reliability Docs | Yes | Yes | Yes | Partial | No |

**Note:** Dead Man's Switch metrics are **CRITICAL** for Sentinel services - silent failures that don't crash are the most dangerous failure mode for background processing services.

## Installation

1. **Add the HyperFleet marketplace (if not already added):**
   ```
   /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. **Install the operational readiness plugin:**
   ```
   /plugin install hyperfleet-operational-readiness@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Run an Operational Readiness Audit

Navigate to any HyperFleet repository and ask:

```
check operational readiness
```

The skill will:
1. Detect the repository type (API, Sentinel, Adapter, etc.)
2. Run applicable operational checks
3. Generate a compliance report with gaps
4. Provide remediation recommendations

### Output Format

The audit produces:

**Summary Table:**
```markdown
| Check | Status | Severity | Applicable |
|-------|--------|----------|------------|
| Dead Man's Switch Metrics | FAIL | Critical | Yes |
```

**Detailed Findings:**
- Per-check results with evidence
- Specific gaps with file locations
- Remediation guidance

**Recommendations:**
- Prioritized list of issues to address
- Grouped by severity (Critical, Major, Minor)

## Repository Type Detection

The skill automatically detects repo type based on:

| Repository Type | Indicators |
|-----------------|------------|
| API Service | `pkg/api/`, OpenAPI spec, database code |
| Sentinel | Directory name contains "sentinel", reconciliation loops |
| Adapter | Directory starts with "adapter-", CloudEvents usage |
| Infrastructure | Helm charts, Terraform files |
| Tooling | Go CLI without service patterns |

## Comparison with Standards Audit

| Aspect | Standards Audit | Operational Readiness |
|--------|----------------|----------------------|
| Source | Dynamic (architecture repo) | Hardcoded (HYPERFLEET-539) |
| Focus | Code quality & conventions | Production reliability |
| Checks | Linting, commits, error model | Health probes, PDB, metrics |
| Changes | Updates as standards evolve | Stable core requirements |

**Use both together** for comprehensive pre-production validation.

## Contributing

See the main [HyperFleet Claude Plugins README](../README.md) for contribution guidelines.

## Maintainers

- Ciaran Roche (@ciaranRoche)
