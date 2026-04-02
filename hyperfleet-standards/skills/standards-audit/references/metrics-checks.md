# Metrics Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched from the architecture repo). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

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

### Step 3: Find Metrics Code

Search for files that define or expose metrics:

```bash
# Prometheus client usage
grep -rl "prometheus\.\|promauto\.\|promhttp\." --include="*.go" 2>/dev/null

# Metric definitions
grep -rn "NewCounter\|NewGauge\|NewHistogram\|NewSummary\|NewCounterVec\|NewGaugeVec\|NewHistogramVec" --include="*.go" 2>/dev/null

# Metric names
grep -rn "hyperfleet_\|Name:\s*\"" --include="*.go" 2>/dev/null | head -30

# Metrics endpoint
grep -rn "9090\|/metrics\|promhttp.Handler\|metricsPort" --include="*.go" 2>/dev/null

# ServiceMonitor/PodMonitor
grep -rl "ServiceMonitor\|PodMonitor" --include="*.yaml" --include="*.yml" 2>/dev/null
```

### Step 4: Checks

For each check, verify against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Naming Convention

**What to verify:** Metric names follow the prefix format, component naming, and casing rules defined in the standard.
**How to find:** Inspect all metric name strings found in Step 3.

#### Check 2: Required Suffixes

**What to verify:** Metrics use the correct type-based suffixes as specified in the standard (e.g., counters, durations, sizes, info gauges).
**How to find:** Cross-reference metric types with their names from Step 3 results.

#### Check 3: Required Labels

**What to verify:** All metrics include the required labels defined in the standard.
**How to find:** Inspect label definitions in metric constructors found in Step 3.

#### Check 4: Label Best Practices

**What to verify:** Labels follow the cardinality, sensitivity, and sanitization rules from the standard.
**How to find:** Inspect label values and patterns in metric registration and usage code.

#### Check 5: Standard Metrics

**What to verify:** The service exposes all mandatory standard metrics listed in the standard.
**How to find:** Search for the standard metric names defined in the standard document.

#### Check 6: Metric Types

**What to verify:** Correct Prometheus metric types are used for each use case, following the guidance in the standard.
**How to find:** Review metric type constructors found in Step 3.

#### Check 7: Histogram Buckets

**What to verify:** Histogram buckets are configured appropriately for the workload, following the recommendations in the standard.
**How to find:** `grep -rn "Buckets\|DefBuckets" --include="*.go" 2>/dev/null`

#### Check 8: Metrics Endpoint

**What to verify:** Metrics are served on the correct port, path, and handler as specified in the standard.
**How to find:** Review endpoint configuration found in Step 3.

#### Check 9: ServiceMonitor/PodMonitor

**What to verify:** Helm charts include monitoring manifests with correct port, path, interval, and labels as defined in the standard.
**How to find:** Review monitoring manifests found in Step 3.

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Non-Goals | N/A (informational) |
| Metric Naming Convention | Naming Convention |
| Format | Naming Convention |
| Naming Rules | Naming Convention |
| Required Labels | Required Labels |
| Label Best Practices | Label Best Practices |
| Standard Metrics | Standard Metrics |
| Process Metrics | Standard Metrics |
| Build Info | Standard Metrics |
| Health Status | Standard Metrics |
| Metric Types and Usage | Metric Types |
| Counter | Metric Types |
| Gauge | Metric Types |
| Histogram | Metric Types |
| Summary | Metric Types |
| Histogram Bucket Recommendations | Histogram Buckets |
| API Request Duration | Histogram Buckets |
| Event Processing Duration | Histogram Buckets |
| Database Query Duration | Histogram Buckets |
| General Guidelines | Histogram Buckets |
| Metrics Exposition | Metrics Endpoint |
| Port and Path | Metrics Endpoint |
| OpenMetrics Compatibility | Metrics Endpoint |
| Component-Specific Metrics | Standard Metrics |

## Output Format

```markdown
# Metrics Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Naming Convention | PASS/PARTIAL/FAIL | 0/N |
| Required Suffixes | PASS/PARTIAL/FAIL | 0/N |
| Required Labels | PASS/PARTIAL/FAIL | 0/N |
| Label Best Practices | PASS/PARTIAL/FAIL | 0/N |
| Standard Metrics | PASS/PARTIAL/FAIL | 0/N |
| Metric Types | PASS/PARTIAL/FAIL | 0/N |
| Histogram Buckets | PASS/PARTIAL/FAIL/N/A | 0/N |
| Metrics Endpoint | PASS/PARTIAL/FAIL | 0/N |
| ServiceMonitor/PodMonitor | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-MET-001: [Brief description]
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

- If the repo has no Go code: report "No Go code found -- metrics review not applicable"
- If no metrics code is found: report "No Prometheus metrics found in this repository"
- If the orchestrator did not supply the metrics standard content: report that the standard content is missing and skip the metrics audit
