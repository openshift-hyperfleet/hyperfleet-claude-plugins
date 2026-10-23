# Output Example — HIGH Confidence

Real investigation of tier1-nightly run `2111419519061725184` (Oct 17, 2026), following the `/e2e-debug` workflow. Diagnosis was validated against the actual fix: hyperfleet-e2e PR #167 (`HYPERFLEET-1767`, merged Oct 19) — the Oct 19 nightly on the fix commit passed.

---

**CI Failure Analysis for:** tier1-nightly / 2111419519061725184
**URL:** https://prow.ci.openshift.org/view/gs/test-platform-results-public/logs/periodic-ci-openshift-hyperfleet-hyperfleet-e2e-main-e2e-tier1-nightly/2111419519061725184
**Confidence:** HIGH

### 1. The Failure Point
* **Failing Step/Job:** `openshift-hyperfleet-e2e-test` (setup passed, both cleanups passed)
* **Failing Test:** 2 specs failed, both in the version performance suite:
  * `[Suite: version][perf] Delete latency -- should delete a version within acceptable latency [tier1, perf, Serial]`
  * `[Suite: version][perf] Update latency -- should update a version within acceptable latency [tier1, perf, Serial]`
* **Exact Error:** `DELETE /channels/{parent_id}/versions/{id} exceeded threshold: median=55.254146ms threshold=50ms` (assertion at `pkg/helper/perf.go:54`; the Update spec failed identically at `median=52.472468ms`)
* **Cascade:** Both failures share the same root cause — the same 50ms API-write threshold, asserted by the same helper on the same resource kind. These are NOT independent failures. (One unrelated spec flaked and passed on retry.)

### 2. Root Cause Analysis
* The API-write thresholds (`ThresholdAPICreate/Update/Delete = 50ms` in `pkg/config/thresholds.go`) were calibrated on a GKE-dev baseline run (2026-07-27) where observed latencies were 3-10ms — a direct-cluster environment. In Prow, every sample also traverses the public LoadBalancer and the gateway, so most of the measured time is network; under CI contention the version write medians land at ~52-55ms, marginally over the hardcoded 50ms. The file's own comment flagged the gap: "No Prow tier1-nightly baseline yet; recalibrate once 5+ clean nightly runs are available."

### 3. Supporting Evidence
* **Timeline:**

| UTC | Event |
|-----|-------|
| 11:30:21 | Run starts |
| 11:41:12 | Setup complete — all releases deployed (hyperfleet-api-1.3.0, hyperfleet-adapter-2.2.0) on GKE `hyperfleet-dev-prow` (us-central1-a) |
| 11:47:30 | FIRST FAILURE — version DELETE latency: median=55.25ms vs 50ms (Ginkgo retry reproduced it: 55.42ms) |
| 12:03:29 | Second failure — version PATCH latency: median=52.47ms vs 50ms |
| 12:03:31 | Test step exits (45 passed, 2 failed, 1 flaked) |
| 12:05:39 | Run ends (FAILURE) |

* **Logs:** Both failures assert at `pkg/helper/perf.go:54`, n=5 samples per spec. The DELETE spec's Ginkgo retry produced a nearly identical median (55.42ms → 55.25ms), ruling out a transient spike within the test.
* **Documentation:** Matches the "Marginal performance-threshold miss" known pattern (HYPERFLEET-1185): a small overshoot against a hardcoded threshold is usually environmental, not a functional regression.
* **Related Changes:** No hyperfleet-api latency changes in the window (only a Konflux docs update). The e2e repo was at `b3ef98e` (HYPERFLEET-1505) — context, not cause: the same version-perf specs failed on Oct 15 as well, independently of any API change.
* **Cross-Run Comparison:** The Oct 18 run used the identical e2e commit (`b3ef98e`) and PASSED — same code, different outcome, confirming contention-dependent variance rather than a deterministic regression.
* **Prior Runs:** PASS, FAIL, FAIL, FAIL, FAIL, PASS, FAIL, FAIL, PASS, FAIL (this run), PASS, PASS — intermittent across 12 days.
* **Live Cluster:** Not checked (not needed — deterministic assertion values, the cross-run pattern, and the fix commit fully explain the failure).

### 4. Recommended Action
* Recalibrate the API-write thresholds from measured Prow baselines instead of the GKE-dev baseline — merged as hyperfleet-e2e PR #167 (HYPERFLEET-1767): baselines taken from tier1-nightly medians (2026-09-16 to 2026-10-16), noting that "each sample also goes through the public LoadBalancer and the gateway, so most of it is network time."
* Validation: the Oct 19 nightly ran the fix commit (`54003fa`) and PASSED.
* A retry before the fix was a coin flip — the same commit passed the next day. Not a functional regression in the API or the tests.
