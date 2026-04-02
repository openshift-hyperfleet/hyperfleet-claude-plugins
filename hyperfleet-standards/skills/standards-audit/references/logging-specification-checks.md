# Logging Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched from the architecture repo). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"

# Tooling indicators
basename $(pwd) | grep -qiE "(^|[-_])(tool|cli|util)([-_]|$)" && echo "IS_TOOLING"
```

### Step 3: Find Logging Code

Search for logging-related files and patterns:

```bash
# Logging library usage
grep -rl "slog\.\|zap\.\|logr\.\|zerolog\.\|logrus\." --include="*.go" 2>/dev/null

# Log level configuration
grep -rn "log.level\|LOG_LEVEL\|HYPERFLEET_LOG_LEVEL\|log-level\|logLevel" --include="*.go" 2>/dev/null | head -10

# Log format configuration
grep -rn "log.format\|LOG_FORMAT\|HYPERFLEET_LOG_FORMAT\|log-format\|logFormat" --include="*.go" 2>/dev/null | head -10

# Log output configuration
grep -rn "log.output\|LOG_OUTPUT\|HYPERFLEET_LOG_OUTPUT\|log-output\|logOutput" --include="*.go" 2>/dev/null | head -10

# Structured logging fields
grep -rn "\.With(\|\.WithField\|\.WithValues\|slog\.String\|slog\.Int\|slog\.Any" --include="*.go" 2>/dev/null | head -20

# Required fields (component, version, hostname)
grep -rn "component\|version\|hostname" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10

# Trace correlation
grep -rn "trace_id\|span_id\|request_id\|event_id" --include="*.go" 2>/dev/null | head -10

# Sensitive data handling
grep -rn "redact\|REDACTED\|mask\|sanitize" --include="*.go" 2>/dev/null | head -10

# Component-specific fields
grep -rn "method\|path\|status_code\|duration_ms\|adapter\|job_result\|decision_reason" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Configuration Support

**What to verify:** The application supports `--log-level` / `HYPERFLEET_LOG_LEVEL`, `--log-format` / `HYPERFLEET_LOG_FORMAT`, and `--log-output` / `HYPERFLEET_LOG_OUTPUT` with the defaults defined in the standard.
**How to find:** Review log configuration code from Step 3.

#### Check 2: Log Levels

**What to verify:** The application supports all log levels defined in the standard (`debug`, `info`, `warn`, `error`) and uses them for the appropriate scenarios.
**How to find:** `grep -rn "Debug\|Info\|Warn\|Error" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -20`

#### Check 3: Required Fields

**What to verify:** All log entries include the required fields defined in the standard: `timestamp` (RFC3339 UTC), `level`, `message`, `component`, `version`, `hostname`.
**How to find:** Review logging initialization and structured field setup from Step 3.

#### Check 4: Correlation Fields

**What to verify:** When available, log entries include correlation fields as defined in the standard: `trace_id`, `span_id`, `request_id`, `event_id`.
**How to find:** Review trace correlation code from Step 3.

#### Check 5: JSON Format Support

**What to verify:** The application supports JSON log format for production use with all required and contextual fields as specified in the standard.
**How to find:** Review log format configuration from Step 3.

#### Check 6: Component-Specific Fields

**What to verify:** The application includes the additional fields required by the standard for its component type (API: method, path, status_code, duration_ms; Sentinel: decision_reason, topic; Adapter: adapter, job_result).
**How to find:** Review component-specific fields from Step 3.

#### Check 7: Sensitive Data Redaction

**What to verify:** Sensitive data (API tokens, passwords, cloud provider keys, PII) is redacted from log output as required by the standard.
**How to find:** Review sensitive data handling from Step 3 and check for unredacted logging of credentials or tokens.

#### Check 8: Log Size Guidelines

**What to verify:** Log entries follow the size guidelines defined in the standard: messages under 1 KB, stack traces 10-15 frames max, total entry under 64 KB, resource IDs instead of full payloads.
**How to find:** `grep -rn "Sprintf\|fmt.Sprint\|payload\|body" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10`

#### Check 9: Distributed Tracing Integration

**What to verify:** Logging is integrated with OpenTelemetry tracing as specified in the standard: W3C traceparent propagation, CloudEvents trace_id, log correlation.
**How to find:** Review trace correlation code from Step 3.

#### Check 10: Shared Library Logger Context

**What to verify:** Shared libraries (packages used across multiple components) inherit the logging context from the calling component rather than creating their own logger instances. The standard requires that shared code receives a logger or context from the caller so that component, version, and correlation fields are preserved.
**How to find:**

```bash
# Find shared/common/library packages (scan all directories, not just pkg/internal)
find . -not -path './.git/*' -type d \( -name common -o -name shared -o -name lib -o -name pkg \) 2>/dev/null

# Check if shared packages create their own loggers vs accepting them
grep -rn "slog.New\|slog.Default\|zap.New\|zerolog.New" --include="*.go" 2>/dev/null | grep -v "_test.go" | grep -v "main.go" | head -10

# Check if shared functions accept logger/context parameters
grep -rn "func.*context.Context\|func.*\*slog.Logger\|func.*\*zap.Logger" --include="*.go" 2>/dev/null | grep -v "_test.go" | grep -v "main.go" | head -10
```

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Non-Goals | N/A (informational) |
| Shared Libraries | Shared Library Logger Context |
| Configuration | Configuration Support |
| Log Levels | Log Levels |
| Log Fields | Required Fields |
| Required Fields | Required Fields |
| Correlation Fields | Correlation Fields |
| Resource Fields | Required Fields |
| Error Fields | Required Fields |
| Log Formats | JSON Format Support |
| Text Format | JSON Format Support |
| JSON Format (Production, Default) | JSON Format Support |
| Component Guidelines | Component-Specific Fields |
| API | Component-Specific Fields |
| Sentinel | Component-Specific Fields |
| Adapters | Component-Specific Fields |
| Distributed Tracing | Distributed Tracing Integration |
| Sensitive Data | Sensitive Data Redaction |
| Log Size Guidelines | Log Size Guidelines |

## Output Format

```markdown
# Logging Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling]
**Logging Library:** [slog / zap / zerolog / logr / NOT FOUND]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Configuration Support | PASS/PARTIAL/FAIL | 0/N |
| Log Levels | PASS/PARTIAL/FAIL | 0/N |
| Required Fields | PASS/PARTIAL/FAIL | 0/N |
| Correlation Fields | PASS/PARTIAL/FAIL | 0/N |
| JSON Format Support | PASS/FAIL | 0/N |
| Component-Specific Fields | PASS/PARTIAL/FAIL | 0/N |
| Sensitive Data Redaction | PASS/PARTIAL/FAIL | 0/N |
| Log Size Guidelines | PASS/PARTIAL/FAIL | 0/N |
| Distributed Tracing | PASS/PARTIAL/FAIL | 0/N |
| Shared Library Logger | PASS/PARTIAL/FAIL/N/A | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-LOG-001: [Brief description]
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

- If the repo has no Go code: report "No Go code found -- logging review not applicable"
- If no logging code is found: report "No structured logging found in this repository"
- If the orchestrator did not supply the logging-specification standard content: report that the standard content is missing and skip the logging audit
- If the repository type is Tooling: logging checks are optional — report findings but do not flag as failures
