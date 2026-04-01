# Error Model Checks

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

**What to verify:** Verify that error responses include all required and extension fields as defined in the standard. Check field formats and URI patterns against the standard's specification.
**How to find:** Look for error response construction in the files identified in Step 3.

#### Check 2: Error Code Taxonomy

**What to verify:** Verify that error codes follow the category format and category-to-HTTP-status mappings defined in the standard. Flag any mismatches between error code categories and HTTP status codes.
**How to find:** `grep -rn "HYPERFLEET-" --include="*.go" 2>/dev/null`

#### Check 3: HTTP Status Code Usage

**What to verify:** Verify that HTTP status codes follow the usage rules in the standard (e.g., 400 vs 422 distinction, required content type for error responses, no bare status codes without structured bodies).
**How to find:** `grep -rn "WriteHeader\|http.Error\|StatusCode" --include="*.go" 2>/dev/null`

#### Check 4: Validation Error Structure (API only)

**What to verify:** For validation errors (400/422), verify the errors array structure and constraint types match what the standard defines.
**How to find:** `grep -rn "validation\|422\|field.*constraint\|errors.*array" --include="*.go" 2>/dev/null`

#### Check 5: Error Wrapping and Propagation

**What to verify:** Verify that errors are wrapped using `%w` (not `%v`) to preserve the error chain, wrapping adds meaningful context, and internal errors are not silently swallowed. Refer to the standard for wrapping conventions.
**How to find:** `grep -rn "fmt.Errorf\|errors.New\|errors.Wrap" --include="*.go" 2>/dev/null`

#### Check 6: Security Anti-Patterns

**What to verify:** Check for security anti-patterns listed in the standard (stack traces in responses, raw internal errors exposed to clients, system paths or query details leaked in error messages).
**How to find:** `grep -rn "runtime.Stack\|debug.Stack\|err.Error()" --include="*.go" 2>/dev/null`

#### Check 7: Component-Specific Guidelines

**What to verify:** Verify the code follows the component-specific error handling guidelines defined in the standard for the detected repository type (API, Sentinel, or Adapter).
**How to find:** Read error handling code in the component's main packages and compare against the standard's requirements for this component type.

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
