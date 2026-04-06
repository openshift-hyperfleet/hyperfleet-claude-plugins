# Makefile Checks

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

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"

# Helm chart indicators
ls Chart.yaml 2>/dev/null && echo "IS_HELM_CHART"
ls charts/ 2>/dev/null && echo "HAS_CHARTS_DIR"
```

### Step 3: Find Relevant Code

Search for Makefile and related configuration:

```bash
# Makefile
ls Makefile 2>/dev/null

# Additional make includes
grep -n "^include\|^-include" Makefile 2>/dev/null

# .hyperfleet.yaml for repo metadata
cat .hyperfleet.yaml 2>/dev/null

# All Makefile targets
grep -n "^[a-zA-Z_-]*:" Makefile 2>/dev/null

# Variable assignments
grep -n "?=\|:=\|=" Makefile 2>/dev/null | head -20
```

### Step 4: Checks

For each check, verify the Makefile against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Required Targets

**What to verify:** Verify that all required Makefile targets defined in the standard are present. The standard lists different required targets for different repo types.
**How to find:** `grep -n "^[a-zA-Z_-]*:" Makefile 2>/dev/null`

#### Check 2: Optional Targets

**What to verify:** For any optional targets that are present, verify they follow the naming and behavior conventions defined in the standard.
**How to find:** Same grep as Check 1; compare against the standard's optional target list.

#### Check 3: Binary Output Directory

**What to verify:** Verify that binary output location, .gitignore entry, and clean target behavior match the standard's requirements.
**How to find:** `grep -n "bin/\|\.gitignore" Makefile .gitignore 2>/dev/null`

#### Check 4: Standard Variables

**What to verify:** Verify that Makefile variables use the names and assignment operators (e.g., `?=` for overridable) specified in the standard.
**How to find:** `grep -n "?=\|:=" Makefile 2>/dev/null | head -20`

#### Check 5: Container Tool Auto-Detection

**What to verify:** Verify that the Makefile prefers the container tool and uses the detection approach specified in the standard.
**How to find:** `grep -n "podman\|docker\|CONTAINER_TOOL\|container-tool" Makefile 2>/dev/null`

#### Check 6: Git Dirty Detection

**What to verify:** Verify that git dirty detection uses the method specified in the standard (not alternatives that may be unreliable) and applies the correct suffix.
**How to find:** `grep -n "git status\|git diff\|dirty" Makefile 2>/dev/null`

#### Check 7: Go Build Flags

**What to verify:** Verify that Go build commands include the flags and ldflags injections required by the standard.
**How to find:** `grep -n "go build\|ldflags\|trimpath" Makefile 2>/dev/null`

#### Check 8: Container Build Args

**What to verify:** Verify that container build commands pass the build arguments required by the standard.
**How to find:** `grep -n "build-arg\|--platform\|image:" Makefile 2>/dev/null`

#### Check 9: Repo Type Detection

**What to verify:** Verify that `.hyperfleet.yaml` exists with repo type metadata and that Makefile targets are consistent with the declared type, as required by the standard.
**How to find:** `cat .hyperfleet.yaml 2>/dev/null`

#### Check 10: Helm-Chart Repo Variations

**What to verify:** For Helm chart repositories, verify that the Makefile uses the Helm-specific target names and omits Go-specific targets as defined in the standard.
**How to find:** `grep -n "helm-lint\|helm-template\|test-helm" Makefile 2>/dev/null`

#### Check 11: Container Target Guard Dependency

**What to verify:** Verify that container build targets depend on prerequisite targets (e.g., `build`, `test`) as required by the standard, ensuring that a container image cannot be built without passing compilation and tests first.
**How to find:** `grep -A3 "^container\|^image\|^docker-build\|^podman-build" Makefile 2>/dev/null`

## Output Format

```markdown
# Makefile Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter / Tooling / Infrastructure]
**Makefile Found:** [Yes/No]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Required Targets | PASS/PARTIAL/FAIL | 0/N |
| Optional Targets | PASS/PARTIAL/FAIL | 0/N |
| Binary Output Directory | PASS/PARTIAL/FAIL/N/A | 0/N |
| Standard Variables | PASS/PARTIAL/FAIL | 0/N |
| Container Tool Detection | PASS/PARTIAL/FAIL | 0/N |
| Git Dirty Detection | PASS/PARTIAL/FAIL | 0/N |
| Go Build Flags | PASS/PARTIAL/FAIL/N/A | 0/N |
| Container Build Args | PASS/PARTIAL/FAIL/N/A | 0/N |
| Repo Type Detection | PASS/PARTIAL/FAIL | 0/N |
| Helm-Chart Variations | PASS/PARTIAL/FAIL/N/A | 0/N |
| Container Target Guard | PASS/PARTIAL/FAIL/N/A | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-MAK-001: [Brief description]
- **File:** `Makefile:42`
- **Found:** [what exists in the Makefile]
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

- If no Makefile is found: report "No Makefile found -- Makefile review not applicable"
- If no `.hyperfleet.yaml` is found: report as a Minor finding and infer repo type from directory structure
- If the orchestrator did not supply the makefile-conventions standard content: report that the standard content is missing and skip the makefile audit
