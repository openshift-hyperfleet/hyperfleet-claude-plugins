# Health Endpoints Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched from the architecture repo). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

```bash
ls pkg/api/ 2>/dev/null && echo "IS_API"
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"
ls charts/ 2>/dev/null && echo "HAS_HELM"
```

### Step 3: Find Relevant Code

```bash
# Health/readiness handlers
grep -rn "healthz\|readyz\|/health\|/ready\|livenessProbe\|readinessProbe" --include="*.go" 2>/dev/null

# Metrics endpoint
grep -rn "/metrics\|promhttp\|prometheus.*Handler" --include="*.go" 2>/dev/null

# Port configurations
grep -rn "8080\|9090" --include="*.go" 2>/dev/null | grep -i "port\|listen\|addr"

# Helm probe configs
grep -rn "livenessProbe\|readinessProbe\|healthz\|readyz" --include="*.yaml" --include="*.tpl" 2>/dev/null
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Endpoint Paths

**What to verify:** Verify that health, readiness, and metrics endpoints use the paths and ports defined in the standard. Flag non-standard paths or incorrect port assignments.
**How to find:** Look for route registration and listener setup in the files identified in Step 3.

#### Check 2: Response Format

**What to verify:** Verify that liveness and readiness endpoint responses match the JSON structure and status codes defined in the standard (including the checks map for readiness).
**How to find:** Read the handler implementations found in Step 3.

#### Check 3: Liveness vs Readiness Separation

**What to verify:** Verify that liveness probes only check process health and do not check external dependencies. The standard defines what belongs in each probe type. Flag liveness probes that check external dependencies, as this causes cascading restarts.
**How to find:** Read liveness handler code and check for any external calls (database, broker, API).

#### Check 4: Component-Specific Readiness Checks

**What to verify:** Verify that readiness checks include all required dependency checks for the detected component type, as defined in the standard.
**How to find:** Read readiness handler code and compare checks against the standard's requirements for this component type.

#### Check 5: Helm Chart Probe Configuration

**What to verify:** If the repo has Helm charts, verify probe paths, ports, and timing values match the standard's specification. Check that values are configurable via values.yaml where the standard requires it.
**How to find:** `grep -rn "livenessProbe\|readinessProbe" --include="*.yaml" --include="*.tpl" charts/ 2>/dev/null`

#### Check 6: Startup and Shutdown Behavior

**What to verify:** Verify that the implementation follows the startup/shutdown contract defined in the standard. Specifically:
- `/healthz` MUST return 200 OK immediately when the process starts (before full initialization completes)
- `/readyz` MUST return 503 Service Unavailable until all initialization completes, then switch to 200
- On SIGTERM, the handler MUST change `/readyz` to return 503 before beginning the shutdown sequence
**How to find:**

```bash
# Check health server startup ordering (should start before main initialization)
grep -rn "ListenAndServe\|http.Server" --include="*.go" 2>/dev/null | head -10

# Check readiness state management (flag/atomic that transitions from not-ready to ready)
grep -rn "ready\|isReady\|readyFlag\|SetReady\|atomic.*ready" --include="*.go" 2>/dev/null | head -10

# Check SIGTERM handler changes readiness state (preserve file:line context)
grep -rn "SIGTERM\|signal.Notify" --include="*.go" 2>/dev/null | head -10
grep -rn -A10 "signal.Notify" --include="*.go" 2>/dev/null | grep -i "ready\|readyz" | head -5
```

#### Check 7: Metrics Endpoint

**What to verify:** Verify that metrics are served on the correct port (separate from probes) using the handler type specified in the standard. Check for ServiceMonitor/PodMonitor in Helm charts if present.
**How to find:** `grep -rn "metrics\|promhttp\|9090" --include="*.go" --include="*.yaml" 2>/dev/null`

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Port and Endpoint Configuration | Endpoint Paths |
| Endpoint Specification | Endpoint Paths, Response Format |
| `/healthz` - Liveness Probe | Response Format, Liveness vs Readiness Separation |
| `/readyz` - Readiness Probe | Response Format, Component-Specific Readiness Checks |
| `/metrics` - Prometheus Metrics | Metrics Endpoint |
| Kubernetes Probe Configuration | Helm Chart Probe Configuration |
| Probe Timing | Helm Chart Probe Configuration |
| Helm Values Template | Helm Chart Probe Configuration |
| Deployment Probe Template | Helm Chart Probe Configuration |
| Graceful Degradation | Startup and Shutdown Behavior |
| Startup Behavior | Startup and Shutdown Behavior |
| Shutdown Behavior | Startup and Shutdown Behavior |

## Output Format

```markdown
# Health Endpoints Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Endpoint Paths | PASS/PARTIAL/FAIL | 0/N |
| Response Format | PASS/PARTIAL/FAIL | 0/N |
| Liveness vs Readiness | PASS/PARTIAL/FAIL | 0/N |
| Component Readiness | PASS/PARTIAL/FAIL | 0/N |
| Helm Probes | PASS/PARTIAL/FAIL/N/A | 0/N |
| Startup/Shutdown | PASS/PARTIAL/FAIL | 0/N |
| Metrics Endpoint | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-HLT-001: [Brief description]
- **File:** `path/to/file.go:42`
- **Found:** [what exists in the code]
- **Expected:** [what the standard requires]
- **Severity:** Critical/Major/Minor
- **Suggestion:** [specific remediation]

---

## Recommendations

**Critical (fix before merge):**
1. [Issue with file reference]

**Major (should fix soon):**
1. [Issue with file reference]

**Minor (nice to have):**
1. [Issue with file reference]
```

## Error Handling

- If the repo has no Go code and no Helm charts: report "No service code or Helm charts found -- health endpoints review not applicable"
- If no health endpoint code is found: report "No health endpoint implementations found"
- If the orchestrator did not supply the health-endpoints standard content: report that the standard content is missing and skip the health endpoints audit
