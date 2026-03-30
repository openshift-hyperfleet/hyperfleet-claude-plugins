# Audit Report Output Format

## Audit Report Structure

```markdown
# HyperFleet Operational Readiness Audit Report

**Repository:** [repo name]
**Path:** [full path]
**Repository Type:** [API/Sentinel/Adapter/Infrastructure/Tooling]
**Audit Date:** [ISO timestamp]
**Requirements Source:** HYPERFLEET-539

---

## Summary

| Check | Status | Severity | Applicable |
|-------|--------|----------|------------|
| Functional Health Probes | PASS/PARTIAL/FAIL | Critical | Yes/No |
| Dead Man's Switch Metrics | PASS/PARTIAL/FAIL | Critical | Yes/No |
| Retry Logic with Backoff | PASS/PARTIAL/FAIL | Major | Yes/No |
| PodDisruptionBudget | PASS/PARTIAL/FAIL | Major | Yes/No |
| Resource Limits | PASS/PARTIAL/FAIL | Major | Yes/No |
| Graceful Shutdown | PASS/PARTIAL/FAIL | Critical | Yes/No |
| Reliability Documentation | PASS/PARTIAL/FAIL | Minor | Yes/No |

**Overall Operational Readiness:** X/Y checks passing (Z%)

---

## Detailed Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL
**Severity:** Critical/Major/Minor
**Applicable:** Yes/No (reason if No)

#### Evidence Found
- [File path:line - what was found]

#### Gaps Found (if any)
- **Location:** [file path:line number or N/A]
- **Expected:** [what operational readiness requires]
- **Found:** [what was actually found]
- **Remediation:** [how to fix]

---

## Recommendations

**Critical Issues (address before production):**
1. [Issue description and remediation]

**Major Issues (address soon):**
1. [Issue description and remediation]

**Minor Issues (address when convenient):**
1. [Issue description and remediation]
```
