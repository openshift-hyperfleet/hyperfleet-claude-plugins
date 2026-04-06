# Logging Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

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

# Log configuration — search for generic log config patterns; exact env var names are defined in the standard
grep -rn "log.*level\|log.*format\|log.*output\|SetLevel\|SetFormatter" --include="*.go" 2>/dev/null | head -20

# Structured logging fields
grep -rn "\.With(\|\.WithField\|\.WithValues\|slog\.String\|slog\.Int\|slog\.Any" --include="*.go" 2>/dev/null | head -20

# Required fields (component, version, hostname)
grep -rn "component\|version\|hostname" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10

# Trace correlation — search for correlation field patterns; exact field names are defined in the standard
grep -rn "trace.*id\|span.*id\|request.*id\|event.*id\|TraceID\|SpanID\|correlation" --include="*.go" 2>/dev/null | head -10

# Sensitive data handling
grep -rn "redact\|mask\|sanitize\|scrub" --include="*.go" 2>/dev/null | head -10

# Component-specific fields — search for field names defined in the standard for the detected repo type
grep -rn "With\|WithField\|WithValues" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Configuration Support

**What to verify:** The application supports the log configuration flags and environment variables defined in the standard, with the correct defaults.
**How to find:** Review log configuration code from Step 3.

#### Check 2: Log Levels

**What to verify:** The application supports all log levels defined in the standard and uses them for the appropriate scenarios as described in the standard.
**How to find:** `grep -rn "Debug\|Info\|Warn\|Error" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -20`

#### Check 3: Required Fields

**What to verify:** All log entries include the required fields defined in the standard.
**How to find:** Review logging initialization and structured field setup from Step 3.

#### Check 4: Correlation Fields

**What to verify:** When available, log entries include the correlation fields defined in the standard.
**How to find:** Review trace correlation code from Step 3.

#### Check 5: JSON Format Support

**What to verify:** The application supports JSON log format for production use with all required and contextual fields as specified in the standard.
**How to find:** Review log format configuration from Step 3.

#### Check 6: Component-Specific Fields

**What to verify:** The application includes the additional fields required by the standard for its component type.
**How to find:** Review component-specific fields from Step 3.

#### Check 7: Sensitive Data Redaction

**What to verify:** Sensitive data categories listed in the standard are redacted from log output as required.
**How to find:** Review sensitive data handling from Step 3 and check for unredacted logging of credentials or tokens.

#### Check 8: Log Size Guidelines

**What to verify:** Log entries follow the size guidelines defined in the standard (message size, stack trace depth, total entry size, payload handling).
**How to find:** `grep -rn "Sprintf\|fmt.Sprint\|payload\|body" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10`

#### Check 9: Distributed Tracing Integration

**What to verify:** Logging is integrated with distributed tracing as specified in the standard (propagation format, correlation fields, integration mechanism).
**How to find:** Review trace correlation code from Step 3.

#### Check 10: Shared Library Logger Context Inheritance

**What to verify:** Verify that shared/library packages accept a logger via context or constructor injection (not global loggers) so that caller context (trace IDs, component fields) is preserved, as required by the standard.
**How to find:** `grep -rn "func New\|func Init\|slog.Default\|log.Default\|zap.L()\|zap.S()" --include="*.go" 2>/dev/null | head -10`

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
| Logger Context Inheritance | PASS/PARTIAL/FAIL | 0/N |

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
