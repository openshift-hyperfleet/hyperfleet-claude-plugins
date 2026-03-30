---
name: operational-readiness-audit
description: Audits local HyperFleet repositories for operational readiness based on HYPERFLEET-539 requirements. Checks health probes, dead man's switch metrics, retry logic, PDB, resource limits, graceful shutdown, and reliability documentation. READ-ONLY - does not modify any files.
---

# HyperFleet Operational Readiness Audit Skill

## CRITICAL: READ-ONLY MODE

**This skill MUST NOT modify any files in the repository being audited.** All operations are read-only analysis. The skill produces reports but never changes code, configuration, or documentation.

## When to Use This Skill

Activate this skill when the user:
- Asks to "check operational readiness"
- Asks "is this repo operationally ready?"
- Asks to "audit for production readiness"
- Asks "what operational gaps does this repo have?"
- Asks to "run an operational readiness check"
- Asks about "production readiness"
- Asks "is this service ready for production operations?"
- Asks to "validate operational requirements"

## Operational Readiness Requirements Source

These checks are based on **HYPERFLEET-539** requirements for operational readiness. Unlike the standards-audit skill which dynamically fetches standards, these operational requirements are hardcoded as they represent core reliability requirements that rarely change.

## Repository Type Detection

Before running applicable checks, detect the repository type.

### Detection Commands

```bash
# Check for API indicators
ls pkg/api/ 2>/dev/null && echo "HAS_API_PKG"
ls openapi.yaml 2>/dev/null || ls openapi/openapi.yaml 2>/dev/null && echo "HAS_OPENAPI"
grep -l "database" cmd/*.go 2>/dev/null && echo "HAS_DATABASE"

# Check for Sentinel indicators
basename $(pwd) | grep -i sentinel && echo "IS_SENTINEL"
grep -r "polling\|reconcile" --include="*.go" -l 2>/dev/null | head -1 && echo "HAS_RECONCILE"

# Check for Adapter indicators
basename $(pwd) | grep "^adapter-" && echo "IS_ADAPTER"
grep -r "cloudevents\|pubsub" --include="*.go" -l 2>/dev/null | head -1 && echo "HAS_CLOUDEVENTS"

# Check for Infrastructure
ls charts/Chart.yaml 2>/dev/null || ls Chart.yaml 2>/dev/null && echo "HAS_HELM"
ls *.tf 2>/dev/null && echo "HAS_TERRAFORM"

# Check for Go code
ls cmd/*.go 2>/dev/null || ls pkg/**/*.go 2>/dev/null && echo "IS_GO_REPO"
```

### Repository Type Matrix

| Indicators | Repository Type |
|------------|-----------------|
| HAS_API_PKG + HAS_OPENAPI + HAS_DATABASE | API Service |
| IS_SENTINEL or HAS_RECONCILE | Sentinel |
| IS_ADAPTER or HAS_CLOUDEVENTS (without API) | Adapter |
| HAS_HELM or HAS_TERRAFORM (without Go) | Infrastructure |
| IS_GO_REPO (without service patterns) | Tooling |

## Operational Readiness Checks

There are 7 checks, each with severity, applicability rules, commands, and pass/fail criteria. See the full specifications in [references/checks.md](references/checks.md).

### Check Summary

| # | Check | Severity |
|---|-------|----------|
| 1 | Functional Health Probes | Critical |
| 2 | Dead Man's Switch Metrics | Critical |
| 3 | Retry Logic with Exponential Backoff | Major |
| 4 | PodDisruptionBudget | Major |
| 5 | Resource Limits | Major |
| 6 | Graceful Shutdown | Critical |
| 7 | Reliability Documentation | Minor |

## Applicability Matrix

| Check | API | Sentinel | Adapter | Infrastructure | Tooling |
|-------|-----|----------|---------|----------------|---------|
| Functional Health Probes | Yes | Yes | Yes | No | No |
| Dead Man's Switch Metrics | Optional | **CRITICAL** | Yes | No | No |
| Retry Logic with Backoff | Yes | Yes | Yes | No | No |
| PodDisruptionBudget | Yes | Yes | Yes | Yes | No |
| Resource Limits | Yes | Yes | Yes | Yes | No |
| Graceful Shutdown | Yes | Yes | Yes | No | No |
| Reliability Documentation | Yes | Yes | Yes | Partial | No |

## Audit Execution

### For Each Applicable Check

1. **Determine applicability** based on repository type
2. **Execute check commands** listed in [references/checks.md](references/checks.md)
3. **Evaluate results** against pass/fail criteria
4. **Record status** as PASS, PARTIAL, or FAIL
5. **Document specific gaps** with file locations and remediation

## Output Format

Follow the report structure defined in [references/output-format.md](references/output-format.md). The report must include:

- Header with repository name, path, type, date, and requirements source
- Summary table with all checks, statuses, severities, and applicability
- Overall readiness percentage
- Detailed findings per check with evidence and gaps
- Recommendations grouped by severity (Critical, Major, Minor)

For a complete example of the expected output, see [references/example-audit.md](references/example-audit.md).

## Error Handling

If the skill cannot complete an audit:

1. **Unknown repo type:** Ask user to specify or default to "Tooling" (most restrictive)
2. **No Helm chart:** Skip Helm-related checks and note in report
3. **No Go code:** Skip code-based checks and note in report
4. **Partial checks:** Report which checks could not be performed

Always provide partial results where possible and suggest manual verification steps for incomplete checks.

## Notes

- This skill is **READ-ONLY** - it never modifies files
- Requirements are **hardcoded** based on HYPERFLEET-539 (not dynamically fetched)
- Severity ratings: Critical > Major > Minor
- Repository type affects which checks apply
- **Sentinel services have stricter requirements** for dead man's switch metrics
- All checks include file locations and specific remediation guidance
- You can ask to create tickets for any gaps found — the `jira-ticket-creator` skill auto-activates when you request ticket creation

## References

- [references/checks.md](references/checks.md) - Detailed specifications for all 7 operational readiness checks, including commands, pass/fail criteria, and applicability
- [references/output-format.md](references/output-format.md) - Template structure for the audit report output
- [references/example-audit.md](references/example-audit.md) - Complete example of an audit session with a Sentinel repository
