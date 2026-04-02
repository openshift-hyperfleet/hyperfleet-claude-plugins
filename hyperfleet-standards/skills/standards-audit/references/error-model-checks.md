# Error Model Checks

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

### Step 3: Find Relevant Code

Search for files that handle errors returned to clients or logged:

```bash
# HTTP error responses
grep -rl "WriteHeader\|http.Error\|JSON.*error\|problem.json\|application/problem" --include="*.go" 2>/dev/null

# Error constructors/types
grep -rl "ProblemDetails\|NewError\|ErrorResponse\|ErrResponse" --include="*.go" 2>/dev/null

# Error wrapping
grep -rn "fmt.Errorf\|errors.New\|errors.Wrap" --include="*.go" 2>/dev/null | head -30

# Error code usage
grep -rn "HYPERFLEET-" --include="*.go" 2>/dev/null
```

### Step 4: Checks

For each check, verify the code against the requirements defined in the standard document fetched in Step 1.

#### Check 1: RFC 9457 Structure (API only)

**What to verify:** Verify that error responses include all required fields (`type`, `title`, `status`, `detail`, `instance`) and all extension fields (`code`, `timestamp`, `trace_id`, `errors`) as defined in the standard. The `type` field MUST be a registered problem type URI as defined in the standard (e.g., `https://<api-host>/problems/validation-error`, `https://<api-host>/problems/authentication-required`). The `timestamp` field MUST use RFC 3339 format. Error responses MUST use `application/problem+json` as the Content-Type header.
**How to find:**

```bash
# Look for error response construction
grep -rn "ProblemDetails\|NewError\|ErrorResponse\|problem.json\|application/problem" --include="*.go" 2>/dev/null

# Check Content-Type header setting
grep -rn "application/problem\+json\|problem.json" --include="*.go" 2>/dev/null

# Check timestamp format
grep -rn "RFC3339\|time.Now\|timestamp" --include="*.go" 2>/dev/null | grep -i "error\|problem" | head -10
```

#### Check 2: Error Code Taxonomy

**What to verify:** Verify that error codes follow the category format and category-to-HTTP-status mappings defined in the standard. Flag any mismatches between error code categories and HTTP status codes.
**How to find:** `grep -rn "HYPERFLEET-" --include="*.go" 2>/dev/null`

#### Check 3: HTTP Status Code Usage

**What to verify:** Verify that HTTP status codes follow the usage rules in the standard (e.g., 400 vs 422 distinction, required content type for error responses, no bare status codes without structured bodies).
**How to find:** `grep -rn "WriteHeader\|http.Error\|StatusCode" --include="*.go" 2>/dev/null`

#### Check 4: Validation Error Structure (API only)

**What to verify:** For validation errors (400/422), verify the errors array structure and constraint types match what the standard defines. When multiple validation errors exist, the error code MUST be `VAL-000` (generic validation); specific codes (e.g., `VAL-001`) are for single-error responses only.
**How to find:** `grep -rn "validation\|422\|field.*constraint\|errors.*array\|VAL-000\|VAL-00" --include="*.go" 2>/dev/null`

#### Check 5: Error Wrapping and Propagation

**What to verify:** Verify that errors are wrapped using `%w` (not `%v`) to preserve the error chain, wrapping adds meaningful context, and internal errors are not silently swallowed. Refer to the standard for wrapping conventions.
**How to find:** `grep -rn "fmt.Errorf\|errors.New\|errors.Wrap" --include="*.go" 2>/dev/null`

#### Check 6: Security Anti-Patterns

**What to verify:** Check for security anti-patterns listed in the standard (stack traces in responses, raw internal errors exposed to clients, system paths or query details leaked in error messages). Also verify that full error details are logged internally before sanitizing for external responses — the standard requires logging complete error context for debugging while returning only safe, sanitized information to clients.
**How to find:**

```bash
# Check for stack traces and raw errors in responses
grep -rn "runtime.Stack\|debug.Stack\|err.Error()" --include="*.go" 2>/dev/null

# Verify errors are logged before being sanitized for responses
grep -B5 -A5 "WriteHeader\|WriteJSON\|problem" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10
```

#### Check 7: Component-Specific Guidelines

**What to verify:** Verify the code follows the component-specific error handling guidelines defined in the standard for the detected repository type:
- **API**: MUST return RFC 9457 responses with `application/problem+json`, MUST include `Retry-After` header for 429 responses
- **Sentinel**: MUST wrap errors with context before propagating, MUST use structured logging for errors
- **Adapter**: MUST map provider-specific errors to HyperFleet error codes, MUST NOT leak provider error details to callers
**How to find:**

```bash
# API: Check for Retry-After header on 429 responses
grep -rn "429\|TooManyRequests\|Retry-After" --include="*.go" 2>/dev/null

# Adapter: Check for provider error mapping
grep -rn "MapError\|translateError\|convertError\|provider.*error" --include="*.go" 2>/dev/null | head -10

# Component error handling patterns
grep -rn "WriteHeader\|http.Error\|JSON.*error" --include="*.go" 2>/dev/null | head -20
```

#### Check 8: Error Logging Integration

**What to verify:** Error responses MUST be logged following the Logging Specification. Verify that error responses are logged with the required fields: `error_code`, `error_type`, `trace_id`, and `request_context`.
**How to find:**

```bash
# Check if error response code logs errors
grep -rn "error_code\|error_type\|Error.*log\|log.*Error" --include="*.go" 2>/dev/null | head -20

# Check for structured error logging near error response construction
grep -B5 -A5 "WriteJSON\|WriteHeader\|problem" --include="*.go" 2>/dev/null | grep -i "log\|slog\|zap" | head -10
```

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Goals | N/A (informational) |
| Non-Goals | N/A (informational) |
| Reference Implementation | N/A (informational) |
| RFC 9457 Problem Details | RFC 9457 Structure |
| Basic Structure | RFC 9457 Structure |
| Standard Fields (RFC 9457) | RFC 9457 Structure |
| HyperFleet Extension Fields | RFC 9457 Structure |
| Complete Example | N/A (informational) |
| Problem Types | RFC 9457 Structure |
| Type URI Format | RFC 9457 Structure |
| Registered Problem Types | RFC 9457 Structure |
| Error Code Format | Error Code Taxonomy |
| Format | Error Code Taxonomy |
| Error Categories | Error Code Taxonomy |
| HTTP Status Code Mapping | HTTP Status Code Usage |
| Client Errors (4xx) | HTTP Status Code Usage |
| Server Errors (5xx) | HTTP Status Code Usage |
| Mapping Policy | HTTP Status Code Usage |
| Validation Errors | Validation Error Structure |
| Single Validation Error | Validation Error Structure |
| Multiple Validation Errors | Validation Error Structure |
| Validation Constraint Types | Validation Error Structure |
| Standard Error Codes | Error Code Taxonomy |
| Validation Errors (VAL) | Error Code Taxonomy, Validation Error Structure |
| Authentication Errors (AUT) | Error Code Taxonomy |
| Authorization Errors (AUZ) | Error Code Taxonomy |
| Not Found Errors (NTF) | Error Code Taxonomy |
| Conflict Errors (CNF) | Error Code Taxonomy |
| Rate Limit Errors (LMT) | Error Code Taxonomy |
| Internal Errors (INT) | Error Code Taxonomy |
| Service Errors (SVC) | Error Code Taxonomy |
| Error Wrapping and Propagation | Error Wrapping and Propagation |
| Internal Error Handling | Error Wrapping and Propagation, Security Anti-Patterns |
| Security Considerations | Security Anti-Patterns |
| Component-Specific Guidelines | Component-Specific Guidelines |
| API Service | Component-Specific Guidelines |
| Sentinel | Component-Specific Guidelines |
| Adapters | Component-Specific Guidelines |
| Error Logging Integration | Error Logging Integration |
| Example Error Responses | N/A (informational) |
| Validation Error | N/A (informational) |
| Resource Not Found | N/A (informational) |
| Version Conflict | N/A (informational) |
| Rate Limit Exceeded | N/A (informational) |
| Internal Server Error | N/A (informational) |

## Output Format

```markdown
# Error Model Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| RFC 9457 Structure | PASS/PARTIAL/FAIL/N/A | 0/N |
| Error Code Taxonomy | PASS/PARTIAL/FAIL | 0/N |
| HTTP Status Codes | PASS/PARTIAL/FAIL/N/A | 0/N |
| Validation Errors | PASS/PARTIAL/FAIL/N/A | 0/N |
| Error Wrapping | PASS/PARTIAL/FAIL | 0/N |
| Security | PASS/PARTIAL/FAIL | 0/N |
| Component Guidelines | PASS/PARTIAL/FAIL | 0/N |
| Error Logging Integration | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-ERR-001: [Brief description]
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

- If the repo has no Go code: report "No Go code found -- error model review not applicable"
- If no error handling code is found: report "No error handling patterns found in this repository"
- If the orchestrator did not supply the error-model standard content: report that the standard content is missing and skip the error model audit
