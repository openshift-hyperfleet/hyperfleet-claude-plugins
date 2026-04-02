# Makefile Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched from the architecture repo). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

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

**What to verify:** Verify that Makefile variables use the names and assignment operators (e.g., `?=` for overridable) specified in the standard. All service Makefiles MUST define these four version variables: `BUILD_DATE`, `GIT_SHA`, `GIT_DIRTY`, `APP_VERSION`. The version variable MUST be named `APP_VERSION` (not `VERSION`) to avoid collision with `ubi9/go-toolset` environment.
**How to find:**

```bash
# Check variable assignments
grep -n "?=\|:=" Makefile 2>/dev/null | head -20

# Verify each of the four required version variables exists individually
grep -n "BUILD_DATE" Makefile 2>/dev/null || echo "MISSING: BUILD_DATE"
grep -n "GIT_SHA" Makefile 2>/dev/null || echo "MISSING: GIT_SHA"
grep -n "GIT_DIRTY" Makefile 2>/dev/null || echo "MISSING: GIT_DIRTY"
grep -n "APP_VERSION" Makefile 2>/dev/null || echo "MISSING: APP_VERSION"

# Check for incorrect VERSION variable (should be APP_VERSION)
grep -n "^VERSION\s*[:?]\?=" Makefile 2>/dev/null
```

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

**What to verify:** Verify that container-related targets (e.g., `container-build`, `container-push`) depend on the `check-container-tool` guard target as required by the standard. The guard ensures the container tool is available before attempting container operations.
**How to find:**

```bash
# Check if check-container-tool target exists
grep -n "^check-container-tool:" Makefile 2>/dev/null

# Verify container targets list check-container-tool as a prerequisite
grep -n "^container-build:.*check-container-tool" Makefile 2>/dev/null || echo "MISSING: container-build does not depend on check-container-tool"
grep -n "^container-push:.*check-container-tool" Makefile 2>/dev/null || echo "MISSING: container-push does not depend on check-container-tool"
```

#### Check 12: CGO_ENABLED FIPS Compliance

**What to verify:** For services that require FIPS compliance (those using `GOEXPERIMENT=boringcrypto`), verify that `CGO_ENABLED` is set to `1` as required by the standard.
**How to find:**

```bash
# Check for GOEXPERIMENT=boringcrypto usage
grep -n "GOEXPERIMENT.*boringcrypto" Makefile 2>/dev/null

# Check CGO_ENABLED setting
grep -n "CGO_ENABLED" Makefile 2>/dev/null
```

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Scope | N/A (informational) |
| Problem Statement | N/A (informational) |
| Goals | N/A (informational) |
| Standard Targets | Required Targets |
| Required Targets | Required Targets |
| Example: Required targets | N/A (informational) |
| Optional Targets | Optional Targets |
| Example: Optional targets | N/A (informational) |
| Target Naming Rules | Required Targets |
| Binary Output Location | Binary Output Directory |
| Temporary Files | Binary Output Directory |
| Repository Type Variations | Helm-Chart Repo Variations |
| Repository Types | Repo Type Detection |
| Target Equivalents for Helm-chart Repositories | Helm-Chart Repo Variations |
| Repository Type Indicator | Repo Type Detection |
| Supported repository types | Repo Type Detection |
| Audit Tool Behavior | N/A (informational) |
| Example: Service repository with Helm charts | N/A (informational) |
| Example audit output for Helm-chart repository | N/A (informational) |
| Flag Conventions | Standard Variables |
| Standard Variables | Standard Variables |
| Variable Definition Pattern | Standard Variables |
| Container Tool Auto-Detection | Container Tool Auto-Detection |
| Version Information and Git Dirty Detection | Git Dirty Detection |
| Git Dirty Detection | Git Dirty Detection |
| Standard Version Variables | Standard Variables |
| Go Build Flags | Go Build Flags |
| Example build target | N/A (informational) |
| Container Image Targets | Container Build Args |
| Required: `image` and `image-push` | Container Build Args |
| Optional: `image-dev` | Container Build Args |

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
| Container Guard Dependency | PASS/PARTIAL/FAIL/N/A | 0/N |
| CGO_ENABLED FIPS | PASS/FAIL/N/A | 0/N |

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
