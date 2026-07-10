# Known Failure Patterns

Cross-reference the error from the logs against these categories. The "Handbook Section" column refers to sections in the [E2E Debugging QRH](https://github.com/openshift-hyperfleet/hyperfleet-e2e/blob/main/docs/debugging.md).

## Error Signature → Category Mapping

| Error Signature | Category | Handbook Section | First Check |
|---|---|---|---|
| `Eventually timed out` / `context deadline exceeded` | Timeout | Failure Triage Flowchart + Adapter Debugging + Timeout Tuning | Identify which adapter is stuck via `GET /api/hyperfleet/v1/clusters/{id}/statuses` |
| Perf/duration assertion fails by a small margin against a hardcoded threshold (e.g., `20.208s` vs a `20s` limit, `30.250s` vs `30s`) | Marginal performance-threshold miss | Timeout Tuning | Check the margin size and whether CI node/cluster resource contention overlapped the test window before treating this as a functional regression — a small, one-off overshoot is usually environmental, not a code bug. See HYPERFLEET-1185 |
| `Expected X to equal Y` / `to be true` | Assertion failure | Failure Triage Flowchart | Read the source line from the stack trace to see what condition was checked |
| `unexpected status code 400` / `422` | Validation error | Failure Triage Flowchart (API Error Format) | Parse the embedded RFC 9457 JSON for the `code` field (e.g., `HYPERFLEET-VAL-001`) and `errors` array for field-level details |
| `unexpected status code 404` | Not found | Failure Triage Flowchart (API Error Format) | Check cluster ID — resource may have been deleted or never created. Error code: `HYPERFLEET-NTF-*` |
| `unexpected status code 409` | Conflict | Failure Triage Flowchart (API Error Format) | Resource may be in deletion (`deleted_time` set). Error code: `HYPERFLEET-CNF-*` |
| `unexpected status code 500` / `503` | Server error | Failure Triage Flowchart (API Error Format) | Check API pod logs for panic or DB connection errors. Error code: `HYPERFLEET-INT-*` or `HYPERFLEET-SVC-*` |
| `HYPERFLEET-{CAT}-{NNN}` error codes | API error (any) | Failure Triage Flowchart | Categories: `VAL` (validation), `AUT` (auth), `AUZ` (authz), `NTF` (not found), `CNF` (conflict), `LMT` (rate limit), `INT` (internal), `SVC` (service) |
| `panic` / `nil pointer` | Code crash | Failure Triage Flowchart | Check the full stack trace — often a test helper initialization issue |
| `connection refused` | Connectivity / pod down | Failure Triage Flowchart | Multiple possible causes — do NOT assume the pod crashed. Check in order: (1) GKE node operations via `gcloud container operations list` for node upgrade/drain overlapping the test, (2) K8s events for `ReadOnlyFileSystemDetected`/`NodeNotReady`/`DeletingNode`, (3) `FailedToCreateEndpoint` warnings as a signal of node replacement, (4) pod describe for OOMKilled/CrashLoopBackOff. See HYPERFLEET-1225 for a confirmed case of GKE node upgrade causing this |
| `EOF` / `connection reset by peer` calling a HyperFleet service's own REST endpoint (NOT `Unable to connect to the server: EOF`, which is the K8s control-plane API — see Prow Infrastructure Errors below) — occurs immediately after a successful readiness/health check, during a Helm `--wait` rolling upgrade of that service, with no GKE node operation overlapping the window | LoadBalancer backend-pool drain race during rolling update | CI Failure Debugging | Check whether the failing service's Helm chart defines a `preStop` lifecycle hook and a sufficient `terminationGracePeriodSeconds`. Without a preStop delay, the pod stops serving before the LB backend pool is updated, so in-flight or newly-routed requests hit a closed socket. See HYPERFLEET-1306 — hyperfleet-api PR #268 added a `preStop` hook and raised `terminationGracePeriodSeconds` to 70 to fix this |
| `invalid ownership metadata` / `annotation validation error` | Helm ownership conflict | Resource Cleanup + CI Failure Debugging | Delete stale ClusterRoles from a previous run |
| `resource already exists` | Test pollution | Resource Cleanup | Check for orphaned namespaces or ManifestWorks from a prior test |
| `namespace collision` | Test pollution | Resource Cleanup | Cluster ID reuse — check cleanup from previous test |
| `context deadline exceeded` (in setup step) | Deployment failure | CI Failure Debugging | Check pod status, resource limits, Helm chart configs, PostgreSQL connectivity |
| `Available=False` with reason `JobRunning` | Adapter still processing | Adapter Debugging + Timeout Tuning | Timeout too short — increase it |
| `Available=False` with reason `JobFailed` | Adapter business logic error | Adapter Debugging | Check adapter pod logs |
| `Available=False` with reason `PreconditionsNotMet` | Dependency adapter stuck | Adapter Debugging | Investigate the dependency adapter first |
| `Applied=False` with reason `ResourceCreationFailed` | K8s resource creation error | Adapter Debugging | Check K8s events and RBAC permissions for the adapter |
| `Health=False` | Adapter health degraded | Adapter Debugging | Infrastructure issue — check K8s cluster health and adapter pod logs |
| `Finalized=False` during deletion | Adapter cleanup incomplete | Adapter Debugging + Resource Cleanup | Resource has `deleted_time` set. Check if adapter is still cleaning up (`CleanupInProgress`) or unhealthy (`AdapterUnhealthy`) |
| A negative test expects the adapter to report failure/`nil` status, but the adapter reports success instead, following an adapter framework change | Adapter behavioral drift after refactor | Adapter Debugging | Check whether a recent adapter parameter-resolution/defaulting refactor changed how missing or invalid params are handled — it may now silently resolve a default instead of surfacing the failure path the test expects. See HYPERFLEET-1339 |
| No status reported for an adapter | Event delivery failure | Timeout Tuning | Check Sentinel metrics and broker logs |
| ResourceBundle / ManifestWork not found but API returns 200 | Maestro DB pagination | N/A (requires live cluster) | Stale ResourceBundles accumulated past Maestro's default page size (100). Query `GET /resource-bundles?size=1` and check `total`. If >> 100, the test's resources are being paged out. Fix: use `search` param with JSONB syntax instead of `labelSelector` (see hyperfleet-e2e PR #79, HYPERFLEET-992) |
| Test returns `nil` for a resource lookup with no error | Silent parameter ignored | N/A | An API parameter (e.g., `labelSelector`) may be silently ignored — the API returns 200 OK with unfiltered/wrong data instead of an error. Logs will look clean. Requires live Maestro/API query to diagnose. Check the API docs for supported query parameters |

## Prow Infrastructure Errors (Not HyperFleet Code Issues)

These errors originate from the shared Prow/K8s test cluster, NOT from HyperFleet code. Do not investigate recent HyperFleet commits for these — a retry or Slack escalation to `#forum-ocp-testplatform` is the correct action.

| Error Signature | Cause | Action |
|---|---|---|
| `etcdserver: mvcc: database space exceeded` | Shared cluster etcd is full | Retry; if persistent, escalate to `#forum-ocp-testplatform` |
| `ImagePullBackOff` / `ErrImagePull` on non-HyperFleet images | Container registry rate limit or outage | Retry after 15-30 minutes |
| `dial tcp: lookup ... no such host` | DNS resolution failure in cluster | Retry; if persistent, check cluster DNS pods |
| `Unable to connect to the server: EOF` | API server overloaded or restarting | Retry |
| `error dialing backend: EOF` / `TLS handshake timeout` | Network connectivity issue in Prow cluster | Retry |
| `nodes are available: ... Insufficient cpu/memory` | Cluster capacity exhausted | Retry during off-peak; escalate if persistent |
| `serviceaccount ... not found` / `token expired` | Service account or auth issue in Prow | Escalate to `#forum-ocp-testplatform` |
| `cat: /tmp/secret/namespace_name: No such file or directory` (in cleanup steps) | Cascade from setup failure | Not the root cause — check setup step for the real error |
| `i/o timeout` then `connection refused` on API mid-test (setup was healthy) | GKE node upgrade/drain/replacement | Check `gcloud container operations list` for `UPGRADE_NODES` overlapping the test window. Node hosting API/postgres/maestro-db was drained and replaced. See HYPERFLEET-1225. Fix: configure GKE maintenance window to avoid CI hours |
| `ReadOnlyFileSystemDetected` / `NodeNotReady` / `DeletingNode` in K8s events | GKE node being replaced | Node auto-upgrade or repair in progress. Pods on that node are evicted. Not a code bug |
| `Multi-Attach error` on PVs (postgres, maestro-db) | PV force-detach during node replacement | PersistentVolumes from the old node can't attach to the new node until force-detached. Delays pod recovery after node replacement |
| `FailedToCreateEndpoint` for `hyperfleet-api` or adapter services in `default` namespace | Endpoint churn from node replacement or concurrent runs | Indicates rapid pod rescheduling or overlapping test runs creating services with the same name. If seen alongside `connection refused`, a node was likely replaced mid-run |

## Flakiness Indicators

If a test passes sometimes and fails others, check for:

- Race conditions in concurrent tests (missing `sync.WaitGroup` or `ginkgo.GinkgoRecover()`)
- Timing sensitivity (polling faster than the system can process)
- Resource name collisions between parallel runs
- `Available=Unknown` during adapter transitions (only valid for the first report)

See Handbook "Common Patterns" section for details.

## Accumulated Persistent State (Not Visible in Single-Run Logs)

The shared Prow GKE cluster persists between runs. Even after a run's namespace is deleted, these states accumulate and cause failures that GCS log artifacts alone cannot explain:

| State | Where it lives | How it causes failures | Detection |
|---|---|---|---|
| Stale Maestro ResourceBundles | Maestro PostgreSQL DB | Total exceeds default page size (100), pushing test resources off the first page. Queries return `nil` with no error | `kubectl port-forward svc/maestro 8001:8000` then `curl .../resource-bundles?size=1 \| jq .total` |
| Orphaned ManifestWorks | Maestro DB + K8s AppliedManifestWorks | Slow Maestro reconciliation, resource conflicts | `kubectl get appliedmanifestworks -A --no-headers \| wc -l` |
| Stale ClusterRoles | Cluster-scoped K8s objects | Helm ownership conflicts (`invalid ownership metadata`) | `kubectl get clusterroles -o name \| grep adapter-` |
| Leaked Pub/Sub topics/subscriptions | Google Cloud Pub/Sub | Subscription collisions, quota exhaustion | `gcloud pubsub subscriptions list --filter="name:hyperfleet"` |
| Orphaned test namespaces | K8s namespaces | Namespace collision, resource conflicts | `kubectl get namespaces -o name \| grep -E 'e2e-\|test-'` |

These failures typically present as: logs look clean, API returns 200 OK, no error codes — but the test assertion fails with a `nil` result or wrong data. When the log-based diagnosis reaches LOW confidence, check persistent state before escalating.

## "Works Locally, Fails in CI" Checklist

- CI deploys to a shared cluster — previous runs may leave residual resources
- **Maestro DB accumulates stale ResourceBundles across runs** — locally Maestro starts clean, in CI it may have hundreds of entries from prior runs
- Background clusters affect Sentinel evaluation timing
- CI environments have different network latency and resource constraints
- Verify CI job is using the expected image tags (all components from main)

See Handbook "Common Patterns" section for details.
