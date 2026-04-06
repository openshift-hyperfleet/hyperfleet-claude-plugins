# Health Endpoints Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

```bash
ls pkg/api/ 2>/dev/null && echo "IS_API"
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"
ls charts/ 2>/dev/null && echo "HAS_HELM"
```

### Step 3: Find Relevant Code

```bash
# Health/readiness handlers — search for endpoint path patterns; exact paths are defined in the standard
grep -rn "health\|ready\|alive\|liveness\|readiness" --include="*.go" . 2>/dev/null | grep -i "handler\|route\|mux\|endpoint\|path" | head -20

# Metrics endpoint
grep -rn "metrics\|promhttp\|prometheus.*Handler" --include="*.go" . 2>/dev/null

# Port configurations — search for port/listen patterns; exact port numbers are defined in the standard
grep -rn "port\|listen\|addr\|Addr" --include="*.go" . 2>/dev/null | grep -i "server\|http\|metrics" | head -20

# Helm probe configs
grep -rn "livenessProbe\|readinessProbe\|startupProbe" --include="*.yaml" --include="*.tpl" . 2>/dev/null
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Endpoint Paths

**What to verify:** Verify that health, readiness, and metrics endpoints use the paths and ports defined in the standard. Flag non-standard paths or incorrect port assignments.
**How to find:** Look for route registration and listener setup in the files identified in Step 3.

#### Check 2: Response Format

**What to verify:** Verify that liveness and readiness endpoint responses match the JSON structure and status codes defined in the standard.
**How to find:** Read the handler implementations found in Step 3.

#### Check 3: Liveness vs Readiness Separation

**What to verify:** Verify that liveness and readiness probes check the correct dependencies as defined in the standard. The standard defines what belongs in each probe type and the rationale for the separation.
**How to find:** Read liveness handler code and check for any external calls (database, broker, API).

#### Check 4: Component-Specific Readiness Checks

**What to verify:** Verify that readiness checks include all required dependency checks for the detected component type, as defined in the standard.
**How to find:** Read readiness handler code and compare checks against the standard's requirements for this component type.

#### Check 5: Helm Chart Probe Configuration

**What to verify:** If the repo has Helm charts, verify probe paths, ports, and timing values match the standard's specification. Check that values are configurable via values.yaml where the standard requires it.
**How to find:** `grep -rn "livenessProbe\|readinessProbe" --include="*.yaml" --include="*.tpl" charts/ 2>/dev/null`

#### Check 6: Startup and Shutdown Behavior

**What to verify:** Verify that the implementation follows the startup/shutdown contract defined in the standard (health server start order, readiness state transitions, SIGTERM handling of readiness).
**How to find:** Read the main entrypoint and signal handling code for server startup ordering and shutdown hooks.

#### Check 7: Metrics Endpoint

**What to verify:** Verify that metrics are served on the port defined in the standard (separate from probes) using the handler type specified in the standard. Check for ServiceMonitor/PodMonitor in Helm charts if present.
**How to find:** `grep -rn "metrics\|promhttp\|prometheus" --include="*.go" --include="*.yaml" . 2>/dev/null`

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
