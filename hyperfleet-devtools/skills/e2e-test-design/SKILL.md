---
name: hyperfleet-e2e-test-design
description: Use when designing E2E test cases for HyperFleet epics or features - requires a Jira epic ticket ID to understand acceptance criteria, reads existing test cases from the repo, and produces structured test case documents following the project template
argument-hint: <HYPERFLEET-XXX>
---

# HyperFleet E2E Test Case Design

**You are a quality engineer expert.** You think in terms of test coverage, risk analysis, failure modes, and regression prevention. You design test cases that are precise, verifiable, and traceable to acceptance criteria. You use systematic test design techniques — state transition testing, equivalence partitioning, boundary value analysis, and decision tables — to derive test cases methodically rather than relying on intuition.

## Overview

Design black-box E2E test cases for HyperFleet cluster lifecycle management features. Test cases validate **customer-facing workflows** across components (API, Sentinel, Broker, Adapters, K8s resources) — NOT internal component behavior or final cloud resources.

## When to Use

- User provides a Jira epic ticket ID and asks to design test cases
- User asks to add test coverage for a HyperFleet feature
- User wants to review or extend existing test case designs

## Prerequisites

Verify required CLI tools are available before proceeding:

- **jira CLI**: `!which jira` — required for epic/ticket lookup. If unavailable, ask the user for Jira ticket details manually.
- **gh CLI**: `!which gh` — required for fetching existing test cases from GitHub. If unavailable, ask the user to provide test case files.

## Required Inputs

Before designing test cases, you MUST gather three sources of context.

### 1. Jira Epic Details

```bash
jira issue view HYPERFLEET-XX
jira epic list HYPERFLEET-XX --plain --columns key,summary,status,type
```

### 2. Existing Test Cases (MANDATORY — read BEFORE designing)

```bash
gh api repos/openshift-hyperfleet/hyperfleet-e2e/contents/test-design/testcases --jq '.[].name'
# Then read FULL content of every relevant file:
gh api repos/openshift-hyperfleet/hyperfleet-e2e/contents/test-design/testcases/{filename} \
  --jq '.content' | base64 -d
```

### 3. Architecture Context

```text
WebFetch: https://raw.githubusercontent.com/openshift-hyperfleet/architecture/refs/heads/main/hyperfleet/architecture/architecture-summary.md
```

> **Note**: This URL must be kept in sync if the architecture repo restructures. If the fetch returns empty/404, fall back to asking the user for the architecture summary.

## Design Process

1. Read Jira epic + child issues
2. Read ALL existing test cases (FULL content)
3. Read architecture summary
4. Build traceability matrix (explicit + implicit ACs → coverage gaps)
5. Risk-assess each gap (likelihood × blast radius)
6. Apply test design techniques to gaps (depth by risk)
7. Draft candidate test cases (Tier0 → Tier1 → Tier2)
8. **CANDIDATE PRE-FILTER** (scope, component boundary, implicit coverage)
9. **OVERLAP ANALYSIS** (compare surviving candidates against existing)
10. Remove/merge overlapping cases
11. **CROSS-EPIC REGRESSION CHECK**
12. **COVERAGE VERIFICATION** (update matrix with new candidates)
13. Generate Jira gap specs for uncovered ACs
14. Present coverage matrix + overlap + regression tables to user
15. Write final test case document (after user confirmation)

## Traceability Matrix (MANDATORY)

Map every acceptance criterion from the Jira epic to test coverage BEFORE designing:

```markdown
| # | Acceptance Criterion | Existing Test(s) | Coverage | Gap Description |
|---|---|---|---|---|
| AC1 | Cluster reaches Ready state | cluster.md: Test 1 | Full | — |
| AC2 | Failed adapter blocks Ready | — | NONE | No negative test for adapter failure impact on cluster status |
```

**Rules:**
- Every AC must appear in the matrix
- "Full" = no new test needed. "Partial" = design for gap only. "NONE" = design new tests
- Only design new test cases for "Partial" and "NONE" gaps
- **Cross-file implicit coverage**: An AC can be "Full" if multiple test files collectively prove it. Example: "operational parity between transport modes" is proven if both `cluster.md` (k8s transport) and `adapter-with-maestro-transport.md` (Maestro transport) tests pass and produce equivalent end states. Don't require a single test to prove what separate test suites already demonstrate together
- **Development-time guarantees vs runtime behavior**: ACs like "zero code changes required" or "no breaking changes" are design constraints, not runtime behaviors. Mark these as N/A for E2E — they're verified by the fact that existing tests continue to pass after the feature ships
- **Transport/config-agnostic tests**: Tests that validate "all deployed adapters" (e.g., concurrent processing) are transport-agnostic. If a Maestro adapter is deployed in the test environment, these tests already exercise it. Don't create transport-specific duplicates

### Implicit AC Extraction (MANDATORY)

Epics often omit requirements that are assumed but must be tested. After mapping explicit ACs, scan for implicit ones:

| Category | Questions to Ask | Example Implicit AC |
|---|---|---|
| **Idempotency** | What happens if the same request is sent twice? | Duplicate cluster creation returns existing resource, not error |
| **Backward compatibility** | Does this break existing resources or API contracts? | Existing clusters continue to work after feature rollout |
| **Data integrity** | Can data be corrupted or lost during this workflow? | Cluster metadata preserved across adapter restarts |
| **Security boundaries** | Can one tenant's action affect another? | Cluster creation scoped to requesting tenant only |
| **Ordering guarantees** | Does the system depend on event ordering? | Out-of-order adapter status reports resolve to correct final state |
| **Resource cleanup** | What happens to orphaned resources on failure? | Failed cluster creation doesn't leave orphaned K8s resources |

**Rules:**
- Add implicit ACs to the traceability matrix with prefix `IAC` (e.g., IAC1, IAC2)
- Mark their source as "Implicit — [category]" in the Gap Description
- Implicit ACs default to Tier1 unless they represent a critical data integrity risk (then Tier0)
- Present implicit ACs separately to the user for confirmation — they may not all be in scope

## Candidate Pre-Filter (MANDATORY)

Before overlap analysis, apply these filters to each candidate. Any candidate that fails a filter is DROPPED — do not carry it forward.

```markdown
| Candidate | Filter Applied | Verdict | Reason |
|---|---|---|---|
| Candidate A | Component boundary | DROP | TLS cert validation is single-component (adapter→Maestro client), not cross-component E2E |
| Candidate B | Implicit coverage | DROP | Parity proven by cluster.md (k8s) + maestro.md (Maestro) both passing — no single test needed |
| Candidate C | Transport-agnostic | DROP | concurrent-processing.md validates all deployed adapters regardless of transport mode |
```

### Filter 1: E2E Scope Boundary

Re-check each candidate against the scope boundary table. Ask: **"Does this test validate a customer-facing workflow across multiple components?"**

DROP if the failure/behavior happens entirely within one component:
- Client configuration errors (TLS, auth, connection strings) → integration test
- Internal retry/backoff behavior → unit test
- Input validation at a single API boundary → unit/integration test
- Internal state management within one service → unit test

### Filter 2: Implicit Cross-File Coverage

Check if the AC is already proven by **multiple existing test files collectively passing**:
- If test file A proves "k8s transport works" and test file B proves "Maestro transport works," then "operational parity" is implicitly proven — no side-by-side comparison test needed
- If a test validates "all deployed adapters," it covers any adapter type deployed in the environment (transport-agnostic)

### Filter 3: Third-Party System Internals

DROP candidates that test internal behavior of external/third-party systems:
- Maestro's resource-bundle lifecycle management → Maestro's scope
- Broker's message deduplication guarantees → Broker's scope
- K8s garbage collection behavior → K8s scope
- Only test what HyperFleet components observe via API or K8s resource status

### Filter 4: Design-Time vs Runtime Guarantees

DROP candidates that test development constraints rather than runtime behavior:
- "Zero code changes required" → verified by same binary running with both configs (CI/build scope)
- "No breaking changes to existing implementations" → verified by existing tests continuing to pass (regression suite)
- "Backward compatible API" → verified by existing API tests passing after feature merge

**Rules:**
- Present the pre-filter table to the user showing which candidates survived and which were dropped
- If ALL candidates are dropped, this is a valid outcome — it means existing coverage is sufficient
- Dropped candidates may still generate Jira gap specs if they belong in other test scopes (integration, perf, Helm)

## Overlap Analysis (MANDATORY)

Compare each candidate against existing tests BEFORE writing:

```markdown
| New Candidate | Closest Existing Test | Overlap % | Verdict | Reason |
|---|---|---|---|---|
| Candidate A | Existing Test X | 20% | KEEP | Only Step 1 overlaps (cluster creation boilerplate) |
| Candidate B | Existing Test Y | 90% | DROP | Steps 1-5 identical, only adds one assertion |
```

- **>70% overlap** → DROP. **40-70%** → MERGE into existing test. **<40%** → KEEP
- Cluster creation + cleanup are boilerplate — don't count as meaningful overlap
- Compare ACTIONS and EXPECTED RESULTS, not just titles

## Cross-Epic Regression Check

Before finalizing candidates, assess whether new tests interact with or could be affected by existing tests from other epics:

1. **Shared resource conflicts**: Does the new feature change behavior of resources tested by existing tests? (e.g., new adapter condition changes when cluster reaches Ready)
2. **Precondition changes**: Does the new feature add or change preconditions that existing tests rely on? (e.g., new required field on cluster creation)
3. **State model changes**: Does the feature add new states or transitions that invalidate existing state transition tests?

```markdown
| Existing Test File | Potential Impact | Action Needed |
|---|---|---|
| cluster.md: Test 1 | New adapter condition added to Ready aggregation | Update expected conditions list |
| nodepool.md: Test 3 | No impact — nodepool lifecycle unchanged | None |
```

**Rules:**
- Only flag genuine functional interactions, not superficial ones (e.g., shared API endpoint is not a conflict unless response schema changes)
- If existing tests need updates, note them but **do not modify existing test files** in this design session — create a follow-up item
- Present impact table to the user alongside the coverage matrix

## Coverage Verification (MANDATORY)

After overlap analysis, update the traceability matrix to show which new candidates fill each gap. This closes the loop and confirms all ACs are addressed:

```markdown
| # | Acceptance Criterion | Existing Test(s) | Coverage Before | New Candidate | Coverage After |
|---|---|---|---|---|---|
| AC1 | Cluster reaches Ready state | cluster.md: Test 1 | Full | — | Full |
| AC2 | Failed adapter blocks Ready | — | NONE | Candidate A | Full |
| AC3 | Concurrent creation no conflicts | concurrent.md: Test 2 | Partial | Candidate C | Full |
| AC4 | Recovery after crash | — | NONE | — | NONE (deferred) |
```

**Rules:**
- Every AC from the original traceability matrix must appear
- "Coverage After" must be justified: Full = existing + new candidates cover it, Partial = gap narrowed but not closed, NONE = no coverage (must include reason: deferred, out of E2E scope, etc.)
- Any AC still at NONE or Partial after this step must be explicitly acknowledged with a reason (e.g., "deferred to post-MVP", "belongs in integration tests", "needs team input on expected behavior")
- **Present this table to the user and get confirmation before writing the file**

### Jira-Ready Gap Specs for Uncovered ACs

For any AC still at NONE or Partial after coverage verification, generate a Jira ticket specification so the gap can be tracked. Format in **Jira wiki markup** for direct use with the `hyperfleet-jira-issue` skill.

```markdown
### GAP-E2E-001: [AC summary]

**Suggested Ticket:**
- **Title:** E2E: [concise description of missing coverage] (< 100 chars)
- **Type:** Story
- **Priority:** [Major if Tier0 gap, Normal if Tier1, Minor if Tier2]
- **Story Points:** [3 for new test case, 5 for multi-scenario coverage]
- **Component:** CICD

**Description (Jira Wiki Markup):**

h3. What

Design and implement E2E test case for: [AC description]. Currently has [NONE/Partial] coverage.

h3. Why

* Acceptance criterion from epic [HYPERFLEET-XXX|https://issues.redhat.com/browse/HYPERFLEET-XXX]
* [Reason coverage is missing: out of scope for current design, needs team input, deferred to post-MVP, etc.]

h3. Acceptance Criteria

* Test case document written following E2E test case template
* Test covers: [specific scenarios]
* [If Partial] Extends existing test: [existing test reference]

h3. Technical Notes

* Related existing tests: [list closest existing tests for reference]
* Design technique: [recommended technique for this gap]
* Suggested tier: [Tier0/Tier1/Tier2]
```

**Rules:**
- Only generate gap specs for NONE and Partial ACs — never for Full
- Link back to the source epic in the description
- Include the reason from the coverage verification table
- Priority maps from tier: Tier0 gap → Major, Tier1 → Normal, Tier2 → Minor
- Offer to create tickets via `hyperfleet-jira-issue` skill after user reviews the gap specs

## E2E Scope Boundary

**E2E tests validate customer-facing workflows.** Before adding a test, ask: "Would a customer do this?"

| Belongs in E2E | Belongs in Unit/Integration |
|---|---|
| Full resource lifecycle (create → Ready) | API input validation (invalid JSON, malformed payloads) |
| Adapter failure reflected in cluster status | Individual field validation edge cases |
| Concurrent resource creation without conflicts | Internal component behavior (adapter job internals) |
| Recovery after component crash | Message broker delivery guarantees (event acking, redelivery) |
| Cross-component workflow validation | Single-component error handling, API status contract validation |

**Verification rules:**
- Verify via **API endpoints** (resource status, conditions) and **K8s resource existence** — never internal component mechanics
- API endpoint is primary E2E verification; kubectl pod checks are secondary/manual
- Never call internal-only API endpoints (e.g., POST `/clusters/{id}/statuses`)
- Prefer resource-level tests over component-level tests (e.g., "Cluster reflects adapter failure" > "Adapter error handling in isolation")
- If API integration tests can cover it, don't duplicate in E2E

## Architecture Reference

| Component | Role | E2E Test Boundary |
|-----------|------|-------------------|
| **HyperFleet API** | Simple CRUD, no business logic | HTTP requests/responses, status codes |
| **Database** | Persistent storage | Validated indirectly via API |
| **Sentinel** | Polls API, publishes events | Observed via adapter execution timing |
| **Broker** | Fan-out events to adapters | Validated indirectly via adapters |
| **Adapters** | Consume events, create K8s resources, report status | Condition transitions (Applied/Available/Health) |
| **K8s Resources** | Created by adapters | Resource existence, metadata, status |

### Status Model

- **Resource conditions**: `Ready`, `Available` (True/False)
- **Adapter conditions**: `Applied`, `Available`, `Health` (True/False/Unknown)
- **Aggregation**: All adapters Available=True → Cluster Ready

### Data Flow

```text
User → API (CRUD) → DB
Sentinel polls API → publishes events → Broker → Adapters
Adapters → evaluate preconditions → create K8s resources → report status to API
```

## Tier Definitions

| Tier | Purpose | Examples |
|------|---------|---------|
| **Tier0** | Critical happy-path workflows, blocks release | Cluster creation lifecycle, nodepool lifecycle, K8s resource metadata, adapter dependencies |
| **Tier1** | Important negative cases customers might encounter | Adapter failure in cluster status, crash recovery, concurrent creation conflicts |
| **Tier2** | Edge cases unlikely in production | Timeout detection, generation-based skip, name-length boundary |

### Risk-Based Prioritization

Tier alone is not enough. Assess **risk** for each coverage gap to determine test depth (number of scenarios per AC):

```markdown
| AC | Likelihood | Blast Radius | Risk Score | Test Depth |
|---|---|---|---|---|
| AC2: Adapter failure blocks Ready | Medium | High (cluster stuck) | HIGH | 3 scenarios (failure, crash, timeout) |
| AC5: Name-length boundary | Low | Low (single request) | LOW | 1 scenario |
```

- **Likelihood**: How likely is this to happen in production? (High/Medium/Low)
- **Blast Radius**: If it fails, what's the impact? Single resource, all resources, data loss? (High/Medium/Low)
- **Risk Score**: Likelihood × Blast Radius matrix:

| | Low Blast | Medium Blast | High Blast |
|---|---|---|---|
| **High Likelihood** | MEDIUM | HIGH | CRITICAL |
| **Medium Likelihood** | LOW | MEDIUM | HIGH |
| **Low Likelihood** | LOW | LOW | MEDIUM |

- **Test Depth**: HIGH/CRITICAL → 2-4 scenarios covering variations. MEDIUM → 1-2 scenarios. LOW → 1 scenario
- Apply risk assessment AFTER the traceability matrix, BEFORE designing candidates

### Tier Design Guidelines

**Tier0 — Full Lifecycle (positive tests)**:
- MUST cover: create → initial state (False) → adapter execution → transitions → final state (Ready=True, Available=True)
- MUST verify adapter conditions (Applied, Available, Health) and metadata (created_time, last_report_time, observed_generation, reason, message, last_transition_time)
- MUST validate dependency enforcement if adapters have dependencies
- Derive from: State Transition Testing + Decision Tables

**Tier1 — Negative Validation (important failure scenarios)**:
- Test failure handling visible to customers, error reporting, recovery
- Deploy dedicated test adapters for failure scenarios (see Test Design Rules)
- Derive from: Failure Mode Analysis + State Transition (invalid transitions, regressions)

**Tier2 — Edge Cases (low-risk regression)**:
- Idempotency, timeout handling, configuration boundaries
- API input validation belongs here at most (not Tier0/Tier1) — it's more naturally unit/integration scope
- Derive from: Boundary Value Analysis + Decision Tables (rare combinations)

## Systematic Test Design Techniques

**Apply at least one technique per coverage gap.** Select based on what you're testing:

| What you're testing | Primary technique | Secondary |
|---|---|---|
| Resource lifecycle (create/update/delete) | State Transition | — |
| API input validation | Equivalence Partitioning | Boundary Value Analysis |
| Adapter preconditions / dependency chains | Decision Table | State Transition |
| Component failure handling | Failure Mode Analysis | State Transition (recovery) |

### 1. State Transition Testing (Primary for HyperFleet)

Map states and transitions, then derive test cases covering: all valid transitions (Tier0), invalid transitions (Tier1), stuck-in-state (Tier2), state regression True→False (Tier1).

**HyperFleet state models:**
```text
Cluster:    Pending → Provisioning → Ready / Failed. Ready → Deleting → Deleted
Adapter:    Unknown → False → True (normal). True → False (regression). Unknown stuck (timeout)
Resource:   Ready=False → Ready=True (all adapters Available)
```

### 2. Equivalence Partitioning

Divide inputs into valid/invalid classes. Test one value per class. Example: valid platform ("gcp"), invalid platform ("unsupported"), empty, missing field.

### 3. Boundary Value Analysis

Test at edges of valid ranges: min, min+1, typical, max-1, max, below min, above max.

### 4. Decision Table Testing

For multi-condition behavior (e.g., dependency Available=True + precondition met → combinations determine action).

### 5. Failure Mode Analysis

For each component in the test boundary, enumerate: unavailable, invalid data, slow/timeout, partial failure, recovery after restore.

## Test Design Rules

### Independence
- Each test creates its own resources and cleans up everything, regardless of pass/fail
- No ordering dependency or shared state between tests

### Dedicated Test Adapters for Failure Testing
- **Never modify existing adapter configuration** — risks dirty environment if cleanup fails
- Deploy dedicated adapters with pre-configured behavior: `failure-adapter` (SIMULATE_RESULT=failure), `crash-adapter` (SIMULATE_RESULT=crash), `precondition-error-adapter` (invalid URL)
- Each has its own Helm release; cleanup includes Pub/Sub subscription deletion if applicable

### Resource Naming
- Use `{{.Random}}` template — never hardcoded names like `test-cluster-1`
- Label resources with test run ID for traceability
- Reference testdata payload files (e.g., `@testdata/payloads/clusters/cluster-request.json`) rather than inline JSON

### Test Data Strategy

For each test case, specify which test data variants are needed — not just "valid input":

| Data Category | What to Define | Example |
|---|---|---|
| **Minimal valid** | Fewest fields that produce a valid request | Cluster with only required fields (name, platform) |
| **Maximal valid** | All optional fields populated | Cluster with labels, annotations, all adapter configs |
| **Boundary payloads** | Values at limits of valid ranges | Name at max length, maximum number of nodepools |
| **Invalid variants** | One invalid field per variant (for negative tests) | Missing required field, invalid platform value |

**Rules:**
- Reference payload files in `@testdata/payloads/` — never inline large JSON in test steps
- Name payload files descriptively: `cluster-minimal.json`, `cluster-max-nodepools.json`, not `test1.json`
- Document which fields vary per test and why — don't force the reader to diff JSON files
- For parameterized tests (same steps, different data), use a data table instead of duplicating test cases

### Writing Test Steps
- Setup (adapter deployment, test data) belongs in **Preconditions** — unless deploy/uninstall IS the test action (then keep both as test steps)
- Don't generate deployment commands (helm, gcloud) unless they match actual project tooling — use descriptive sentences
- Use correct nested API paths: `/clusters/{cluster_id}/nodepools`, not `/nodepools`
- **Expected results must be deterministic** — never "returns X OR Y"
- **Expected results must be verifiable via an action** (API call, kubectl). Internal behavior ("Sentinel publishes event") belongs in Notes, not Expected Results
- Don't assume internal behavior — flag uncertain mechanisms for team discussion
- Reduce boilerplate — focus on what's unique per test case

### Timing and Polling Strategy

HyperFleet is async (API → Sentinel → Broker → Adapter). Test steps that wait for state transitions MUST define explicit polling strategies:

| Wait Type | Pattern | Example |
|---|---|---|
| **Condition transition** | Poll API with interval + timeout | Poll `GET /clusters/{id}` every 10s, timeout 5m, until `Ready=True` |
| **Resource creation** | Poll K8s API for existence | Poll `kubectl get` every 5s, timeout 2m, until resource exists |
| **Status propagation** | Poll with backoff | Poll adapter conditions every 10s, timeout 3m |

**Rules for test steps involving waits:**
- Always specify: **poll interval**, **timeout**, and **success condition**
- Never use fixed `sleep` — always poll for the expected state
- Timeout must be realistic for the operation (cluster Ready may take minutes; API response is seconds)
- Define what happens on timeout: the test FAILS with a clear message, not hangs
- In expected results, state the final condition to assert — not "wait for completion"

**Recommended defaults (override per test if needed):**
```text
API response:        no wait (synchronous)
Adapter condition:   poll 10s, timeout 3m
Cluster Ready:       poll 10s, timeout 5m
K8s resource:        poll 5s, timeout 2m
Cleanup verification: poll 5s, timeout 1m
```

### Flakiness Prevention

Flaky tests erode trust in the entire E2E suite. Design tests to resist flakiness from the start:

| Flakiness Source | Prevention Rule |
|---|---|
| **Timing assumptions** | Never assert "within X seconds" — poll for state, fail on timeout |
| **Shared state** | Each test creates and destroys its own resources. Never depend on pre-existing data |
| **Resource name collisions** | Use `{{.Random}}` names. Never assume a name is available |
| **Eventual consistency** | Poll for the desired state, don't assert immediately after a write |
| **Ordering sensitivity** | Don't assert on list ordering unless the API guarantees it. Use set-based assertions |
| **Timestamp precision** | Assert timestamps exist and are valid ISO 8601 — don't compare exact values |
| **Environment leakage** | Don't depend on specific adapter counts, node counts, or cluster configuration |
| **Cleanup failures** | Design cleanup to be idempotent — deleting an already-deleted resource should not fail the test |

**When writing test steps, flag flakiness risks:**
- If a step depends on timing, add a **Flakiness note** explaining the polling strategy
- If a step interacts with shared infrastructure (e.g., Pub/Sub topics), note the isolation mechanism
- If expected results could vary between runs, the test is not ready — redesign it

### Automation Feasibility Assessment

Each test case must have a justified **Automation** field. Use this decision guide:

| Automation Value | Criteria | Examples |
|---|---|---|
| **Automated** | Fully scriptable, deterministic, no human judgment needed | API lifecycle, condition transitions, K8s resource verification |
| **Semi-Automated** | Setup/execution automated, but verification needs human review | UI rendering, log output quality, performance perception |
| **Manual Only** | Requires physical access, human judgment, or unreproducible conditions | Hardware failure simulation, network partition on real infrastructure |
| **Not Automated (yet)** | Automatable but blocked by tooling/infrastructure gaps | Tests requiring features not yet in the E2E framework |

**Rules:**
- Default is **Automated** — only deviate with justification
- "Not Automated (yet)" must include what's blocking (e.g., "E2E framework lacks network partition simulation")
- **Manual Only** tests must justify why they can't be automated — don't use this as a catch-all
- If >30% of designed tests are Manual Only, reconsider whether the test design is too focused on non-automatable scenarios

### API Response Validation

**Success**: HTTP status code, required fields (id, name, status), correct types, valid timestamps

**Errors**: RFC 9457 Problem Details format consistently across ALL tests:
- `type` (URI), `title`, `status` (integer), `detail`
- Never leak internals. Same structure in every test case

**Conditions**: All expected conditions present with `type`, `status` (True/False/Unknown), `reason`, `message`, `lastTransitionTime`

## Test Case Template

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

## Red Flags and Common Mistakes

| Mistake | Fix |
|---------|-----|
| **Scope** | |
| Testing internal component behavior in E2E | E2E validates via API endpoints and K8s resources only |
| Including API input validation as Tier0/Tier1 | Tier2 at most — more naturally covered by unit/integration tests |
| Calling internal-only APIs (POST /statuses) | Only use customer-facing GET endpoints |
| Duplicating what API integration tests cover | If API integration covers it, skip it in E2E |
| Assuming internal behavior ("restart Sentinel triggers duplicates") | Flag uncertain mechanisms for team discussion |
| **Test design** | |
| Designing without reading existing tests (FULL content) | Read every step and expected result, not just titles |
| Skipping traceability matrix or overlap analysis | Both are MANDATORY before writing any test file |
| Writing test file before showing overlap table | Present to user FIRST, get confirmation |
| Deriving tests by intuition only | Apply at least one formal technique per gap |
| Only testing happy path states | Map full state diagram: regression (True→False), stuck states |
| **Test structure** | |
| Tests depend on each other's state | Each test: own setup, own cleanup, no shared state |
| Modifying existing adapter config for failure tests | Deploy dedicated test adapters with pre-configured behavior |
| Hardcoded resource names ("test-cluster-1") | Use `{{.Random}}` template, label with test run ID |
| Non-deterministic expected results ("returns X OR Y") | Assert single intended API contract behavior |
| Unverifiable expected results ("Sentinel publishes event") | Expected results must map to API call or kubectl output |
| Test data setup as test steps | Belongs in Preconditions (unless deploy IS the test action) |
| Creating individual files for 1-2 tests | Merge into relevant resource file |
| **Validation** | |
| Inconsistent error response format across tests | RFC 9457 Problem Details (type, title, status, detail) everywhere |
| Skipping condition metadata validation | Always validate reason, message, lastTransitionTime |
| Vague expected results | Specify exact condition values, HTTP status codes |
| Generating deployment commands that don't match actual process | Use descriptive sentences or reference actual project tooling |
| **Candidate filtering** | |
| Proposing test for single-component failure (TLS, auth, client config) | Apply scope boundary filter — single-component errors belong in integration tests |
| Creating test when multiple test files already prove the AC collectively | Check cross-file implicit coverage — don't require one test to prove what separate suites demonstrate |
| Duplicating transport-specific test when existing test is transport-agnostic | Tests validating "all deployed adapters" already cover any transport mode deployed |
| Testing internal behavior of third-party systems (Maestro cleanup, broker dedup) | Only test what HyperFleet observes via API or K8s resource status |
| Testing design-time constraints ("zero code changes", "no breaking changes") | These are verified by existing tests continuing to pass, not by new E2E tests |
| Carrying candidates through overlap analysis before checking scope | Apply pre-filter BEFORE overlap analysis to avoid wasted effort |
| **Risk & coverage** | |
| All tests at same depth regardless of risk | Assess likelihood × blast radius; HIGH risk gaps get 2-4 scenarios |
| Only testing explicit ACs from epic | Extract implicit ACs: idempotency, backward compat, data integrity, security boundaries |
| Ignoring impact on existing tests from other epics | Run cross-epic regression check; flag state model or precondition changes |
| **Reliability** | |
| Using `sleep` instead of polling for async operations | Poll with interval + timeout + success condition; never fixed sleep |
| Asserting on timing ("completes within 30s") | Assert on state, not time. Timeout is a failure boundary, not an assertion |
| Tests that pass alone but fail in parallel runs | Resource name collisions, shared state, ordering assumptions — use `{{.Random}}`, isolate fully |
| No flakiness notes on timing-sensitive steps | Flag polling strategy and isolation mechanism in test step notes |
| Marking tests Manual Only without justification | Default is Automated; Manual Only requires explicit rationale |
| No test data variants specified | Define minimal/maximal/boundary/invalid payloads per test |
