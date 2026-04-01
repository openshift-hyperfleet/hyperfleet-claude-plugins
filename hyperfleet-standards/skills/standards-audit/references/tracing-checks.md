# Tracing Checks

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

### Step 3: Find Tracing Code

Search for files related to tracing and OpenTelemetry:

```bash
# OpenTelemetry imports
grep -rl "go.opentelemetry.io/otel" --include="*.go" 2>/dev/null

# Span creation
grep -rn "tracer.Start\|otel.Tracer\|span.End\|span.SetAttributes" --include="*.go" 2>/dev/null | head -30

# Tracing configuration
grep -rn "OTEL_SERVICE_NAME\|OTEL_EXPORTER_OTLP_ENDPOINT\|OTEL_TRACES_SAMPLER\|HYPERFLEET_TRACING_ENABLED" --include="*.go" 2>/dev/null

# Context propagation
grep -rn "propagation\|traceparent\|tracecontext\|W3C" --include="*.go" 2>/dev/null | head -20

# Trace ID in logs
grep -rn "trace_id\|span_id\|TraceID\|SpanID" --include="*.go" 2>/dev/null | head -20
```

### Step 4: Checks

For each check, verify against the requirements defined in the standard document fetched in Step 1.

#### Check 1: OpenTelemetry SDK Usage

**What to verify:** The service uses the correct OTel packages, initializes the SDK properly, handles shutdown, and avoids vendor-specific SDKs, as defined in the standard.
**How to find:** Inspect OTel imports and SDK initialization code found in Step 3.

#### Check 2: Configuration via Environment Variables

**What to verify:** Tracing is configured through the environment variables specified in the standard, with correct defaults and naming conventions.
**How to find:** Review environment variable references found in Step 3.

#### Check 3: Service Name and Resource Attributes

**What to verify:** Resource attributes are set according to the standard's requirements for service identification.
**How to find:** `grep -rn "resource.New\|semconv\|service.name\|service.version" --include="*.go" 2>/dev/null`

#### Check 4: W3C Trace Context Propagation

**What to verify:** The service implements trace context propagation (HTTP headers, CloudEvents) as required by the standard.
**How to find:** Review propagation-related code found in Step 3.

#### Check 5: Required Spans by Component Type

**What to verify:** The service creates spans for all operations required by the standard for its component type (API, Sentinel, or Adapter).
**How to find:** Review span creation patterns found in Step 3.

#### Check 6: Span Naming Conventions

**What to verify:** Span names follow the naming patterns defined in the standard and avoid anti-patterns listed there.
**How to find:** Inspect span name strings in `tracer.Start` calls found in Step 3.

#### Check 7: Standard Span Attributes

**What to verify:** Spans include the required and recommended attributes for their category (HTTP, database, messaging) as listed in the standard.
**How to find:** `grep -rn "SetAttributes\|attribute\." --include="*.go" 2>/dev/null | head -30`

#### Check 8: HyperFleet-Specific Attributes

**What to verify:** HyperFleet-specific span attributes are set on relevant operations as defined in the standard.
**How to find:** `grep -rn "hyperfleet\." --include="*.go" 2>/dev/null`

#### Check 9: Sampling and OTLP Configuration

**What to verify:** Sampling strategy and OTLP exporter are configured according to the standard's requirements.
**How to find:** `grep -rn "Sampler\|sampler\|BatchSpan\|SimpleSpan\|otlp" --include="*.go" 2>/dev/null`

#### Check 10: Logging Integration and Error Handling

**What to verify:** Trace/span IDs are included in structured logs and errors are properly recorded on spans, as required by the standard.
**How to find:** Review logging and error handling code found in Step 3.

## Output Format

```markdown
# Tracing Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| OpenTelemetry SDK Usage | PASS/PARTIAL/FAIL/N/A | 0/N |
| Environment Configuration | PASS/PARTIAL/FAIL | 0/N |
| Service Name & Resources | PASS/PARTIAL/FAIL | 0/N |
| W3C Trace Context | PASS/PARTIAL/FAIL | 0/N |
| Required Spans | PASS/PARTIAL/FAIL | 0/N |
| Span Naming | PASS/PARTIAL/FAIL | 0/N |
| Span Attributes | PASS/PARTIAL/FAIL | 0/N |
| HyperFleet Attributes | PASS/PARTIAL/FAIL | 0/N |
| Sampling & OTLP Config | PASS/PARTIAL/FAIL | 0/N |
| Logging & Error Handling | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-TRC-001: [Brief description]
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

- If the repo has no Go code: report "No Go code found -- tracing review not applicable"
- If no tracing code is found: report "No OpenTelemetry instrumentation found in this repository"
- If the orchestrator did not supply the tracing standard content: report that the standard content is missing and skip the tracing audit
- If the repository type is Infrastructure or Tooling: report "Tracing review does not apply to this repository type"
