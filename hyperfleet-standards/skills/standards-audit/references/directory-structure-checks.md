# Directory Structure Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# Check .hyperfleet.yaml for repo type
cat .hyperfleet.yaml 2>/dev/null

# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"
ls openapi.yaml 2>/dev/null || ls openapi/openapi.yaml 2>/dev/null && echo "HAS_OPENAPI"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"

# Check for Go module
ls go.mod 2>/dev/null && echo "IS_GO_REPO"
```

### Step 3: Survey Directory Structure

Map the current directory layout:

```bash
# Top-level directory listing
ls -la

# Find all directories (first two levels)
find . -maxdepth 2 -type d -not -path './.git*' 2>/dev/null | sort

# Check cmd/ layout
ls cmd/*/main.go 2>/dev/null

# Check for key files
ls Makefile README.md .gitignore .dockerignore Dockerfile .hyperfleet.yaml 2>/dev/null

# Check .gitignore contents
cat .gitignore 2>/dev/null

# Check .dockerignore contents
cat .dockerignore 2>/dev/null

# Check docs/ contents
ls docs/ 2>/dev/null
```

### Step 4: Checks

For each check, verify against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Required Directories and Files

**What to verify:** The repository contains all required directories and root-level files as listed in the standard for its component type.
**How to find:** Compare directory listing from Step 3 against the standard's required items.

#### Check 2: Optional Directories

**What to verify:** Any optional directories that are present follow the purpose and structure defined in the standard.
**How to find:** Review directory listing from Step 3 and validate contents of optional directories against the standard.

#### Check 3: cmd/ Layout

**What to verify:** The `cmd/` directory follows the layout conventions specified in the standard (subdirectory structure, main.go presence, package declarations).
**How to find:** Review `cmd/` listing from Step 3.

#### Check 4: bin/ in .gitignore

**What to verify:** Build output directories are gitignored as required by the standard.
**How to find:** Review `.gitignore` content from Step 3.

#### Check 5: .dockerignore Configuration

**What to verify:** If a Dockerfile or Containerfile exists, `.dockerignore` contains the exclusion patterns specified in the standard.
**How to find:** Review `.dockerignore` content from Step 3.

#### Check 6: .gitignore Mandatory Patterns

**What to verify:** `.gitignore` includes all mandatory patterns listed in the standard.
**How to find:** Review `.gitignore` content from Step 3 and compare against the standard's required patterns.

#### Check 7: .hyperfleet.yaml Metadata

**What to verify:** The `.hyperfleet.yaml` file exists and contains valid metadata fields as defined in the standard.
**How to find:** Review `.hyperfleet.yaml` content from Step 3.

#### Check 8: Temporary File Locations

**What to verify:** Compiled binaries, build artifacts, and coverage reports are placed in the locations specified by the standard.
**How to find:** Check for misplaced files: `ls *.out *.exe *.test 2>/dev/null`

#### Check 9: docs/ Structure (Service Repos)

**What to verify:** For service and adapter repos, the `docs/` directory contains the required documentation files listed in the standard.
**How to find:** Review `docs/` listing from Step 3.

## Output Format

```markdown
# Directory Structure Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling / Infrastructure]
**Files Reviewed:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Required Directories & Files | PASS/PARTIAL/FAIL | 0/N |
| Optional Directories | PASS/PARTIAL/FAIL/N/A | 0/N |
| cmd/ Layout | PASS/PARTIAL/FAIL | 0/N |
| bin/ in .gitignore | PASS/PARTIAL/FAIL | 0/N |
| .dockerignore Config | PASS/PARTIAL/FAIL/N/A | 0/N |
| .gitignore Patterns | PASS/PARTIAL/FAIL | 0/N |
| .hyperfleet.yaml Metadata | PASS/PARTIAL/FAIL | 0/N |
| Temporary File Locations | PASS/PARTIAL/FAIL | 0/N |
| docs/ Structure | PASS/PARTIAL/FAIL/N/A | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-DIR-001: [Brief description]
- **File:** `path/to/file`
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

- If the repo has no Go code: report "No Go code found -- directory structure review has reduced applicability"
- If no `go.mod` is found: report "No Go module found -- this may not be a Go repository"
- If the orchestrator did not supply the directory-structure standard content: report that the standard content is missing and skip the directory structure audit
- If the repository type is Documentation: report "Directory structure review has minimal applicability for documentation repos"
