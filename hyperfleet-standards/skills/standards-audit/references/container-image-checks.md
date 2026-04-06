# Container Image Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched via `gh api`). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type to apply the correct checks:

```bash
# Check if repo produces container images
{ test -f Dockerfile || test -f Containerfile; } && echo "HAS_DOCKERFILE"

# Check .hyperfleet.yaml for repo type
cat .hyperfleet.yaml 2>/dev/null

# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"
```

### Step 3: Find Container Build Artifacts

Search for Dockerfile and build-related files:

```bash
# Dockerfile / Containerfile content (show both if present)
for f in Dockerfile Containerfile; do test -f "$f" && echo "=== $f ===" && cat "$f"; done

# .dockerignore
cat .dockerignore 2>/dev/null

# Makefile build/image targets
grep -n "image\|docker\|podman\|container\|CONTAINER_TOOL\|BASE_IMAGE\|APP_VERSION" Makefile 2>/dev/null

# Build args and ldflags
grep -n "ldflags\|LDFLAGS\|trimpath\|GIT_SHA\|BUILD_DATE" Makefile 2>/dev/null
```

### Step 4: Checks

For each check, verify the Dockerfile and build configuration against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Base Images

**What to verify:** Builder and runtime stages use the base images specified in the standard. No unapproved base images.
**How to find:** `grep -n "^FROM\|^ARG BASE_IMAGE" {Dockerfile,Containerfile} 2>/dev/null`

#### Check 2: Multi-Stage Build

**What to verify:** Dockerfile uses multi-stage build with separate builder and runtime stages as required by the standard.
**How to find:** `grep -c "^FROM" {Dockerfile,Containerfile} 2>/dev/null` (should be >= 2)

#### Check 3: Non-Root User

**What to verify:** Builder and runtime stages use the user IDs specified in the standard. Root is only used temporarily for package installation.
**How to find:** `grep -n "^USER" {Dockerfile,Containerfile} 2>/dev/null`

#### Check 4: Go Build Parameters

**What to verify:** Build uses the Go build flags and ldflags required by the standard. CGO setting matches the standard's requirements.
**How to find:** Review Makefile build targets and Dockerfile RUN commands from Step 3.

#### Check 5: Container Labels

**What to verify:** All required OCI labels defined in the standard are present. The standard specifies which label keys are mandatory — verify each one.
**How to find:** Extract the list of required label keys from the standard document, then check for each:

```bash
# List all LABEL directives to compare against the standard's required labels
grep -nE '^[[:space:]]*LABEL' Dockerfile Containerfile 2>/dev/null
```

#### Check 6: .dockerignore

**What to verify:** A `.dockerignore` file exists at the repository root as required by the standard.
**How to find:** `ls .dockerignore 2>/dev/null`

#### Check 7: CA Certificates

**What to verify:** CA certificates are copied from the builder stage to the runtime stage for TLS support, since minimal base images may not include them.
**How to find:** `grep -n "ca-trust\|ca-certificates\|tls-ca-bundle" {Dockerfile,Containerfile} 2>/dev/null`

#### Check 8: Cache Mounts

**What to verify:** Go module and build caches use `--mount=type=cache` for efficient rebuilds as recommended by the standard.
**How to find:** `grep -n "mount=type=cache" {Dockerfile,Containerfile} 2>/dev/null`

#### Check 9: Version Variable Convention

**What to verify:** The Dockerfile and Makefile use the version variable name specified in the standard to avoid collision with base image environment variables.
**How to find:** `grep -n "VERSION" {Dockerfile,Containerfile} Makefile 2>/dev/null`

#### Check 10: Platform Specification

**What to verify:** Container builds specify the target platform as required by the standard.
**How to find:** `grep -n "PLATFORM\|--platform" Makefile {Dockerfile,Containerfile} 2>/dev/null`

## Output Format

```markdown
# Container Image Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Dockerfile:** [path or "NOT FOUND"]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Base Images | PASS/PARTIAL/FAIL | 0/N |
| Multi-Stage Build | PASS/FAIL | 0/N |
| Non-Root User | PASS/PARTIAL/FAIL | 0/N |
| Go Build Parameters | PASS/PARTIAL/FAIL | 0/N |
| Container Labels | PASS/PARTIAL/FAIL | 0/N |
| .dockerignore | PASS/FAIL | 0/N |
| CA Certificates | PASS/FAIL | 0/N |
| Cache Mounts | PASS/FAIL | 0/N |
| Version Variable Convention | PASS/FAIL | 0/N |
| Platform Specification | PASS/FAIL | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-IMG-001: [Brief description]
- **File:** `Dockerfile:42`
- **Found:** [what exists in the file]
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

- If no Dockerfile or Containerfile is found: report "No Dockerfile found -- container image review not applicable"
- If the repository type is Infrastructure or Tooling without a Dockerfile: report "Container image review does not apply to this repository type"
- If the orchestrator did not supply the container-image standard content: report that the standard content is missing and skip the container image audit
