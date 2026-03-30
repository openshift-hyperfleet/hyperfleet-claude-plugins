# Red Flags and Common Mistakes

| Mistake | Fix |
|---------|-----|
| **Scope** | |
| Testing internal component behavior in E2E | E2E validates via API endpoints and K8s resources only |
| Including API input validation as Tier0/Tier1 | Tier2 at most — more naturally covered by unit/integration tests |
| Calling internal-only APIs (e.g., POST /statuses) | Only call customer-facing endpoints (read and write: GET, POST, PUT, DELETE, PATCH); do not call internal-only APIs |
| Duplicating what API integration tests cover | If API integration covers it, skip it in E2E |
| Assuming internal behavior ("restart Sentinel triggers duplicates") | Flag uncertain mechanisms for team discussion |
| **Test design** | |
| Designing without reading existing tests (FULL content) | Read every step and expected result, not just titles |
| Skipping traceability matrix or overlap analysis | Both are MANDATORY before writing any test file |
| Writing test file before showing overlap table | Present to user FIRST, get confirmation |
| Deriving tests by intuition only | Apply at least one formal technique per gap |
| Only testing happy path states | Map full state diagram: regression (True->False), stuck states |
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
| Generating deployment commands that don't match actual process | Never invent fictional commands; cite the real CLI commands, scripts, or documented CI/CD steps when available, or use accurate high-level descriptions that map directly to real tooling |
| **Candidate filtering** | |
| Proposing test for single-component failure (TLS, auth, client config) | Apply scope boundary filter — single-component errors belong in integration tests |
| Creating test when multiple test files already prove the AC collectively | Check cross-file implicit coverage — don't require one test to prove what separate suites demonstrate |
| Duplicating transport-specific test when existing test is transport-agnostic | Tests validating "all deployed adapters" already cover any transport mode deployed |
| Testing internal behavior of third-party systems (Maestro cleanup, broker dedup) | Only test what HyperFleet observes via API or K8s resource status |
| Testing design-time constraints ("zero code changes", "no breaking changes") | These are verified by existing tests continuing to pass, not by new E2E tests |
| Carrying candidates through overlap analysis before checking scope | Apply pre-filter BEFORE overlap analysis to avoid wasted effort |
| **Risk & coverage** | |
| All tests at same depth regardless of risk | Assess likelihood x blast radius; HIGH risk gaps get 2-4 scenarios |
| Only testing explicit ACs from epic | Extract implicit ACs: idempotency, backward compat, data integrity, security boundaries |
| Ignoring impact on existing tests from other epics | Run cross-epic regression check; flag state model or precondition changes |
| **Reliability** | |
| Using `sleep` instead of polling for async operations | Poll with interval + timeout + success condition; never fixed sleep |
| Asserting on timing ("completes within 30s") | Assert on state, not time. Timeout is a failure boundary, not an assertion |
| Tests that pass alone but fail in parallel runs | Resource name collisions, shared state, ordering assumptions — use `{{.Random}}`, isolate fully |
| No flakiness notes on timing-sensitive steps | Flag polling strategy and isolation mechanism in test step notes |
| Marking tests Manual Only without justification | Default is Automated; Manual Only requires explicit rationale |
| No test data variants specified | Define minimal/maximal/boundary/invalid payloads per test |
