# Systematic Test Design Techniques

**Apply at least one technique per coverage gap.** Select based on what you're testing:

| What you're testing | Primary technique | Secondary |
|---|---|---|
| Resource lifecycle (create/update/delete) | State Transition | — |
| API input validation | Equivalence Partitioning | Boundary Value Analysis |
| Adapter preconditions / dependency chains | Decision Table | State Transition |
| Component failure handling | Failure Mode Analysis | State Transition (recovery) |

## 1. State Transition Testing (Primary for HyperFleet)

Map states and transitions, then derive test cases covering: all valid transitions (Tier0), invalid transitions (Tier1), stuck-in-state (Tier2), state regression True->False (Tier1).

**HyperFleet state models:**
```text
Cluster:    Pending -> Provisioning -> Ready / Failed. Ready -> Deleting -> Deleted
Adapter:    Unknown -> False -> True (normal). True -> False (regression). Unknown stuck (timeout)
Resource:   Ready=False -> Ready=True (all adapters Available)
```

## 2. Equivalence Partitioning

Divide inputs into valid/invalid classes. Test one value per class.

### HyperFleet Examples

| Input | Valid Classes | Invalid Classes |
|---|---|---|
| Platform | `"gcp"`, `"aws"` (one test each) | `"unsupported"`, empty string, missing field |
| Cluster size (node count) | Small (1), Typical (3), Large (10) | 0 nodes, negative value |
| Cluster name | Lowercase alphanumeric with hyphens | Contains uppercase, special chars, exceeds max length |
| Adapter count | Single adapter, Multiple adapters (2-3) | Zero adapters configured |

### Steps

1. Identify the input under test
2. Partition into valid and invalid equivalence classes
3. Select one representative value per class
4. Design one test case per representative value

## 3. Boundary Value Analysis

Test at edges of valid ranges: min, min+1, typical, max-1, max, below min, above max.

### HyperFleet Examples

| Boundary | Min | Min+1 | Typical | Max-1 | Max | Below Min | Above Max |
|---|---|---|---|---|---|---|---|
| Node count | 1 | 2 | 5 | 9 | 10 | 0 | 11 |
| Cluster name length | 1 char | 2 chars | 20 chars | 62 chars | 63 chars | empty | 64 chars |
| Concurrent clusters | 1 | 2 | 5 | — | system limit | 0 | limit+1 |
| Adapter conditions | 1 adapter | 2 adapters | 3 adapters | — | all registered | 0 adapters | — |

### Steps

1. Identify the numeric or string-length boundary from the spec/API schema
2. Create a test for each boundary point (min, min+1, typical, max-1, max)
3. Create negative tests for below-min and above-max
4. Focus E2E tests on boundaries that affect cross-component behavior (e.g., max concurrent clusters)

## 4. Decision Table Testing

For multi-condition behavior, enumerate all condition combinations and the expected action for each.

### HyperFleet Example: Cluster Ready Aggregation

| # | Dependency Available | Precondition Met | All Adapters Applied | All Adapters Available | Expected Cluster Status |
|---|---|---|---|---|---|
| 1 | True | True | True | True | Ready=True |
| 2 | True | True | True | False | Ready=False |
| 3 | True | True | False | — | Ready=False |
| 4 | True | False | — | — | Provisioning (resources skipped) |
| 5 | False | — | — | — | Ready=False (dependency failure) |

### Steps

1. List all conditions that affect the outcome
2. Build a table with all meaningful combinations (prune infeasible combos)
3. Define the expected action/result for each row
4. Design one test case per row — each test sets up the specific condition combination and asserts the expected result

## 5. Failure Mode Analysis

For each component in the test boundary, systematically enumerate failure scenarios.

### HyperFleet Component Failure Checklist

For each component, test these failure modes:

| Failure Mode | HyperFleet API | Sentinel | Broker | Adapter |
|---|---|---|---|---|
| **Unavailable** | API returns 503 | Sentinel pod down | Broker unreachable | Adapter pod crashed |
| **Invalid data** | Malformed cluster response | — | Corrupted event payload | Invalid API response for precondition |
| **Slow/timeout** | API response > timeout | Polling delay | Event delivery delay | Adapter execution timeout |
| **Partial failure** | Some endpoints up, others down | — | Some events delivered | Some adapters succeed, others fail |
| **Recovery after restore** | API returns to 200 | Sentinel resumes polling | Events redelivered | Adapter re-processes, reaches correct state |

### Example Test Case: Adapter Crash Recovery

1. **Setup**: Create cluster, wait for adapter to report Applied=True
2. **Inject failure**: Kill the adapter pod
3. **Verify degraded state**: Cluster shows adapter Health=Unknown or False
4. **Restore**: Adapter pod restarts
5. **Verify recovery**: Adapter re-processes event, reports Applied=True, cluster reaches Ready

### Steps

1. Pick a component within the E2E test boundary
2. Walk through each failure mode row
3. For HIGH-risk failures (likelihood x blast radius), design 2-4 scenario variations
4. For each scenario: setup -> inject failure -> verify degraded state -> restore -> verify recovery
