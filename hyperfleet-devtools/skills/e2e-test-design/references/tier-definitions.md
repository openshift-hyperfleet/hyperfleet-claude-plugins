# Tier Definitions

| Tier | Purpose | Examples |
|------|---------|---------|
| **Tier0** | Critical happy-path workflows, blocks release | Cluster creation lifecycle, nodepool lifecycle, K8s resource metadata, adapter dependencies |
| **Tier1** | Important negative cases customers might encounter | Adapter failure in cluster status, crash recovery, concurrent creation conflicts |
| **Tier2** | Edge cases unlikely in production | Timeout detection, generation-based skip, name-length boundary |

## Risk-Based Prioritization

Tier alone is not enough. Assess **risk** for each coverage gap to determine test depth (number of scenarios per AC):

```markdown
| AC | Likelihood | Blast Radius | Risk Score | Test Depth |
|---|---|---|---|---|
| AC2: Adapter failure blocks Ready | Medium | High (cluster stuck) | HIGH | 3 scenarios (failure, crash, timeout) |
| AC5: Name-length boundary | Low | Low (single request) | LOW | 1 scenario |
```

- **Likelihood**: How likely is this to happen in production? (High/Medium/Low)
- **Blast Radius**: If it fails, what's the impact? Single resource, all resources, data loss? (High/Medium/Low)
- **Risk Score**: Likelihood x Blast Radius matrix:

| | Low Blast | Medium Blast | High Blast |
|---|---|---|---|
| **High Likelihood** | MEDIUM | HIGH | CRITICAL |
| **Medium Likelihood** | LOW | MEDIUM | HIGH |
| **Low Likelihood** | LOW | LOW | MEDIUM |

- **Test Depth**: HIGH/CRITICAL -> 2-4 scenarios covering variations. MEDIUM -> 1-2 scenarios. LOW -> 1 scenario
- Apply risk assessment AFTER the traceability matrix, BEFORE designing candidates

## Tier Design Guidelines

**Tier0 — Full Lifecycle (positive tests)**:
- MUST cover: create -> initial state (False) -> adapter execution -> transitions -> final state (Ready=True, Available=True)
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
