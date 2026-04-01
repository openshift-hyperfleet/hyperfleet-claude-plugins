# Operational Readiness Checks

## Check 1: Functional Health Probes

**Severity:** Critical
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the health-endpoints standard. The standard defines what liveness and readiness endpoints must verify.

**Applies to:** API, Sentinel, Adapter
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. Liveness endpoint exists (`/healthz` or `/health` or `/live`)
2. Readiness endpoint exists (`/readyz` or `/ready`)
3. Liveness checks verify only process health (not external dependencies)
4. Readiness checks verify actual dependencies:
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
- Both liveness and readiness endpoints exist
- Liveness checks only process health (no external dependency calls)
- Readiness checks contain actual dependency checks (not just `return 200`)

**Fail indicators:**
- No health endpoints found
- Liveness probe checks external dependencies (risk of restart storms)
- Readiness handlers only return static OK without checking dependencies
- Missing readiness probe separate from liveness

---

## Check 2: Dead Man's Switch Metrics

**Severity:** Critical (REQUIRED for Sentinel services)
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the metrics standard. The standard defines what heartbeat/timestamp metrics services must emit.

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

## Check 3: Retry Logic with Exponential Backoff

**Severity:** Major
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the operational readiness requirements. The requirements define retry logic, backoff, and idempotency expectations.

**Applies to:** API, Sentinel, Adapter
**Does NOT apply to:** Infrastructure, Tooling

**What to check:**

1. HTTP client retry configuration with bounded counts and exponential backoff with jitter
2. Message broker client retry configuration
3. Non-idempotent operations are either made idempotent or excluded from automatic retry

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
- Exponential backoff with jitter configured (not fixed delays)
- Bounded retry count or duration
- Non-idempotent operations handled safely (idempotency keys, at-most-once, or no auto-retry)

**Fail indicators:**
- Raw http.Client used without retry wrapper
- Fixed sleep delays instead of exponential backoff
- No jitter in backoff strategy
- Unbounded retries (no max count or duration)
- Side-effectful operations retried without idempotency guarantees
- No retry logic on broker/external service calls

---

## Check 4: PodDisruptionBudget

**Severity:** Major
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the operational readiness requirements. The requirements define PodDisruptionBudget expectations for Helm charts.

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

## Check 5: Resource Limits

**Severity:** Major
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the operational readiness requirements. The requirements define resource requests and limits expectations.

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

## Check 6: Graceful Shutdown

**Severity:** Critical
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the graceful-shutdown standard. The standard defines signal handling and shutdown behavior expectations.

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

## Check 7: Reliability Documentation

**Severity:** Minor
**Requirement:** The orchestrator (via the `hyperfleet-architecture` skill) provides the operational readiness requirements. The requirements define what operational documentation services should have.

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
