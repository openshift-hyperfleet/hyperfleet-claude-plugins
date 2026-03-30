# Test Case Template

```markdown
# Feature: [Feature Name]

## Table of Contents
1. [Test title 1](#anchor-1)

---

## Test Title: [Descriptive Title]

### Description
[1-2 sentences: what is validated, what the expected outcome proves]

**Design technique(s):** [State Transition / Equivalence Partitioning / Boundary Value / Decision Table / Failure Mode]

---

| **Field** | **Value** |
|-----------|-----------|
| **Pos/Neg** | [Positive/Negative] |
| **Priority** | [Tier0/Tier1/Tier2] |
| **Status** | [Draft/Deprecated] |
| **Automation** | [Automated/Semi-Automated/Manual Only/Not Automated (yet)] |
| **Version** | [MVP/post-MVP] |
| **Created** | [YYYY-MM-DD] |
| **Updated** | [YYYY-MM-DD] |

---

### Preconditions
1. Environment is prepared using hyperfleet-infra
2. HyperFleet API and Sentinel are deployed and running
3. [Feature-specific preconditions]

---

### Test Steps

#### Step 1: [Action Description]
**Action:**
- [What to do, with curl/kubectl examples]

**Expected Result:**
- [Specific, verifiable outcomes]

#### Step N: Cleanup resources
**Action:**
- Delete resources created during test

**Expected Result:**
- Resources deleted successfully

**Note:** Workaround cleanup. Once CLM supports DELETE, replace with API DELETE call.
```

## File Organization

```text
test-design/testcases/
├── cluster.md                          # Cluster lifecycle
├── nodepool.md                         # Nodepool lifecycle
├── adapter.md                          # Adapter framework tests
├── adapter-with-maestro-transport.md   # Maestro transport layer
├── concurrent-processing.md            # Concurrency tests
└── {feature-name}.md                   # New features
```

- Group related tests into a single file per feature/component
- **Don't create individual files for 1-2 test cases** — merge into the relevant resource file
- Use kebab-case filenames; include Table of Contents when file has multiple tests
