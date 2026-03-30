# Test Design Rules

## Independence
- Each test creates its own resources and cleans up everything, regardless of pass/fail
- No ordering dependency or shared state between tests

## Dedicated Test Adapters for Failure Testing
- **Never modify existing adapter configuration** — risks dirty environment if cleanup fails
- Deploy dedicated adapters with pre-configured behavior: `failure-adapter` (SIMULATE_RESULT=failure), `crash-adapter` (SIMULATE_RESULT=crash), `precondition-error-adapter` (invalid URL)
- Each has its own Helm release; cleanup includes Pub/Sub subscription deletion if applicable

## Resource Naming
- Use `{{.Random}}` template — never hardcoded names like `test-cluster-1`
- Label resources with test run ID for traceability
- Reference testdata payload files (e.g., `@testdata/payloads/clusters/cluster-request.json`) rather than inline JSON

## Test Data Strategy

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

## Writing Test Steps
- Setup (adapter deployment, test data) belongs in **Preconditions** — unless deploy/uninstall IS the test action (then keep both as test steps)
- Don't generate deployment commands (helm, gcloud) unless they match actual project tooling — use descriptive sentences
- Use correct nested API paths: `/clusters/{cluster_id}/nodepools`, not `/nodepools`
- **Expected results must be deterministic** — never "returns X OR Y"
- **Expected results must be verifiable via an action** (API call, kubectl). Internal behavior ("Sentinel publishes event") belongs in Notes, not Expected Results
- Don't assume internal behavior — flag uncertain mechanisms for team discussion
- Reduce boilerplate — focus on what's unique per test case

## Timing and Polling Strategy

HyperFleet is async (API -> Sentinel -> Broker -> Adapter). Test steps that wait for state transitions MUST define explicit polling strategies:

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

## Flakiness Prevention

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

## Automation Feasibility Assessment

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

## API Response Validation

**Success**: HTTP status code, required fields (id, name, status), correct types, valid timestamps

**Errors**: RFC 9457 Problem Details format consistently across ALL tests:
- `type` (URI), `title`, `status` (integer), `detail`
- Never leak internals. Same structure in every test case

**Conditions**: All expected conditions present with `type`, `status` (True/False/Unknown), `reason`, `message`, `lastTransitionTime`
