---
name: e2e-test-design
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
4. Build traceability matrix (explicit + implicit ACs -> coverage gaps)
5. Risk-assess each gap (likelihood x blast radius)
6. Apply test design techniques to gaps (depth by risk)
7. Draft candidate test cases (Tier0 -> Tier1 -> Tier2)
8. **CANDIDATE PRE-FILTER** (scope boundary, implicit cross-file coverage, third-party internals, design-time vs runtime)
9. **RED-FLAG REVIEW (candidates)** — validate candidates against [references/red-flags.md](references/red-flags.md): check scope, candidate filtering, and test design rules
10. **OVERLAP ANALYSIS** (compare surviving candidates against existing)
11. Remove/merge overlapping cases
12. **CROSS-EPIC REGRESSION CHECK**
13. **COVERAGE VERIFICATION** (update matrix with new candidates)
14. Generate Jira gap specs for uncovered ACs
15. Present coverage matrix + overlap + regression tables to user
16. **RED-FLAG REVIEW (final)** — review test structure, validation, and reliability rules against [references/red-flags.md](references/red-flags.md) before writing
17. Write final test case document (after user confirmation)

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

Apply all four mandatory filters to each candidate BEFORE overlap analysis: E2E scope boundary, implicit cross-file coverage, third-party system internals, and design-time vs runtime guarantees. Any candidate that fails a filter is DROPPED.

See [references/candidate-filters.md](references/candidate-filters.md) for the full filter definitions and rules.

## Overlap Analysis (MANDATORY)

Compare each candidate against existing tests BEFORE writing:

```markdown
| New Candidate | Closest Existing Test | Overlap % | Verdict | Reason |
|---|---|---|---|---|
| Candidate A | Existing Test X | 20% | KEEP | Only Step 1 overlaps (cluster creation boilerplate) |
| Candidate B | Existing Test Y | 90% | DROP | Steps 1-5 identical, only adds one assertion |
```

- **>70% overlap** -> DROP. **40-70%** -> MERGE into existing test. **<40%** -> KEEP
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

For any AC still at NONE or Partial, generate a gap specification following the template in [references/gap-specs.md](references/gap-specs.md).

## E2E Scope Boundary

**E2E tests validate customer-facing workflows.** Before adding a test, ask: "Would a customer do this?"

| Belongs in E2E | Belongs in Unit/Integration |
|---|---|
| Full resource lifecycle (create -> Ready) | API input validation (invalid JSON, malformed payloads) |
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
- **Aggregation**: All adapters Available=True -> Cluster Ready

### Data Flow

```text
User -> API (CRUD) -> DB
Sentinel polls API -> publishes events -> Broker -> Adapters
Adapters -> evaluate preconditions -> create K8s resources -> report status to API
```

## References

Detailed reference material is organized in the `references/` subdirectory:

- [references/tier-definitions.md](references/tier-definitions.md) — Tier0/Tier1/Tier2 definitions, risk-based prioritization matrix, and tier design guidelines
- [references/test-design-techniques.md](references/test-design-techniques.md) — Systematic test design techniques: state transition, equivalence partitioning, boundary value analysis, decision tables, and failure mode analysis
- [references/candidate-filters.md](references/candidate-filters.md) — Four mandatory pre-filters (E2E scope boundary, implicit cross-file coverage, third-party internals, design-time vs runtime)
- [references/test-design-rules.md](references/test-design-rules.md) — Test independence, dedicated test adapters, resource naming, test data strategy, writing test steps, timing/polling, flakiness prevention, automation feasibility, and API response validation
- [references/test-case-template.md](references/test-case-template.md) — Test case markdown template and file organization conventions
- [references/gap-specs.md](references/gap-specs.md) — Gap specification template for uncovered acceptance criteria
- [references/red-flags.md](references/red-flags.md) — Common mistakes and fixes organized by category (scope, test design, structure, validation, candidate filtering, risk/coverage, reliability)

## Notes

- You can ask to create tickets for any uncovered gaps — the `jira-ticket-creator` skill auto-activates when you request ticket creation
