# Helm Chart Checks

## Review Process

### Step 1: Use the Standard Document

Use the standard document content provided by the orchestrator (fetched from the architecture repo). The orchestrator passes the full standard content to each agent — no additional fetching is needed.

### Step 2: Detect Repository Type

Determine the component type and locate the Helm chart:

```bash
# Find Helm chart
ls charts/*/Chart.yaml Chart.yaml 2>/dev/null

# API indicators
ls pkg/api/ 2>/dev/null && echo "IS_API"

# Sentinel indicators
basename $(pwd) | grep -qi sentinel && echo "IS_SENTINEL"

# Adapter indicators
basename $(pwd) | grep -q "^adapter-" && echo "IS_ADAPTER"
```

### Step 3: Find Helm Chart Artifacts

Survey the chart structure:

```bash
# Chart metadata
cat charts/*/Chart.yaml 2>/dev/null || cat Chart.yaml 2>/dev/null

# Values file
cat charts/*/values.yaml 2>/dev/null || cat values.yaml 2>/dev/null

# Templates
ls charts/*/templates/ 2>/dev/null || ls templates/ 2>/dev/null

# Helpers
cat charts/*/templates/_helpers.tpl 2>/dev/null | head -30

# NOTES.txt
ls charts/*/templates/NOTES.txt 2>/dev/null

# Security context in values
grep -n "securityContext\|podSecurityContext\|runAsNonRoot\|runAsUser" charts/*/values.yaml 2>/dev/null

# PDB
ls charts/*/templates/pdb* charts/*/templates/poddisruptionbudget* 2>/dev/null

# ServiceMonitor
ls charts/*/templates/servicemonitor* charts/*/templates/podmonitor* 2>/dev/null

# Makefile helm targets
grep -n "helm\|test-helm\|lint.*helm" Makefile 2>/dev/null

# Checksum annotations
grep -n "checksum" charts/*/templates/*.yaml 2>/dev/null
```

### Step 4: Checks

For each check, verify the chart against the requirements defined in the standard document fetched in Step 1.

#### Check 1: Naming Conventions

**What to verify:** values.yaml uses camelCase keys, generated config files use snake_case, env vars use UPPER_SNAKE_CASE with HYPERFLEET_ prefix, Kubernetes resources use kebab-case, helper templates are prefixed with chart name.
**How to find:** Review values.yaml and templates from Step 3.

#### Check 2: Mandatory values.yaml Sections

**What to verify:** All mandatory sections defined in the standard are present in values.yaml (image, replicaCount, resources, securityContext, podSecurityContext, serviceAccount, etc.).
**How to find:** Review values.yaml structure from Step 3.

#### Check 3: Chart Versioning

**What to verify:** Chart version follows SemVer 2.0, `appVersion` is `"0.0.0-dev"` in source (this applies to both component charts and umbrella charts), and `appVersion` is not used as fallback for image tag.
**How to find:** Review Chart.yaml from Step 3. For umbrella charts (e.g., in `hyperfleet-infra`), also verify that the umbrella Chart.yaml uses `appVersion: "0.0.0-dev"`.

#### Check 4: Default Security Posture

**What to verify:** Default security context matches the standard: `runAsNonRoot: true`, `runAsUser: 65532`, `allowPrivilegeEscalation: false`, drop ALL capabilities, `readOnlyRootFilesystem: true`, seccomp RuntimeDefault.
**How to find:** Review security context in values.yaml from Step 3.

#### Check 5: Secret Management

**What to verify:** Secrets are not stored in ConfigMaps, charts support `existingSecret` field, no hardcoded credentials as required by the standard.
**How to find:** `grep -rn "Secret\|secret\|password\|credential\|token" charts/*/templates/ charts/*/values.yaml 2>/dev/null`

#### Check 6: Configuration Reload

**What to verify:** Charts use checksum annotations on deployments to trigger pod restarts when ConfigMaps change.
**How to find:** Review checksum annotations from Step 3.

#### Check 7: NOTES.txt

**What to verify:** Chart includes a NOTES.txt with post-install instructions as recommended by the standard.
**How to find:** Review NOTES.txt presence from Step 3.

#### Check 8: Chart Testing

**What to verify:** Makefile includes a `test-helm` target with lint, template render, and configuration variant tests as required by the standard.
**How to find:** `grep -A10 "^test-helm:" Makefile 2>/dev/null`

#### Check 9: Standard Labels

**What to verify:** All Kubernetes resources include the recommended labels defined in the standard. `app.kubernetes.io/version` uses `.Values.image.tag` with `.Chart.AppVersion` as fallback.
**How to find:** `grep -n "app.kubernetes.io" charts/*/templates/_helpers.tpl 2>/dev/null`

#### Check 10: Image Configuration

**What to verify:** Image config follows the standard structure (registry, repository, tag, pullPolicy), includes a `validateValues` guard in `_helpers.tpl` that fails if `image.tag` is not set, the guard is invoked in `deployment.yaml`, and `image.tag` does not fall back to `.Chart.AppVersion` in templates.
**How to find:**

```bash
# Check values.yaml image structure
grep -A10 "^image:" charts/*/values.yaml 2>/dev/null

# Check for validateValues helper in _helpers.tpl
grep -n "validateValues\|image.tag" charts/*/templates/_helpers.tpl 2>/dev/null

# Check validateValues is invoked in deployment.yaml (search entire file, not just top lines)
grep -n 'include.*validateValues' charts/*/templates/deployment.yaml 2>/dev/null

# Check image.tag does NOT fall back to .Chart.AppVersion in templates
# NOTE: .Chart.AppVersion IS expected in the app.kubernetes.io/version label (Section 10).
# Only flag occurrences on image: lines or in image-related helpers.
# Step 1: Check template YAML files — only flag lines that also contain "image"
grep -n "\.Chart\.AppVersion" charts/*/templates/*.yaml 2>/dev/null | grep -v "app.kubernetes.io/version" | grep -i "image"
# Step 2: Check _helpers.tpl — exclude matches inside the labels helper block
# (the labels helper sets app.kubernetes.io/version using .Chart.AppVersion, which is allowed)
grep -n "\.Chart\.AppVersion" charts/*/templates/_helpers.tpl 2>/dev/null | grep -v "app.kubernetes.io/version" | grep -i "image"
```

#### Check 11: Deprecation Guards

**What to verify:** Breaking changes use `fail` messages for renamed keys as required by the standard. When a breaking change is introduced, the chart MUST bump its major version.
**How to find:**

```bash
# Check for fail messages on deprecated keys
grep -rn "fail\|deprecated\|renamed" charts/*/templates/ 2>/dev/null

# Check Chart.yaml version for major version bumps on breaking changes
cat charts/*/Chart.yaml 2>/dev/null | grep "version:"
```

#### Check 12: Broker Configuration Pattern

**What to verify:** If the chart includes broker configuration, `broker.type` MUST be set explicitly in values.yaml. Templates MUST NOT attempt to infer the broker type from populated sub-keys. Broker values.yaml keys MUST use camelCase, and generated `broker.yaml` config file MUST use snake_case.
**How to find:**

```bash
# Check if chart has broker configuration
grep -n "^broker:" charts/*/values.yaml 2>/dev/null

# Check broker.type exists anywhere under the broker mapping
# Use yq if available, otherwise awk-based block extraction
yq '.broker.type' charts/*/values.yaml 2>/dev/null || \
  awk '/^broker:/{flag=1} flag{print} /^[[:alnum:]_-]+:/{if(flag && !/^broker:/) exit}' charts/*/values.yaml 2>/dev/null | grep "type:"

# Check templates do not infer broker type from populated sub-keys
# Use generic regex to catch any .Values.broker.<subkey> conditional
grep -n 'if.*\.Values\.broker\.[A-Za-z0-9_]\+' charts/*/templates/*.yaml 2>/dev/null | grep -v '\.Values\.broker\.type'

# Check camelCase in values vs snake_case in generated config
# Verify camelCase broker keys in values.yaml
grep -n 'broker[A-Z]' charts/*/values.yaml 2>/dev/null
# Verify snake_case broker keys in generated configmap
grep -n 'broker_[a-z]' charts/*/templates/configmap*.yaml 2>/dev/null
```

## Coverage Map

| Standard Section | Check(s) |
|-----------------|----------|
| Key Naming Conventions | Naming Conventions |
| values.yaml Keys | Naming Conventions |
| Generated Application Config Files | Naming Conventions |
| Environment Variables | Naming Conventions |
| Kubernetes Resource Names | Naming Conventions |
| Helper Template Names | Naming Conventions |
| Values.yaml API Surface | Mandatory values.yaml Sections |
| Mandatory Sections | Mandatory values.yaml Sections |
| Conditional Sections | Mandatory values.yaml Sections |
| Chart Versioning Strategy | Chart Versioning |
| appVersion Convention | Chart Versioning |
| Default Security Posture | Default Security Posture |
| Pod Security Context (REQUIRED defaults) | Default Security Posture |
| Container Security Context (REQUIRED defaults) | Default Security Posture |
| Secret Management Pattern | Secret Management |
| Configuration Reload Strategy | Configuration Reload |
| NOTES.txt | NOTES.txt |
| Chart Testing | Chart Testing |
| Makefile Target | Chart Testing |
| Required Test Scenarios | Chart Testing |
| Test Assertions | Chart Testing |
| Deprecation and Migration Pattern | Deprecation Guards |
| Standard Labels and Annotations | Standard Labels |
| Required Labels (all resources) | Standard Labels |
| Selector Labels | Standard Labels |
| Component Labels | Standard Labels |
| Custom Labels and Annotations | Standard Labels |
| Broker Configuration Pattern | Broker Configuration Pattern |
| values.yaml Structure | Broker Configuration Pattern |
| Key Rules | Broker Configuration Pattern |
| Image Configuration | Image Configuration |
| Field Definitions | Image Configuration |
| Template Usage | Image Configuration |
| Validation Guard | Image Configuration |
| Default Values | Image Configuration |
| Enforcement | N/A (informational) |

## Output Format

```markdown
# Helm Chart Review

**Repository:** [repo name]
**Type:** [API Service / Sentinel / Adapter]
**Chart:** [chart path]

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| Naming Conventions | PASS/PARTIAL/FAIL | 0/N |
| Mandatory Sections | PASS/PARTIAL/FAIL | 0/N |
| Chart Versioning | PASS/PARTIAL/FAIL | 0/N |
| Default Security Posture | PASS/PARTIAL/FAIL | 0/N |
| Secret Management | PASS/PARTIAL/FAIL | 0/N |
| Configuration Reload | PASS/FAIL | 0/N |
| NOTES.txt | PASS/FAIL | 0/N |
| Chart Testing | PASS/FAIL | 0/N |
| Standard Labels | PASS/PARTIAL/FAIL | 0/N |
| Image Configuration | PASS/PARTIAL/FAIL | 0/N |
| Deprecation Guards | PASS/PARTIAL/FAIL/N/A | 0/N |
| Broker Configuration | PASS/PARTIAL/FAIL/N/A | 0/N |

**Overall:** X/Y checks passing

---

## Findings

### [Check Name]

**Status:** PASS/PARTIAL/FAIL

#### Issues Found

##### GAP-HLM-001: [Brief description]
- **File:** `charts/myapp/values.yaml:42`
- **Found:** [what exists in the chart]
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

- If no Helm chart is found: report "No Helm chart found -- Helm chart review not applicable"
- If the repository type is Tooling: report "Helm chart review does not apply to Tooling repositories"
- If the orchestrator did not supply the helm-chart-conventions standard content: report that the standard content is missing and skip the Helm chart audit
