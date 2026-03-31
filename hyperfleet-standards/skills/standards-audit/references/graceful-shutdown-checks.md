# Graceful Shutdown Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via the `hyperfleet-architecture` skill). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"
ls openapi.yaml 2>/dev/null || ls openapi/openapi.yaml 2>/dev/null && echo "HAS_OPENAPI"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"
```

### Step 3: Find Relevant Code

Search for files that handle shutdown, signals, or graceful termination:

```bash
# Signal handling
grep -rl "signal.NotifyContext\|signal.Notify\|os.Signal\|syscall.SIGTERM\|syscall.SIGINT" --include="*.go" 2>/dev/null

# Shutdown methods
grep -rl "Shutdown\|GracefulStop\|Close\|server.Close\|server.Shutdown" --include="*.go" 2>/dev/null

# Context cancellation for shutdown
grep -rn "context.WithTimeout\|context.WithCancel\|ctx.Done()\|<-ctx.Done()" --include="*.go" 2>/dev/null | head -30

# Timeout configuration
grep -rn "SHUTDOWN_TIMEOUT\|shutdownTimeout\|gracePeriod\|terminationGrace" --include="*.go" 2>/dev/null

# Kubernetes readiness
grep -rn "terminationGracePeriodSeconds\|readinessProbe\|livenessProbe" --include="*.yaml" --include="*.yml" 2>/dev/null
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Signal Handling

**What to verify:** Verify that signal handling uses the approach specified in the standard (e.g., signal registration method, which signals are handled, where setup occurs, and whether `os.Exit` is called directly). Refer to the standard for the required pattern.
**How to find:** `grep -rn "signal.NotifyContext\|signal.Notify\|syscall.SIGTERM\|os.Exit" --include="*.go" 2>/dev/null`

#### Check 2: Shutdown Sequence

**What to verify:** Verify that the shutdown follows the phased sequence defined in the standard (marking not ready, stopping acceptance, draining, cleanup, exit). Flag missing phases, incorrect ordering, or phases combined incorrectly.
**How to find:** Read the shutdown handler code found in Step 3 and trace the execution order.

#### Check 3: Timeout Configuration

**What to verify:** Verify that the shutdown timeout is read from the environment variable and uses the default value specified in the standard. Check that the timeout is applied via context and is less than the Kubernetes termination grace period.
**How to find:** `grep -rn "SHUTDOWN_TIMEOUT\|shutdownTimeout\|WithTimeout" --include="*.go" 2>/dev/null`

#### Check 4: HTTP Server Drain (API)

**What to verify:** Verify that HTTP server shutdown uses the method and patterns defined in the standard (graceful shutdown vs hard close, context timeout, readiness endpoint behavior during shutdown).
**How to find:** `grep -rn "server.Shutdown\|server.Close\|http.Server" --include="*.go" 2>/dev/null`

#### Check 5: Broker Consumer Drain (Sentinel/Adapter)

**What to verify:** Verify that broker consumers follow the drain sequence defined in the standard (stop receiving, complete in-flight, acknowledge pending, close consumer).
**How to find:** `grep -rn "consumer\|Subscribe\|Unsubscribe\|Ack\|Nack\|Close" --include="*.go" 2>/dev/null`

#### Check 6: Background Worker Shutdown

**What to verify:** Verify that background goroutines respect context cancellation and use the synchronization mechanisms defined in the standard. Check that all spawned goroutines have a shutdown path and tickers/timers are cleaned up.
**How to find:** `grep -rn "go func\|WaitGroup\|errgroup\|ctx.Done\|Ticker\|Timer" --include="*.go" 2>/dev/null`

#### Check 7: Kubernetes Integration

**What to verify:** Verify that Kubernetes pod spec settings (termination grace period, probes, preStop hook) match the values and configuration defined in the standard.
**How to find:** `grep -rn "terminationGracePeriodSeconds\|preStop\|readinessProbe" --include="*.yaml" --include="*.yml" 2>/dev/null`

#### Check 8: Component-Specific Guidelines

**What to verify:** Verify the code follows the component-specific shutdown guidelines defined in the standard for the detected repository type (API, Sentinel, or Adapter).
**How to find:** Read shutdown/cleanup code in the component's main packages and compare against the standard's requirements for this component type.

## Output Format

```markdown
# Graceful Shutdown Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Signal Handling | PASS/PARTIAL/FAIL | 0/N |
| Shutdown Sequence | PASS/PARTIAL/FAIL | 0/N |
| Timeout Configuration | PASS/PARTIAL/FAIL | 0/N |
| HTTP Server Drain | PASS/PARTIAL/FAIL/N/A | 0/N |
| Broker Consumer Drain | PASS/PARTIAL/FAIL/N/A | 0/N |
| Background Worker Shutdown | PASS/PARTIAL/FAIL | 0/N |
| Kubernetes Integration | PASS/PARTIAL/FAIL | 0/N |
| Component Guidelines | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-GSD-001: [Brief description]
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

- If the repo has no Go code: report "No Go code found -- graceful shutdown review not applicable"
- If no shutdown-related code is found: report "No shutdown handling patterns found in this repository"
- If the orchestrator did not supply the graceful-shutdown standard content: report that the standard content is missing and skip the graceful shutdown audit
