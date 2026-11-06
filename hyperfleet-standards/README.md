# HyperFleet Standards Plugin

A Claude Code plugin that audits HyperFleet repositories against team architecture standards.

## Features

### Standards Audit Skill (Auto-Activated)

The **HyperFleet Standards Audit** skill automatically activates when you ask about standards compliance. It performs a comprehensive audit and can deep-dive into specific standards when gaps are found.

- "audit this repo against standards"
- "does this repo follow hyperfleet standards?"
- "check standards compliance"
- "what standards gaps does this repo have?"
- "is this repo ready for production?"

### Key Capabilities

- **Dynamic Standards Discovery** - Delegates to the `hyperfleet-architecture` plugin to fetch standards, ensuring the skill stays current as standards evolve
- **Repository Type Detection** - Reads explicit repository metadata before heuristics, including plugin marketplaces, and retains multiple declared types
- **Parallel Deep-Dive** - Runs thorough checks per standard in parallel using dedicated agents
- **Interactive Output** - Paginated results with AskUserQuestion — never dumps the full report at once
- **Fix Gaps** - Can fix compliance gaps directly when the user chooses to

## Standards Checked

The skill dynamically fetches and audits against all standards in:
```text
https://github.com/openshift-hyperfleet/architecture/tree/main/hyperfleet/standards/
```

Current standards include:
- Commit Message Standard
- Configuration Standard
- Container Image Standard
- Dependency Pinning
- Directory Structure
- Error Model (RFC 9457)
- Generated Code Policy
- Graceful Shutdown
- Health Endpoints
- Helm Chart Conventions
- Linting Standard (golangci-lint)
- Logging Specification
- Makefile Conventions
- Metrics Standard
- Tracing Standard

## Installation

1. **Add the HyperFleet marketplace (if not already added):**

    ```text
    /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. **Install the standards plugin:**

    ```text
    /plugin install hyperfleet-standards@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. **Restart Claude Code** to load the plugin.

## Usage

### Run a Standards Audit

Navigate to any HyperFleet repository and ask:

```text
audit this repo against standards
```

The skill will:
1. Detect the repository type (API, Sentinel, Adapter, etc.)
2. Fetch the latest standards from the architecture repo
3. Run applicable checks
4. Generate a compliance report with gaps

### Interactive Flow

The audit is interactive and paginated:

1. **Summary** — shows a compliance table (PASS/PARTIAL/FAIL per standard)
2. **Choose a standard** — user picks which standard to inspect
3. **Detail** — shows the detailed findings for that standard
4. **Act** — user can fix a gap, create a ticket, inspect another standard, or finish

## Repository Type Detection

The skill automatically detects repo type based on:

| Repository Type | Indicators |
|-----------------|------------|
| Plugin marketplace | Explicit `.hyperfleet.yaml` declares `repository.types: [plugin-marketplace]` |
| API Service | `pkg/api/`, OpenAPI spec, database code |
| Sentinel | Directory name contains "sentinel", reconciliation loops |
| Adapter | Directory starts with "adapter-", CloudEvents usage |
| Infrastructure | Helm charts, Terraform files |
| Tooling | Go CLI without service patterns |

Explicit metadata takes precedence over heuristics, and requirements for multiple
types are additive. Plugin marketplaces use their own Makefile target set only
when the fetched architecture standard defines it; an unsupported type is
reported as partial instead of treated as a service. Go-only lint checks do not
apply to a marketplace without Go code.

## Testing

The repository lint regression suite requires Node.js 22 or newer, Python 3.9 or
newer, Bash, and the pinned npm/yamllint dependencies (see
[lint setup](../CONTRIBUTING.md#linting)). It is discovered by `make test`:

```bash
npm ci --ignore-scripts --no-fund --no-audit
python3 -m pip install -r requirements-lint.txt
bash hyperfleet-standards/tests/run-tests.sh
```

## Applicability Matrix

Not all standards apply to all repository types:

| Standard | API | Sentinel | Adapter | Infra | Tooling |
|----------|-----|----------|---------|-------|---------|
| Commit Messages | Yes | Yes | Yes | Yes | Yes |
| Configuration | Yes | Yes | Yes | No | Yes |
| Container Image | Yes | Yes | Yes | No | No |
| Dependency Pinning | Yes | Yes | Yes | No | Yes |
| Directory Structure | Yes | Yes | Yes | No | Yes |
| Error Model | Yes | Partial | Partial | No | No |
| Generated Code | If applicable | If applicable | If applicable | No | No |
| Graceful Shutdown | Yes | Yes | Yes | No | No |
| Health Endpoints | Yes | Yes | Yes | No | No |
| Helm Chart | Yes | Yes | Yes | Yes | No |
| Linting | Yes | Yes | Yes | No | Yes |
| Logging | Yes | Yes | Yes | No | Optional |
| Makefile | Yes | Yes | Yes | Yes | Yes |
| Metrics | Yes | Yes | Yes | No | No |
| Tracing | Yes | Yes | Yes | No | No |

## Offline Mode

If GitHub is unavailable, the skill falls back to the local architecture repository:

```text
[auto-detected local architecture repo path]
```

Ensure your local architecture repo is up to date for offline use.

### Standards Covered

Each standard has a dedicated deep-dive reference with specific checks:

- Configuration (config sources, env vars, validation)
- Container Image (Dockerfile, base images, labels)
- Dependency Pinning (.bingo/, tool isolation)
- Directory Structure (required dirs, .gitignore)
- Error Model (RFC 9457, error codes, wrapping, security)
- Graceful Shutdown (signals, drain, timeouts)
- Health Endpoints (paths, ports, probes, response format)
- Helm Chart (values.yaml, security posture, testing)
- Linting (.golangci.yml, required linters)
- Logging (structured logging, levels, fields, redaction)
- Makefile (targets, variables, build flags)
- Metrics (naming, labels, histogram buckets)
- Tracing (OTel, propagation, spans)

## Relationship with Operational Readiness

Some checks overlap with the [Operational Readiness](../hyperfleet-operational-readiness/README.md) plugin (health endpoints, graceful shutdown, metrics). The two plugins are complementary:

| Aspect | Standards Audit | Operational Readiness |
|--------|----------------|----------------------|
| Source | Dynamic (architecture repo) | Dynamic (architecture repo) |
| Focus | Code quality & conventions | Production reliability |
| Checks | Linting, commits, error model | Health probes, PDB, metrics |
| Perspective | Does the code follow the standard? | Does it work in production? |

A health probe can pass the standards audit (correct path and port) but fail operational readiness (returns 200 without checking the database). Run both before a release.

## Contributing

See the main [HyperFleet Claude Plugins README](../README.md) for contribution guidelines.

## Maintainers

- Ciaran Roche (@ciaranRoche)
