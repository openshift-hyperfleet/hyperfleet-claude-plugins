# Linting Checks

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
basename $(pwd) | grep -qi "tool\|cli\|util" && echo "IS_TOOLING"
```

### Step 3: Find Relevant Code

Search for linting-related files:

```bash
# golangci-lint config
ls .golangci.yml .golangci.yaml .golangci.toml 2>/dev/null

# Makefile lint target
grep -n "^lint:" Makefile 2>/dev/null
grep -n "golangci-lint" Makefile 2>/dev/null

# golangci-lint version
grep -rn "golangci-lint" Makefile .github/ 2>/dev/null | head -10

# Nolint directives
grep -rn "//nolint" --include="*.go" . 2>/dev/null | head -20
```

### Step 4: Checks

For each check, verify the configuration against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Configuration File Exists

**What to verify:** Verify that a golangci-lint configuration file exists at the repository root in the format specified by the standard.
**How to find:** `ls .golangci.yml .golangci.yaml .golangci.toml 2>/dev/null`

#### Check 2: Required Linters Enabled

**What to verify:** Compare the list of enabled linters in the config against the required linters defined in the standard. Flag any missing linters.
**How to find:** Read the repository's golangci-lint config (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`) and check the `linters` / `enable` section.

#### Check 3: Required Formatters

**What to verify:** Verify that the formatters section includes all formatters required by the standard.
**How to find:** Read the repository's golangci-lint config (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`) and check the `formatters` section.

#### Check 4: Linter Settings

**What to verify:** Verify that individual linter settings (under `linters-settings` or `settings`) match the values specified in the standard.
**How to find:** Read the repository's golangci-lint config (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`) and compare settings values against the standard.

#### Check 5: Generated Code Exclusions

**What to verify:** Verify that generated files are excluded from linting using the patterns or markers specified in the standard.
**How to find:** Read the repository's golangci-lint config (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`) and check `issues.exclude-rules` or `exclusions` sections.

#### Check 6: Test File Relaxations

**What to verify:** Verify that the linters specified in the standard are relaxed for test files (`_test.go`).
**How to find:** Read the repository's golangci-lint config (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`) and check for path-based exclusion rules targeting test files.

#### Check 7: Make Lint Target

**What to verify:** Verify that a `make lint` target exists, invokes golangci-lint as specified by the standard, and does not disable any baseline linters.
**How to find:** `grep -A5 "^lint:" Makefile 2>/dev/null`

#### Check 8: golangci-lint Version

**What to verify:** Verify the golangci-lint version matches the major version required by the standard and is consistent across Makefile, CI, and install scripts.
**How to find:** `grep -rn "golangci-lint.*v[0-9]" Makefile .github/ 2>/dev/null`

#### Check 9: No Baseline Linters Disabled

**What to verify:** Verify that no required linters are disabled in configuration or skipped in command invocations. Check that `//nolint` directives are rare and include justification as required by the standard.
**How to find:**

```bash
# Check config and Makefile for disabled linters or skipped checks
grep -rn "disable\|--skip" .golangci.yml .golangci.yaml .golangci.toml Makefile 2>/dev/null | head -10
# Check Go source files for nolint directives
grep -rn "//nolint" --include="*.go" . 2>/dev/null | head -20
```

#### Check 10: Run Timeout

**What to verify:** Verify that `run.timeout` is set to at least 5 minutes (`5m`) in the golangci-lint configuration as required by the standard.
**How to find:** Read the golangci-lint config and check the `run` section for `timeout`.

#### Check 11: Override Comments

**What to verify:** Verify that any overrides or customizations in the golangci-lint configuration (e.g., disabled rules, changed thresholds, path exclusions beyond generated code) include explanatory comments justifying the deviation as required by the standard.
**How to find:** Read the golangci-lint config and check for overrides without adjacent comments.

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Configuration File | Configuration File Exists |
| Enabled Linters | Required Linters Enabled |
| Code Quality | Required Linters Enabled |
| Code Style | Required Linters Enabled |
| Formatters | Required Formatters |
| Security | Required Linters Enabled |
| Linter Settings | Linter Settings |
| errcheck | Linter Settings |
| govet | Linter Settings |
| goconst | Linter Settings |
| misspell | Linter Settings |
| lll | Linter Settings |
| revive | Linter Settings |
| unparam | Linter Settings |
| exhaustive | Linter Settings |
| Formatter Settings | Required Formatters |
| gofmt | Required Formatters |
| Standard Exclusions | Generated Code Exclusions, Test File Relaxations |
| Generated Code | Generated Code Exclusions |
| Test Files | Test File Relaxations |
| Performance Settings | Run Timeout |
| Output Configuration | N/A (informational) |
| Repository-Specific Overrides | No Baseline Linters Disabled, Override Comments |
| Allowed Overrides | Override Comments |
| Not Allowed | No Baseline Linters Disabled |
| Documenting Overrides | Override Comments |
| CI Integration | Make Lint Target |
| Makefile Target | Make Lint Target |
| Pre-commit Hook (Optional) | N/A (optional) |
| Version Requirements | golangci-lint Version |
| Adopting This Standard | N/A (informational) |

## Output Format

```markdown
# Linting Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling]
**Config File:** [.golangci.yml path or "NOT FOUND"]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Configuration File | PASS/FAIL | 0/N |
| Required Linters | PASS/PARTIAL/FAIL | 0/N |
| Required Formatters | PASS/PARTIAL/FAIL | 0/N |
| Linter Settings | PASS/PARTIAL/FAIL | 0/N |
| Generated Code Exclusions | PASS/PARTIAL/FAIL | 0/N |
| Test File Relaxations | PASS/PARTIAL/FAIL | 0/N |
| Make Lint Target | PASS/FAIL | 0/N |
| golangci-lint Version | PASS/FAIL | 0/N |
| No Baseline Disabled | PASS/FAIL | 0/N |
| Run Timeout | PASS/FAIL | 0/N |
| Override Comments | PASS/PARTIAL/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-LNT-001: [Brief description]
- **File:** `path/to/config:42`
- **Found:** [what exists in the configuration]
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

- If the repo has no Go code: report "No Go code found -- linting review not applicable"
- If no golangci-lint config is found (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`): report as a Critical finding and continue checking other items
- If the orchestrator did not supply the linting standard content: report that the standard content is missing and skip the linting audit
