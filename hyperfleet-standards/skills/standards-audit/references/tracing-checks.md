# Tracing Checks

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

**What to verify:** Resource attributes are set according to the standard's requirements for service identification. The `service.name` MUST match the component mapping defined in the standard (e.g., API → `hyperfleet-api`, Sentinel → `hyperfleet-sentinel`, Adapter → `adapter-<provider>`). Verify the exact name string matches what the standard specifies for the detected component type.
**How to find:**

```bash
# Check service name value
grep -rn "resource.New\|semconv\|service.name\|service.version\|ServiceName" --include="*.go" 2>/dev/null

# Verify the actual service name string
grep -rn "hyperfleet-api\|hyperfleet-sentinel\|adapter-" --include="*.go" 2>/dev/null | grep -i "service"
```

#### Check 4: W3C Trace Context Propagation

**What to verify:** The service implements trace context propagation (HTTP headers, CloudEvents) as required by the standard. For CloudEvents specifically, verify that `traceparent` and `tracestate` extension attributes are propagated on all emitted events.
**How to find:**

```bash
# HTTP propagation
grep -rn "propagation\|tracecontext\|W3C\|Inject\|Extract" --include="*.go" 2>/dev/null | head -20

# CloudEvents trace context extensions
grep -rn "traceparent\|tracestate\|SetExtension.*trace" --include="*.go" 2>/dev/null
```

#### Check 5: Required Spans by Component Type

**What to verify:** The service creates spans for all operations required by the standard for its component type (API, Sentinel, or Adapter). Component-specific spans MUST exist for all required operations listed in the standard per component type. Cross-reference the standard's required-spans list against the actual `tracer.Start` calls in the codebase.
**How to find:**

```bash
# All span creation points
grep -rn "tracer.Start\|StartSpan" --include="*.go" 2>/dev/null

# Cross-reference with component-specific operations
grep -rn "reconcile\|poll\|sync\|watch\|handler\|endpoint" --include="*.go" 2>/dev/null | grep -i "span\|trace" | head -20
```

#### Check 6: Span Naming Conventions

**What to verify:** Span names follow the naming patterns defined in the standard and avoid anti-patterns listed there.
**How to find:** Inspect span name strings in `tracer.Start` calls found in Step 3.

#### Check 7: Standard Span Attributes

**What to verify:** Spans MUST follow OTel Semantic Conventions for attributes. Verify that attribute names and values conform to the OpenTelemetry semantic convention keys for their category (HTTP, database, messaging) as required by the standard. Flag any custom attribute names that duplicate or contradict semantic convention equivalents.
**How to find:**

```bash
# Check for semantic convention usage
grep -rn "semconv\.\|SetAttributes\|attribute\." --include="*.go" 2>/dev/null | head -30

# Check for custom attributes that should use semconv
grep -rn "http.method\|http.status_code\|db.system\|messaging.system" --include="*.go" 2>/dev/null | head -10
```

#### Check 8: HyperFleet-Specific Attributes

**What to verify:** HyperFleet-specific span attributes are set on relevant operations as defined in the standard.
**How to find:** `grep -rn "hyperfleet\." --include="*.go" 2>/dev/null`

#### Check 9: Sampling and OTLP Configuration

**What to verify:** Sampling strategy and OTLP exporter are configured according to the standard's requirements. MUST support OTLP as the primary export format. Verify that the OTLP exporter is configured (not Jaeger, Zipkin, or other vendor-specific exporters) and that sampling defaults match the standard.
**How to find:**

```bash
# Check exporter type
grep -rn "otlp\|jaeger\|zipkin\|Exporter" --include="*.go" 2>/dev/null | head -15

# Check sampler configuration
grep -rn "Sampler\|sampler\|BatchSpan\|SimpleSpan" --include="*.go" 2>/dev/null
```

#### Check 10: Logging Integration and Error Handling

**What to verify:** Trace/span IDs are included in structured logs and errors are properly recorded on spans, as required by the standard. Log correlation MUST use specific `trace_id` and `span_id` fields (not alternative names like `traceID` or `spanID`). Verify the exact field names match the standard's specification.
**How to find:**

```bash
# Check trace/span ID field names in logs
grep -rn "trace_id\|span_id\|traceID\|spanID\|TraceID\|SpanID" --include="*.go" 2>/dev/null | head -20

# Check error recording on spans
grep -rn "RecordError\|SetStatus\|codes.Error" --include="*.go" 2>/dev/null | head -10
```

#### Check 11: Context Propagation Through Call Chain

**What to verify:** Context MUST be propagated through the entire call chain. After tracing is initialized, functions MUST NOT use `context.Background()` or `context.TODO()` — they must pass the trace-carrying context received from their caller. Flag any `context.Background()` usage outside of initialization/startup code.
**How to find:**

```bash
# Find context.Background() usage outside of main/init/bootstrap files
grep -rn "context.Background()\|context.TODO()" --include="*.go" 2>/dev/null | grep -v "_test.go" | grep -v "main.go" | grep -v "init.go" | grep -v "init_" | grep -v "bootstrap" | grep -v "wire.go" | head -20

# Verify functions accept and pass context
grep -rn "func.*ctx context.Context" --include="*.go" 2>/dev/null | head -20
```

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Non-Goals | N/A (informational) |
| OpenTelemetry Adoption | OpenTelemetry SDK Usage |
| Why OpenTelemetry | N/A (informational) |
| SDK Requirements | OpenTelemetry SDK Usage |
| Configuration | Configuration via Environment Variables |
| Service Names | Service Name and Resource Attributes |
| Resource Attributes | Service Name and Resource Attributes |
| Setting service.version from Build | Service Name and Resource Attributes |
| Example Configuration | N/A (informational) |
| Trace Context Propagation | W3C Trace Context Propagation |
| HTTP Requests | W3C Trace Context Propagation |
| CloudEvents (Pub/Sub) | W3C Trace Context Propagation |
| Propagation Flow | W3C Trace Context Propagation |
| Required Spans | Required Spans by Component Type |
| Span Naming Convention | Span Naming Conventions |
| All Components | Required Spans by Component Type |
| API | Required Spans by Component Type |
| Sentinel | Required Spans by Component Type |
| Adapters | Required Spans by Component Type |
| Standard Span Attributes | Standard Span Attributes |
| Semantic Conventions | Standard Span Attributes |
| HTTP Spans | Standard Span Attributes |
| Database Spans | Standard Span Attributes |
| Messaging Spans (Pub/Sub) | Standard Span Attributes |
| Cloud Provider Spans | Standard Span Attributes |
| HyperFleet-Specific Attributes | HyperFleet-Specific Attributes |
| Attribute Best Practices | Standard Span Attributes |
| Sampling Strategy | Sampling and OTLP Configuration |
| Head-Based vs Tail-Based Sampling | Sampling and OTLP Configuration |
| Default: Parent-Based Trace ID Ratio | Sampling and OTLP Configuration |
| Environment-Specific Sampling Rates | Sampling and OTLP Configuration |
| Configuration Example | N/A (informational) |
| Always Sample Specific Operations | Sampling and OTLP Configuration |
| Exporter Configuration | Sampling and OTLP Configuration |
| OTLP Exporter (Default) | Sampling and OTLP Configuration |
| Kubernetes Deployment | N/A (informational) |
| Local Development | N/A (informational) |
| Integration with Logging | Logging Integration and Error Handling |
| Adding Trace Context to Logs | Logging Integration and Error Handling |
| Log Output Example | N/A (informational) |
| Error Handling in Spans | Logging Integration and Error Handling |
| Recording Errors | Logging Integration and Error Handling |
| Error Attributes | Logging Integration and Error Handling |
| Span Lifecycle Best Practices | Context Propagation Through Call Chain |
| Starting and Ending Spans | Context Propagation Through Call Chain |
| Context Propagation | Context Propagation Through Call Chain |

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
| Context Propagation | PASS/PARTIAL/FAIL | 0/N |

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
