# Output Example — HIGH Confidence

Real output from the `/e2e-debug` investigation of tier1-nightly run `2058873327929266176` (May 25, 2026). Diagnosis was validated against the actual fix commits (hyperfleet-adapter PR #160, hyperfleet-e2e PR #107).

---

**CI Failure Analysis for:** tier1-nightly / 2058873327929266176
**URL:** https://prow.ci.openshift.org/view/gs/test-platform-results/logs/periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier1-nightly/2058873327929266176
**Confidence:** HIGH

### 1. The Failure Point
* **Failing Step/Job:** `openshift-hyperfleet-e2e-test` (setup passed, both cleanups passed)
* **Failing Test:** 5 specs failed, all in the Maestro transport negative scenario suite:
  - `[Suite: adapter][maestro-transport][negative] Adapter Framework - Maestro Transport Negative Scenarios -- should fail when targeting unregistered Maestro consumer and report appropriate error [tier1]`
  - `[Suite: adapter][maestro-transport][negative] -- should fail to discover ManifestWork when discovery name does not match created resource [tier1]`
  - `[Suite: adapter][maestro-transport][negative] -- should fail nested discovery when resource names are wrong [tier1]`
  - `[Suite: adapter][maestro-transport][negative] -- should fail post-action when status API is unreachable [tier1]`
  - `[Suite: cluster][negative] Cluster Can Reflect Adapter Failure in Top-Level Status -- should reflect adapter precondition failure in cluster top-level status [tier1, negative]`
* **Exact Error:** `helm upgrade failed: exit status 1 (output: Error: execution error at (hyperfleet-adapter/templates/deployment.yaml:94:31): broker.type must be set to one of: googlepubsub, rabbitmq)`
* **Cascade:** All 5 failures share the same root cause — the Helm template validation rejects the adapter install before any pods are created. These are NOT independent failures.

### 2. Root Cause Analysis
* The adapter Helm chart (`hyperfleet-adapter` PR #160, `HYPERFLEET-1104`, merged May 21) changed the broker type resolution from an inference-based fallback to a hard `required` call at `templates/deployment.yaml:94`. The E2E test helpers that deploy ephemeral negative-scenario adapters (`cl-m-unreg-consumer`, `cl-m-wrong-ds`, `cl-m-wrong-nest`, `cl-m-bad-api`, `cl-precondition-error`) are not passing the `broker.type` Helm value in their override configurations. The adapters fail at Helm template validation before any pods are created, so the negative scenarios never reach the application-level failure behavior they are designed to test.

### 3. Supporting Evidence
* **Timeline:**

| UTC | Event |
|-----|-------|
| 11:37:44 | Setup complete — 9/9 pods Running, API healthy |
| 11:37:51 | Tests begin |
| 11:37:51-11:44:09 | 6 tests pass (nodepool isolation, external deletion, 3 Maestro negative) |
| 11:44:09 | First failure — `cl-m-bad-api` Helm install rejected |
| 11:50:41 | Test step exits (5 failures) |

* **Logs:** All 5 failures show identical Helm template error at line 94:31. Setup step succeeded — all 8 core Helm releases deployed, all pods Running, API and Maestro endpoints healthy. The pre-existing `cl-maestro` adapter (deployed during setup with `--set broker.type=googlepubsub`) works correctly.
* **Documentation:** Matches "Deployment failure" category in CI Failure Debugging section.
* **Related Changes:** `hyperfleet-adapter` PR #160 (`HYPERFLEET-1104`, merged 2026-05-21) introduced the required validation. Fix: `hyperfleet-e2e` PR #107 (`HYPERFLEET-1104`, merged 2026-05-25).
* **Cross-Run Comparison:** Last passing run used pre-PR #160 adapter chart. Same e2e code, same GKE version. Only change: adapter chart added `broker.type` validation.
* **Prior Runs:** FAIL, FAIL, FAIL, FAIL, PASS. 4-day regression window (May 21-25).
* **Live Cluster:** Not checked (not needed — error is deterministic and fully explained by logs + git history).

### 4. Recommended Action
* Add `broker.type: googlepubsub` to all test adapter `values.yaml` files under `testdata/adapter-configs/`.
* Alternatively, modify the test helper's `deployAdapter` function to pass `--set broker.type=googlepubsub` by default.
* A retry will fail identically — this is not flaky or transient.
