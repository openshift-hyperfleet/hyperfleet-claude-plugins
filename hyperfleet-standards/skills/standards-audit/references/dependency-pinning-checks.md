# Dependency Pinning Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via the `hyperfleet-architecture` skill). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# Check for Go module
ls go.mod 2>/dev/null && echo "IS_GO_REPO"

# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"

# Tooling indicators
basename $(pwd) | grep -qi "tooling\|tools\|cli" && echo "IS_TOOLING"
```

### Step 3: Find Dependency Pinning Artifacts

Search for bingo-related files and tool references:

```bash
# .bingo directory
ls -la .bingo/ 2>/dev/null

# .bingo contents
ls .bingo/*.mod .bingo/*.sum 2>/dev/null

# Variables.mk
cat .bingo/Variables.mk 2>/dev/null | head -30

# .bingo/.gitignore
cat .bingo/.gitignore 2>/dev/null

# Makefile references to bingo
grep -n "bingo\|Variables.mk\|BINGO" Makefile 2>/dev/null

# Tool references in Makefile
grep -n "golangci-lint\|mockgen\|oapi-codegen\|controller-gen\|goimports" Makefile 2>/dev/null

# Tools in root go.mod (should NOT be there)
grep -n "golangci-lint\|mockgen\|oapi-codegen\|controller-gen" go.mod 2>/dev/null
```

### Step 4: Checks

For each check, verify against the requirements defined in the standard document fetched in Step 1.

#### Check 1: .bingo/ Directory Structure

**What to verify:** The `.bingo/` directory exists and contains all required files (`.gitignore`, `Variables.mk`, per-tool `.mod` and `.sum` files) as specified in the standard.
**How to find:** Review directory listing from Step 3.

#### Check 2: .bingo/.gitignore Configuration

**What to verify:** The `.bingo/.gitignore` contains the patterns required by the standard to ignore tool binaries.
**How to find:** Review `.bingo/.gitignore` content from Step 3.

#### Check 3: Variables.mk Content

**What to verify:** `Variables.mk` defines tool variables with version pinning and correct build commands as specified in the standard.
**How to find:** Review `Variables.mk` content from Step 3.

#### Check 4: Makefile Integration

**What to verify:** The Makefile includes `Variables.mk` and uses bingo variables to reference tools, following the integration pattern defined in the standard.
**How to find:** Review Makefile references from Step 3.

#### Check 5: Required Makefile Targets

**What to verify:** The Makefile includes the required tool management targets defined in the standard.
**How to find:** `grep -n "^tools-\|^\.PHONY.*tools-" Makefile 2>/dev/null`

#### Check 6: Tool Isolation

**What to verify:** Tool dependencies are isolated from project dependencies as required by the standard (not in root `go.mod`, separate `.mod` per tool).
**How to find:** Review root `go.mod` tool references from Step 3.

#### Check 7: Common Tools Pinned

**What to verify:** Tools used by the project are pinned via bingo rather than installed ad-hoc. Verify against the standard's list of commonly expected tools.
**How to find:** Cross-reference tools used in Makefile with `.bingo/*.mod` files from Step 3.

#### Check 8: Tool Binaries Gitignored

**What to verify:** Tool binaries are not committed to the repository and are properly gitignored as required by the standard.
**How to find:** `git ls-files .bingo/ 2>/dev/null | grep -v -E '\.(mod|sum|mk|gitignore)$'`

## Output Format

```markdown
# Dependency Pinning Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| .bingo/ Directory Structure | PASS/PARTIAL/FAIL | 0/N |
| .bingo/.gitignore Config | PASS/PARTIAL/FAIL | 0/N |
| Variables.mk Content | PASS/PARTIAL/FAIL | 0/N |
| Makefile Integration | PASS/PARTIAL/FAIL | 0/N |
| Required Makefile Targets | PASS/PARTIAL/FAIL | 0/N |
| Tool Isolation | PASS/PARTIAL/FAIL | 0/N |
| Common Tools Pinned | PASS/PARTIAL/FAIL | 0/N |
| Tool Binaries Gitignored | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-DEP-001: [Brief description]
- **File:** `path/to/file:42`
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

- If the repo has no Go code: report "No Go code found -- dependency pinning review not applicable"
- If no `.bingo/` directory is found: report "No .bingo/ directory found -- dependency pinning is not configured"
- If the orchestrator did not supply the dependency-pinning standard content: report that the standard content is missing and skip the dependency pinning audit
- If the repository type is Infrastructure or Documentation: report "Dependency pinning review does not apply to this repository type"
