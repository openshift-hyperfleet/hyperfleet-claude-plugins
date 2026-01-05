---
name: HyperFleet Standards Audit
description: Audits local HyperFleet repositories against team architecture standards dynamically fetched from the architecture repo. Activates when users ask to audit repos, check standards compliance, or identify standards gaps. READ-ONLY - does not modify any files. Produces JIRA-ready gap specifications for integration with jira-ticket-creator skill.
---

# HyperFleet Standards Audit Skill

## CRITICAL: READ-ONLY MODE

**This skill MUST NOT modify any files in the repository being audited.** All operations are read-only analysis. The skill produces reports and JIRA-ready gap specifications but never changes code, configuration, or documentation.

## When to Use This Skill

Activate this skill when the user:
- Asks to "audit this repo against standards"
- Asks "does this repo follow hyperfleet standards?"
- Asks to "check standards compliance"
- Asks "what standards gaps does this repo have?"
- Asks to "run a standards check"
- Asks about "architecture compliance"
- Asks "is this repo ready for production?"
- Asks to "validate against hyperfleet standards"

## Dynamic Standards Discovery

Standards are **dynamically fetched** from the architecture repository - never hardcoded. This ensures the skill stays current as standards evolve.

### Standards Source Priority

1. **GitHub Raw Content (Primary)** - Always get latest version
   ```
   https://raw.githubusercontent.com/openshift-hyperfleet/architecture/main/hyperfleet/standards/
   ```

2. **Local Architecture Repo (Fallback)** - Use when offline or GitHub unavailable
   ```
   /home/croche/Projects/hyperfleet/architecture/hyperfleet/standards/
   ```

### Step 1: List Available Standards

**GitHub (preferred):**
```bash
# Use GitHub API to list files in the standards directory
gh api repos/openshift-hyperfleet/architecture/contents/hyperfleet/standards --jq '.[] | select(.name | endswith(".md")) | .name' 2>/dev/null
```

**Local fallback:**
```bash
ls /home/croche/Projects/hyperfleet/architecture/hyperfleet/standards/*.md 2>/dev/null | xargs -n1 basename
```

### Step 2: Fetch Standards Index (if exists)

Check for `standards-index.yaml` which provides pre-defined metadata:

**GitHub:**
```bash
curl -s https://raw.githubusercontent.com/openshift-hyperfleet/architecture/main/hyperfleet/standards/standards-index.yaml 2>/dev/null
```

**Local:**
```bash
cat /home/croche/Projects/hyperfleet/architecture/hyperfleet/standards/standards-index.yaml 2>/dev/null
```

If the index exists, it contains:
```yaml
standards:
  - file: commit-standard.md
    name: Commit Message Standard
    severity: minor
    applies_to: [all]
  - file: linting.md
    name: Linting Standard
    severity: major
    applies_to: [go-repos]
    companion_files: [golangci.yml]
```

### Step 3: Fetch Each Standard Document

For each `.md` file discovered:

**GitHub:**
```bash
curl -s https://raw.githubusercontent.com/openshift-hyperfleet/architecture/main/hyperfleet/standards/FILENAME.md
```

**Local:**
```bash
cat /home/croche/Projects/hyperfleet/architecture/hyperfleet/standards/FILENAME.md
```

### Step 4: Extract Metadata from Document Content

When `standards-index.yaml` is not available, parse metadata from each document:

**Look for explicit metadata sections:**
```markdown
## Applicability
- API, Sentinel, Adapters

## Severity
Critical - affects reliability
```

**Infer from content keywords:**
| Keyword Pattern | Inferred Applicability |
|-----------------|------------------------|
| `SIGTERM`, `SIGINT`, `graceful shutdown` | Services (API, Sentinel, Adapters) |
| `Makefile`, `make target` | All repositories |
| `golangci`, `.golangci.yml` | Go repositories |
| `RFC 9457`, `problem+json`, `error response` | API services |
| `/healthz`, `/readyz`, `/metrics` | Services |
| `Prometheus`, `hyperfleet_` metrics | Services |
| `LOG_LEVEL`, `structured logging` | Services |
| `.gitignore`, `generated code` | Repos with code generation |
| `commit message`, `git log` | All repositories |

**Infer severity from impact language:**
| Severity | Indicators |
|----------|------------|
| Critical | "MUST", "required for production", "affects reliability", "Kubernetes integration" |
| Major | "SHOULD", "affects code quality", "affects observability" |
| Minor | "RECOMMENDED", "style", "conventions" |

### Step 5: Build Audit Checklist

For each standard document, extract checkable requirements:

1. **File Existence Checks** - Look for mentioned files:
   - `.golangci.yml`
   - `Makefile`
   - `.gitignore`

2. **File Content Checks** - Parse expected configurations:
   - Required Makefile targets: `help`, `build`, `test`, `lint`, `clean`
   - Required linters in `.golangci.yml`
   - Required gitignore patterns

3. **Code Pattern Checks** - Grep patterns for code inspection:
   - Signal handling: `syscall.SIGTERM`
   - Health endpoints: `/healthz`, `/readyz`
   - Metrics: `hyperfleet_`
   - Logging fields: `trace_id`, `component`

4. **Commit Message Checks** - Git log validation:
   - Format: `HYPERFLEET-XXX - type: subject` or `type: subject`
   - Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

## Repository Type Detection

Before running applicable checks, detect the repository type.

### Detection Commands

```bash
# Check for API indicators
ls pkg/api/ 2>/dev/null && echo "HAS_API_PKG"
ls openapi.yaml 2>/dev/null || ls openapi/openapi.yaml 2>/dev/null && echo "HAS_OPENAPI"
grep -l "database" cmd/*.go 2>/dev/null && echo "HAS_DATABASE"

# Check for Sentinel indicators
basename $(pwd) | grep -i sentinel && echo "IS_SENTINEL"
grep -r "polling\|reconcile" --include="*.go" -l 2>/dev/null | head -1 && echo "HAS_RECONCILE"

# Check for Adapter indicators
basename $(pwd) | grep "^adapter-" && echo "IS_ADAPTER"
grep -r "cloudevents\|pubsub" --include="*.go" -l 2>/dev/null | head -1 && echo "HAS_CLOUDEVENTS"

# Check for Infrastructure
ls charts/Chart.yaml 2>/dev/null || ls Chart.yaml 2>/dev/null && echo "HAS_HELM"
ls *.tf 2>/dev/null && echo "HAS_TERRAFORM"

# Check for Go code
ls cmd/*.go 2>/dev/null || ls pkg/**/*.go 2>/dev/null && echo "IS_GO_REPO"
```

### Repository Type Matrix

| Indicators | Repository Type |
|------------|-----------------|
| HAS_API_PKG + HAS_OPENAPI + HAS_DATABASE | API Service |
| IS_SENTINEL or HAS_RECONCILE | Sentinel |
| IS_ADAPTER or HAS_CLOUDEVENTS (without API) | Adapter |
| HAS_HELM or HAS_TERRAFORM (without Go) | Infrastructure |
| IS_GO_REPO (without service patterns) | Tooling |

### Applicability Rules

| Standard Category | API | Sentinel | Adapter | Infrastructure | Tooling |
|-------------------|-----|----------|---------|----------------|---------|
| Commit Messages | Yes | Yes | Yes | Yes | Yes |
| Linting | Yes | Yes | Yes | No | Yes |
| Makefile Conventions | Yes | Yes | Yes | Yes | Yes |
| Error Model | Yes | Partial | Partial | No | No |
| Graceful Shutdown | Yes | Yes | Yes | No | No |
| Health Endpoints | Yes | Yes | Yes | No | No |
| Logging Specification | Yes | Yes | Yes | No | Optional |
| Metrics | Yes | Yes | Yes | No | No |
| Generated Code Policy | If applicable | If applicable | If applicable | No | No |

## Audit Execution

### For Each Applicable Standard

1. **Read the standard document** (from GitHub or local)
2. **Extract checkable requirements** from the content
3. **Execute checks** against the local repository
4. **Record results** as PASS, PARTIAL, or FAIL
5. **Document specific gaps** with file locations and remediation

### Common Check Patterns

**File Existence:**
```bash
test -f FILENAME && echo "PASS" || echo "FAIL"
```

**Makefile Target Existence:**
```bash
grep -E '^TARGET_NAME:' Makefile 2>/dev/null && echo "PASS" || echo "FAIL"
```

**Configuration Content:**
```bash
grep -q "EXPECTED_CONTENT" FILENAME && echo "PASS" || echo "FAIL"
```

**Code Pattern:**
```bash
grep -r "PATTERN" --include="*.go" -l 2>/dev/null | head -1 && echo "PASS" || echo "FAIL"
```

**Git Commit Messages (last 20):**
```bash
git log --oneline -20 --format="%s"
```

Validate each against regex:
```
^(HYPERFLEET-\d+ - )?(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert): .+$
```

## Output Format

### Audit Report Structure

```markdown
# HyperFleet Standards Audit Report

**Repository:** [repo name]
**Path:** [full path]
**Repository Type:** [API/Sentinel/Adapter/Infrastructure/Tooling]
**Audit Date:** [ISO timestamp]
**Standards Source:** [GitHub/Local]

---

## Summary

| Standard | Status | Severity | Gaps |
|----------|--------|----------|------|
| [Standard Name] | PASS/PARTIAL/FAIL | Critical/Major/Minor | 0/N |

**Overall Compliance:** X/Y standards passing (Z%)

---

## Detailed Findings

### [Standard Name]

**Status:** PASS/PARTIAL/FAIL
**Severity:** Critical/Major/Minor
**Applicable:** Yes/No (reason if No)

#### Checks Performed
- [x] Check 1 description
- [ ] Check 2 description (FAILED)
- [x] Check 3 description

#### Gaps Found

##### GAP-XXX-001: [Brief Description]
- **Location:** [file path:line number or N/A]
- **Expected:** [what the standard requires]
- **Found:** [what was actually found]
- **Severity:** Critical/Major/Minor

---

## JIRA-Ready Gap Specifications

[For each gap, provide a complete ticket specification]
```

### JIRA Gap Specification Format

For integration with the `jira-ticket-creator` skill, format each gap as:

```markdown
### GAP-[STANDARD]-[NUMBER]: [Brief Title]

**Suggested Ticket:**
- **Title:** [Concise title < 100 chars]
- **Type:** Task
- **Priority:** [Major/Normal/Minor based on severity]
- **Story Points:** [1/3/5 based on complexity]
- **Activity Type:** Quality / Stability / Reliability

**Description (JIRA Wiki Markup):**

h3. What

[Clear description of what needs to be done - 2-4 sentences]

h3. Why

* Required by HyperFleet [Standard Name] standard
* [Additional business justification]
* Reference: architecture/hyperfleet/standards/[filename].md

h3. Acceptance Criteria:

* [Specific, testable criterion 1]
* [Specific, testable criterion 2]
* [Specific, testable criterion 3]

h3. Technical Notes:

* [Implementation guidance]
* [Related files or patterns]
```

### Story Points Guidance

| Complexity | Points | Examples |
|------------|--------|----------|
| Config change | 1 | Add .golangci.yml, update .gitignore, add Makefile target |
| Code changes | 3 | Add health endpoint, implement signal handler |
| Refactoring | 5 | Restructure logging, implement error model |

### Priority Mapping

| Severity | Priority |
|----------|----------|
| Critical | Major |
| Major | Normal |
| Minor | Minor |

## Integration with jira-ticket-creator

After generating the audit report, users can create JIRA tickets for gaps:

**Workflow:**
1. User: "audit this repo against standards"
2. Skill: Generates report with JIRA-ready gap specifications
3. User: "create a ticket for GAP-LNT-001"
4. jira-ticket-creator skill: Uses the pre-formatted specification

**Bulk Ticket Creation:**
User can also request: "create tickets for all critical gaps"

The gap specifications are pre-formatted in JIRA wiki markup (not Markdown) to work directly with jira-ticket-creator.

## Example Audit Session

**User:** "audit this repo against standards"

**Skill Response:**

```markdown
# HyperFleet Standards Audit Report

**Repository:** hyperfleet-api
**Path:** /home/croche/Projects/hyperfleet/hyperfleet-api
**Repository Type:** API Service
**Audit Date:** 2026-01-05T12:30:00Z
**Standards Source:** GitHub (latest)

---

## Summary

| Standard | Status | Severity | Gaps |
|----------|--------|----------|------|
| Commit Message Standard | PARTIAL | Minor | 3 |
| Linting Standard | PARTIAL | Major | 1 |
| Makefile Conventions | PASS | Major | 0 |
| Error Model | PASS | Critical | 0 |
| Graceful Shutdown | PASS | Critical | 0 |
| Health Endpoints | PASS | Critical | 0 |
| Logging Specification | PARTIAL | Major | 1 |
| Metrics Standard | PASS | Major | 0 |
| Generated Code Policy | PASS | Major | 0 |

**Overall Compliance:** 6/9 standards fully passing (67%)

---

## Detailed Findings

### Linting Standard

**Status:** PARTIAL
**Severity:** Major
**Applicable:** Yes

#### Checks Performed
- [x] .golangci.yml exists
- [ ] All required linters enabled (MISSING: goimports, gocritic, exhaustive)
- [x] Generated code excluded
- [x] make lint target present

#### Gaps Found

##### GAP-LNT-001: Missing required linters in .golangci.yml
- **Location:** .golangci.yml
- **Expected:** 16 linters enabled per standard
- **Found:** 9 linters enabled
- **Missing:** goimports, gocritic, exhaustive, gofmt, lll, revive, goconst
- **Severity:** Major

---

## JIRA-Ready Gap Specifications

### GAP-LNT-001: Add missing linters to .golangci.yml

**Suggested Ticket:**
- **Title:** Add missing linters to hyperfleet-api golangci config
- **Type:** Task
- **Priority:** Normal
- **Story Points:** 1
- **Activity Type:** Quality / Stability / Reliability

**Description (JIRA Wiki Markup):**

h3. What

Update {{.golangci.yml}} to enable all 16 required linters per HyperFleet linting standard. Currently missing 7 linters: goimports, gocritic, exhaustive, gofmt, lll, revive, goconst.

h3. Why

* Required by HyperFleet Linting Standard
* Ensures consistent code quality across all HyperFleet repositories
* Reference: architecture/hyperfleet/standards/linting.md

h3. Acceptance Criteria:

* All 16 linters enabled in {{.golangci.yml}}
* {{make lint}} passes with no new violations (or violations tracked separately)
* Configuration matches reference at {{architecture/hyperfleet/standards/golangci.yml}}

h3. Technical Notes:

* Copy settings from reference config in architecture repo
* May need to add {{exclude-rules}} for existing violations to fix incrementally
* Consider creating separate ticket for fixing existing lint violations

---

## Recommendations

**Quick Wins (1 point each):**
1. GAP-LNT-001: Add missing linters - copy from reference config

**Priority Items:**
1. Fix linting configuration before merging new PRs

Would you like me to create JIRA tickets for any of these gaps?
```

## Error Handling

If the skill cannot complete an audit:

1. **GitHub unavailable:** Fall back to local repository
2. **Local repo missing:** Report which standards could not be fetched
3. **Partial checks:** Report which checks could not be performed
4. **Unknown repo type:** Ask user to specify or default to "Tooling"

Always provide partial results where possible and suggest manual verification steps for incomplete checks.

## Notes

- This skill is **READ-ONLY** - it never modifies files
- Standards are **dynamically fetched** - skill stays current as standards evolve
- Gap specifications use **JIRA wiki markup** (not Markdown) for jira-ticket-creator compatibility
- Severity ratings: Critical > Major > Minor
- Repository type affects which standards apply
- All checks include file locations and specific remediation guidance
