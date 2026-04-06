# Generated Code Policy Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Find Generated Code

Search for generated code markers and generation tooling:

```bash
# Generated file markers
grep -rl "DO NOT EDIT\|Code generated\|AUTO-GENERATED\|@generated" --include="*.go" . 2>/dev/null

# Code generation tools in Makefile
grep -n "generate\|codegen\|oapi-codegen\|mockgen\|protoc\|controller-gen\|deepcopy-gen" Makefile 2>/dev/null

# go generate directives
grep -rn "//go:generate" --include="*.go" . 2>/dev/null

# Generated file patterns
ls zz_generated*.go *_generated.go 2>/dev/null
find . -name "zz_generated*" -o -name "*_generated.go" 2>/dev/null | head -20

# Linter exclusions for generated code
grep -n "generated\|exclude" .golangci.yml .golangci.yaml .golangci.toml 2>/dev/null | head -10

# .gitattributes for generated files
cat .gitattributes 2>/dev/null
```

### Step 3: Checks

For each check, verify against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Generated File Markers

**What to verify:** All generated files include the marker comment or header required by the standard so that tools and reviewers can identify them.
**How to find:** Cross-reference generated files found in Step 2 with the marker format defined in the standard.

#### Check 2: Generation Makefile Target

**What to verify:** A Makefile target exists for code generation as required by the standard, and it regenerates all generated files.
**How to find:** Review Makefile targets from Step 2.

#### Check 3: Generated Files Committed

**What to verify:** Generated files are committed to the repository (or excluded) per the policy defined in the standard.
**How to find:** `git status --short` to check for uncommitted generated files, and `.gitignore` for exclusion patterns.

#### Check 4: Linter Exclusions

**What to verify:** Generated files are excluded from linting using the patterns or markers specified in the standard.
**How to find:** Review golangci-lint config exclusions from Step 2.

#### Check 5: Freshness Verification

**What to verify:** There is a mechanism to verify that generated files are up to date (e.g., CI check, Makefile target) as required by the standard.
**How to find:** `grep -rn "verify.*generate\|check.*generate\|generate.*verify" Makefile .github/ 2>/dev/null`

#### Check 6: Generation Tool Pinning

**What to verify:** Code generation tools are version-pinned as required by the standard (e.g., via bingo or go.mod).
**How to find:** Cross-reference tools found in Makefile with `.bingo/` or `go.mod` entries.

#### Check 7: Generate as Prerequisite for Build and Test

**What to verify:** Verify that the `generate` target is a prerequisite for `build` and `test` targets as required by the standard, ensuring generated code is always up to date before compilation and testing.
**How to find:** `grep -n "^build\|^test" Makefile 2>/dev/null` — check if `generate` appears in the dependency list.

## Output Format

```markdown
# Generated Code Policy Review

**Repository:** [repo name]
**Generated Files Found:** [count]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| File Markers | PASS/PARTIAL/FAIL | 0/N |
| Generation Target | PASS/PARTIAL/FAIL | 0/N |
| Files Committed | PASS/PARTIAL/FAIL | 0/N |
| Linter Exclusions | PASS/PARTIAL/FAIL | 0/N |
| Freshness Verification | PASS/PARTIAL/FAIL | 0/N |
| Tool Pinning | PASS/PARTIAL/FAIL | 0/N |
| Generate Prerequisite | PASS/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-GEN-001: [Brief description]
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

- If no generated code is found: report "No generated code found -- generated code policy review not applicable"
- If the repository type is Infrastructure or Documentation: report "Generated code policy review does not apply to this repository type"
- If the orchestrator did not supply the generated code policy standard content: report that the standard content is missing and skip the generated code policy audit
