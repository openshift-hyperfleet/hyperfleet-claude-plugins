---
name: HyperFleet Operational Readiness Audit
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

### Check 1: Functional Health Probes

**Severity:** Critical
**Requirement:** Health and readiness endpoints must verify actual dependencies (database, message broker, external services), not just return 200 OK.

**Applies to:** API, Sentinel, Adapter
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. Health endpoint exists (`/healthz` or `/health`)
2. Readiness endpoint exists (`/readyz` or `/ready`)
3. Health checks verify actual dependencies:
   - Database connectivity
   - Message broker connectivity
   - Critical external service availability

**Check commands:**
```bash
# Check for health endpoints
grep -r "/healthz\|/health\|/readyz\|/ready" --include="*.go" -l 2>/dev/null

# Check if health checks verify dependencies (not just returning OK)
grep -r "healthz\|readyz" --include="*.go" -A 20 2>/dev/null | grep -i "ping\|check\|db\|database\|broker\|connect"
```

**Pass criteria:**
- Health endpoints exist
- Endpoints contain actual dependency checks (not just `return 200`)

**Fail indicators:**
- No health endpoints found
- Health handlers only return static OK without checking dependencies
- Missing readiness probe separate from liveness

---

### Check 2: Dead Man's Switch Metrics

**Severity:** Critical (REQUIRED for Sentinel services)
**Requirement:** Services must emit heartbeat/timestamp metrics that external monitoring can use to detect silent failures.

**Applies to:** Sentinel (CRITICAL), Adapter (Yes), API (Optional)
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. Heartbeat or timestamp metric exists
2. Metric is updated on each successful operation cycle
3. Metric follows naming convention: `hyperfleet_*_last_success_timestamp` or `hyperfleet_*_heartbeat`

**Check commands:**
```bash
# Check for dead man's switch / heartbeat metrics
grep -r "last_success\|heartbeat\|last_run\|last_processed" --include="*.go" -l 2>/dev/null

# Check for timestamp metric patterns
grep -r "SetToCurrentTime\|prometheus.NewGauge.*timestamp\|prometheus.NewGauge.*heartbeat" --include="*.go" -l 2>/dev/null

# Look for reconciliation loop metrics
grep -r "reconcile.*success\|loop.*completed\|cycle.*finished" --include="*.go" -l 2>/dev/null
```

**Pass criteria:**
- Heartbeat or timestamp metric exists
- Metric is updated in main processing loop

**Fail indicators (CRITICAL for Sentinel):**
- No heartbeat/timestamp metrics found
- Metrics exist but not updated on success path
- Only error metrics without success indicators

---

### Check 3: Retry Logic with Exponential Backoff

**Severity:** Major
**Requirement:** All HTTP clients and message broker interactions must implement retry logic with exponential backoff to handle transient failures.

**Applies to:** API, Sentinel, Adapter
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. HTTP client retry configuration
2. Message broker client retry configuration
3. Exponential backoff implementation (not just fixed delays)

**Check commands:**
```bash
# Check for retry libraries or patterns
grep -r "retry\|backoff\|Retry\|Backoff" --include="*.go" -l 2>/dev/null

# Check for exponential backoff specifically
grep -r "exponential\|ExponentialBackoff\|backoff.Exponential" --include="*.go" -l 2>/dev/null

# Check for common retry libraries
grep -r "cenkalti/backoff\|avast/retry-go\|hashicorp/go-retryablehttp" --include="*.go" -l 2>/dev/null

# Check if raw http.Client is wrapped
grep -r "http.Client\|http.NewRequest" --include="*.go" -A 5 2>/dev/null | grep -i "retry"
```

**Pass criteria:**
- Retry library is imported/used
- HTTP clients wrapped with retry logic
- Exponential backoff configured (not fixed delays)

**Fail indicators:**
- Raw http.Client used without retry wrapper
- Fixed sleep delays instead of exponential backoff
- No retry logic on broker/external service calls

---

### Check 4: PodDisruptionBudget

**Severity:** Major
**Requirement:** Helm charts must include PodDisruptionBudget templates to ensure availability during node maintenance and cluster upgrades.

**Applies to:** API, Sentinel, Adapter, Infrastructure
**Does NOT apply to:** Tooling

**What to check:**

1. PDB template exists in Helm chart
2. PDB has sensible defaults (minAvailable or maxUnavailable)

**Check commands:**
```bash
# Check for PDB template
ls charts/*/templates/pdb.yaml 2>/dev/null || ls charts/*/templates/poddisruptionbudget.yaml 2>/dev/null

# Check values.yaml for PDB configuration
grep -r "podDisruptionBudget\|pdb:" charts/*/values.yaml 2>/dev/null

# Check for PDB in any template
grep -r "PodDisruptionBudget" charts/*/templates/*.yaml 2>/dev/null
```

**Pass criteria:**
- PDB template exists
- PDB values configurable in values.yaml

**Fail indicators:**
- No PDB template in Helm chart
- PDB exists but hardcoded (not configurable)
- No Helm chart exists (for services that should have one)

---

### Check 5: Resource Limits

**Severity:** Major
**Requirement:** Deployment must have CPU and memory requests AND limits defined to ensure proper scheduling and prevent resource exhaustion.

**Applies to:** API, Sentinel, Adapter, Infrastructure
**Does NOT apply to:** Tooling

**What to check:**

1. Resource requests defined (cpu, memory)
2. Resource limits defined (cpu, memory)
3. Values are configurable in values.yaml

**Check commands:**
```bash
# Check values.yaml for resource configuration
grep -A 10 "resources:" charts/*/values.yaml 2>/dev/null

# Check for both requests and limits
grep -A 20 "resources:" charts/*/values.yaml 2>/dev/null | grep -E "requests:|limits:|cpu:|memory:"

# Check deployment template uses resources
grep -r "\.Values.resources\|resources:" charts/*/templates/deployment.yaml 2>/dev/null
```

**Pass criteria:**
- `resources.requests.cpu` defined
- `resources.requests.memory` defined
- `resources.limits.cpu` defined
- `resources.limits.memory` defined
- Values are templates (not hardcoded)

**Fail indicators:**
- Missing requests or limits
- Only requests without limits (or vice versa)
- Hardcoded values instead of templated

---

### Check 6: Graceful Shutdown

**Severity:** Critical
**Requirement:** Services must handle SIGTERM/SIGINT signals, stop accepting new work, drain existing work, and exit cleanly within the termination grace period.

**Applies to:** API, Sentinel, Adapter
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. Signal handling for SIGTERM and SIGINT
2. Server/listener graceful shutdown
3. In-flight request completion
4. Connection draining

**Check commands:**
```bash
# Check for signal handling
grep -r "SIGTERM\|SIGINT\|signal.Notify\|os.Signal" --include="*.go" -l 2>/dev/null

# Check for graceful shutdown
grep -r "Shutdown\|GracefulStop\|graceful" --include="*.go" -l 2>/dev/null

# Check for context cancellation on shutdown
grep -r "context.WithCancel\|ctx.Done" --include="*.go" -A 5 2>/dev/null | grep -i "shutdown\|signal"
```

**Pass criteria:**
- Signal handlers registered for SIGTERM and SIGINT
- Server Shutdown() or GracefulStop() called
- Context cancellation propagated

**Fail indicators:**
- No signal handling
- Using os.Exit() directly without cleanup
- No graceful server shutdown

---

### Check 7: Reliability Documentation

**Severity:** Minor
**Requirement:** Services should have operational documentation including runbooks, metrics documentation, and operational guides.

**Applies to:** API, Sentinel, Adapter, Infrastructure (Partial)
**Does NOT apply to:** Tooling

**What to check:**

1. Runbook exists (docs/runbook.md or similar)
2. Metrics documented
3. Operational guide or README with ops section

**Check commands:**
```bash
# Check for runbook
ls docs/runbook.md 2>/dev/null || ls docs/runbooks/*.md 2>/dev/null || ls RUNBOOK.md 2>/dev/null

# Check for metrics documentation
ls docs/metrics.md 2>/dev/null || grep -l "## Metrics" docs/*.md 2>/dev/null || grep -l "## Metrics" README.md 2>/dev/null

# Check for operational documentation
ls docs/operations.md 2>/dev/null || grep -l "## Operations\|## Operational" docs/*.md 2>/dev/null
```

**Pass criteria:**
- At least one form of operational documentation exists
- Metrics are documented somewhere

**Fail indicators:**
- No runbook
- No metrics documentation
- No operational guidance

---

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
2. **Execute check commands** listed above
3. **Evaluate results** against pass/fail criteria
4. **Record status** as PASS, PARTIAL, or FAIL
5. **Document specific gaps** with file locations and remediation

## Output Format

### Audit Report Structure

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

## Example Audit Session

**User:** "check operational readiness"

**Skill Response:**

```markdown
# HyperFleet Operational Readiness Audit Report

**Repository:** hyperfleet-sentinel
**Path:** /home/croche/Projects/hyperfleet/hyperfleet-sentinel
**Repository Type:** Sentinel
**Audit Date:** 2026-01-29T14:30:00Z
**Requirements Source:** HYPERFLEET-539

---

## Summary

| Check | Status | Severity | Applicable |
|-------|--------|----------|------------|
| Functional Health Probes | PASS | Critical | Yes |
| Dead Man's Switch Metrics | FAIL | Critical | Yes (REQUIRED) |
| Retry Logic with Backoff | PARTIAL | Major | Yes |
| PodDisruptionBudget | PASS | Major | Yes |
| Resource Limits | PASS | Major | Yes |
| Graceful Shutdown | PASS | Critical | Yes |
| Reliability Documentation | FAIL | Minor | Yes |

**Overall Operational Readiness:** 4/7 checks passing (57%)

---

## Detailed Findings

### Functional Health Probes

**Status:** PASS
**Severity:** Critical
**Applicable:** Yes

#### Evidence Found
- cmd/server/health.go:23 - `/healthz` endpoint registered
- cmd/server/health.go:45 - `/readyz` endpoint registered
- cmd/server/health.go:52 - Database ping check in readiness handler

---

### Dead Man's Switch Metrics

**Status:** FAIL
**Severity:** Critical (REQUIRED for Sentinel)
**Applicable:** Yes - Sentinel services MUST have dead man's switch metrics

#### Evidence Found
- No heartbeat or timestamp metrics found

#### Gaps Found
- **Location:** N/A - not implemented
- **Expected:** Heartbeat or timestamp metric updated on each reconciliation cycle
- **Found:** No metrics that would alert on silent failures
- **Remediation:** Add `hyperfleet_sentinel_last_success_timestamp` gauge metric, call `SetToCurrentTime()` after each successful reconciliation cycle

---

### Retry Logic with Backoff

**Status:** PARTIAL
**Severity:** Major
**Applicable:** Yes

#### Evidence Found
- pkg/client/http.go:45 - Basic retry logic found
- No exponential backoff implementation

#### Gaps Found
- **Location:** pkg/client/http.go:45
- **Expected:** Exponential backoff with jitter
- **Found:** Fixed 1-second delay between retries
- **Remediation:** Replace fixed delays with exponential backoff using `cenkalti/backoff` or similar library

---

### PodDisruptionBudget

**Status:** PASS
**Severity:** Major
**Applicable:** Yes

#### Evidence Found
- charts/hyperfleet-sentinel/templates/pdb.yaml exists
- charts/hyperfleet-sentinel/values.yaml:78 - `podDisruptionBudget.minAvailable: 1`

---

### Resource Limits

**Status:** PASS
**Severity:** Major
**Applicable:** Yes

#### Evidence Found
- charts/hyperfleet-sentinel/values.yaml:45 - resources.requests.cpu: 100m
- charts/hyperfleet-sentinel/values.yaml:46 - resources.requests.memory: 128Mi
- charts/hyperfleet-sentinel/values.yaml:47 - resources.limits.cpu: 500m
- charts/hyperfleet-sentinel/values.yaml:48 - resources.limits.memory: 512Mi

---

### Graceful Shutdown

**Status:** PASS
**Severity:** Critical
**Applicable:** Yes

#### Evidence Found
- cmd/main.go:67 - `signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT)`
- cmd/main.go:89 - `server.Shutdown(ctx)` called on signal

---

### Reliability Documentation

**Status:** FAIL
**Severity:** Minor
**Applicable:** Yes

#### Evidence Found
- No runbook found
- No metrics documentation found

#### Gaps Found
- **Location:** docs/ directory
- **Expected:** Runbook and metrics documentation
- **Found:** Only README.md with installation instructions
- **Remediation:** Create docs/runbook.md with operational procedures and docs/metrics.md documenting exposed metrics

---

## Recommendations

**Critical Issues (address before production):**
1. **Dead Man's Switch Metrics** - Add heartbeat metric to detect silent failures. This is REQUIRED for Sentinel services.

**Major Issues (address soon):**
1. **Retry Logic** - Replace fixed delays with exponential backoff to prevent thundering herd during outages.

**Minor Issues (address when convenient):**
1. **Reliability Documentation** - Add runbook and metrics documentation for on-call support.
```

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
