# Candidate Pre-Filter (MANDATORY)

Before overlap analysis, apply these filters to each candidate. Any candidate that fails a filter is DROPPED — do not carry it forward.

```markdown
| Candidate | Filter Applied | Verdict | Reason |
|---|---|---|---|
| Candidate A | Component boundary | DROP | TLS cert validation is single-component (adapter->Maestro client), not cross-component E2E |
| Candidate B | Implicit coverage | DROP | Parity proven by cluster.md (k8s) + maestro.md (Maestro) both passing — no single test needed |
| Candidate C | Implicit cross-file coverage | DROP | concurrent-processing.md validates all deployed adapters regardless of transport mode |
```

## Filter 1: E2E Scope Boundary

Re-check each candidate against the scope boundary table. Ask: **"Does this test validate a customer-facing workflow across multiple components?"**

DROP if the failure/behavior happens entirely within one component:
- Client configuration errors (TLS, auth, connection strings) -> integration test
- Internal retry/backoff behavior -> unit test
- Input validation at a single API boundary -> unit/integration test
- Internal state management within one service -> unit test

## Filter 2: Implicit Cross-File Coverage

Check if the AC is already proven by **multiple existing test files collectively passing**:
- If test file A proves "k8s transport works" and test file B proves "Maestro transport works," then "operational parity" is implicitly proven — no side-by-side comparison test needed
- If a test validates "all deployed adapters," it covers any adapter type deployed in the environment (transport-agnostic)

## Filter 3: Third-Party System Internals

DROP candidates that test internal behavior of external/third-party systems:
- Maestro's resource-bundle lifecycle management -> Maestro's scope
- Broker's message deduplication guarantees -> Broker's scope
- K8s garbage collection behavior -> K8s scope
- Only test what HyperFleet components observe via API or K8s resource status

## Filter 4: Design-Time vs Runtime Guarantees

DROP candidates that test development constraints rather than runtime behavior:
- "Zero code changes required" -> verified by same binary running with both configs (CI/build scope)
- "No breaking changes to existing implementations" -> verified by existing tests continuing to pass (regression suite)
- "Backward compatible API" -> verified by existing API tests passing after feature merge

## Rules

- Present the pre-filter table to the user showing which candidates survived and which were dropped
- If ALL candidates are dropped, this is a valid outcome — it means existing coverage is sufficient
- Dropped candidates may still generate Jira gap specs if they belong in other test scopes (integration, perf, Helm)
