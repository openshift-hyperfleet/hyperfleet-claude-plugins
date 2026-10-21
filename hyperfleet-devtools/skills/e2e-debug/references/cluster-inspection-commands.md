# Cluster Inspection Commands

Commands for Step 5 of the e2e-debug skill. All commands are **read-only**. Replace placeholders with values extracted in Step 1e.

## kubectl Context Verification

```bash
kubectl config current-context 2>/dev/null
```

## Namespace Discovery

```bash
# Check if the run's namespace still exists
kubectl get namespace e2e-<run-id> --no-headers 2>/dev/null

# Find any active test namespaces
kubectl get namespaces -o name | grep -E '^namespace/e2e-'
```

## Remote Delivery (cl-desire, Redis, Applier)

When `cl-desire` is stuck and not converging, check the logs in this order:

**Live environment only** (the run's namespace still exists):

```bash
# The desire store: is it up, and does it accept connections?
kubectl logs -n <namespace> -l app.kubernetes.io/instance=redis --tail=200

# The remote adapter: did it write the desires?
kubectl logs -n <namespace> -l app.kubernetes.io/instance=cl-desire --tail=200

# The applier: did it apply them, and did it report status back?
kubectl logs -n <namespace> -l app.kubernetes.io/instance=hyperfleet-applier --tail=200
```

**After the run has finished** (the CI namespace is deleted): the same components' logs are
captured in the setup step's artifacts — the layout, URL mapping, and filename patterns are in
`references/ci-quick-reference.md` (GCS Artifact Structure).

## Orphaned K8s Resources

```bash
# Stale ClusterRoles from prior runs
kubectl get clusterroles -o name | grep adapter-

# Orphaned test namespaces
kubectl get namespaces -o name | grep -E 'e2e-|test-'
```

## Pod Health and Crash Detection

```bash
# If namespace exists: check pod restarts, OOMKilled, CrashLoopBackOff
kubectl get pods -n e2e-<run-id> -o wide --sort-by='.status.containerStatuses[0].restartCount'
kubectl get pods -n e2e-<run-id> -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}' 2>/dev/null

# K8s events for OOM, scheduling, mount, pull failures
kubectl get events -n e2e-<run-id> --sort-by='.lastTimestamp' --field-selector type!=Normal | tail -20
```

## Node-Level Checks

```bash
# Node resource usage
kubectl top nodes 2>/dev/null

# Cluster-wide warning events (OOM, eviction, scheduling failures)
kubectl get events --all-namespaces --sort-by='.lastTimestamp' --field-selector type!=Normal 2>/dev/null | grep -i "oom\|evict\|kill\|exceeded\|pressure" | tail -10
```

## Sentinel & Adapter Metrics

```bash
# Exact service match for sentinel
PLATFORM_NS=$(kubectl get svc --all-namespaces --no-headers 2>/dev/null | awk '$2 ~ /^.*hyperfleet-sentinel$/ {print $1; exit}')
if [ -z "$PLATFORM_NS" ]; then echo "ERROR: hyperfleet-sentinel service not found" >&2; else
  timeout 10 kubectl port-forward -n "$PLATFORM_NS" svc/hyperfleet-sentinel 9090:9090 & PF_PID=$!
  for i in $(seq 1 10); do curl -s --max-time 1 http://localhost:9090/metrics >/dev/null 2>&1 && break; sleep 0.5; done
  kill -0 $PF_PID 2>/dev/null && curl -s --max-time 5 http://localhost:9090/metrics | grep -E 'hyperfleet_sentinel_(events_published_total|pending_resources)'
  kill $PF_PID 2>/dev/null
fi
```

## Live API Status Check

```bash
# Exact service match — self-contained, does not depend on any other block having run first
PLATFORM_NS=$(kubectl get svc --all-namespaces --no-headers 2>/dev/null | awk '$2 == "hyperfleet-api" {print $1; exit}')
if [ -z "$PLATFORM_NS" ]; then echo "ERROR: hyperfleet-api service not found" >&2; else
  timeout 10 kubectl port-forward -n "$PLATFORM_NS" svc/hyperfleet-api 8000:8000 & PF_PID=$!
  for i in $(seq 1 10); do curl -s --max-time 1 http://localhost:8000/api/hyperfleet/v1/clusters?size=0 >/dev/null 2>&1 && break; sleep 0.5; done
  kill -0 $PF_PID 2>/dev/null && curl -s --max-time 5 "http://localhost:8000/api/hyperfleet/v1/clusters/<cluster-id>/statuses" | jq '.items[] | {adapter, conditions: [.conditions[] | {type, status, reason}]}'
  kill $PF_PID 2>/dev/null
fi
```

## GKE Node Operations

```bash
# Query for operations that could OVERLAP the test window, not just operations that started on the same day.
# An upgrade that started at 23:50 the night before and ended at 00:10 during the test would be missed by a calendar-day filter.
# Use the setup-complete and first-failure timestamps from Step 1e as boundaries.
# Replace <2-hours-before-setup> and <first-failure-time> with ISO 8601 from the timeline.
# Query ops that started up to 2 hours before setup (they could still be running) through first failure.
gcloud container operations list --zone=<zone-from-step-1e> --filter="operationType:(UPGRADE_NODES OR REPAIR_CLUSTER OR UPGRADE_MASTER) AND startTime>='<2-hours-before-setup>' AND startTime<='<first-failure-time>'" --format="table(name,operationType,startTime,endTime,status)" 2>/dev/null
```

**Do NOT use `--limit`.** Then manually check which operations' `startTime`-`endTime` window overlaps with the test window (`setup-complete` to `first-failure`).

## GKE Node-Specific Check

```bash
# Check the node that hosted the API pod (from all-resources.txt)
kubectl describe node <node-name-from-step-1e> 2>/dev/null | grep -A5 -i "condition\|taint\|unschedulable"

# If NotFound, the node was replaced
kubectl get node <node-name-from-step-1e> 2>&1
```

## GKE Node Events

```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp' --field-selector type!=Normal 2>&1 | grep -i "cordon\|drain\|notready\|deletingnode\|nodenotready\|readonlyfilesystem\|upgrade\|preempt" | tail -15
```

## GKE Maintenance Policy

```bash
gcloud container clusters describe <cluster-name-from-step-1e> --zone=<zone-from-step-1e> --format="yaml(maintenancePolicy)" 2>/dev/null
```

If no `maintenancePolicy` is returned, node auto-upgrades can fire any time. See HYPERFLEET-1225.

## GKE Cluster Health

```bash
gcloud container clusters describe <cluster-name-from-step-1e> --zone=<zone-from-step-1e> --format="table(status,currentNodeCount,currentMasterVersion)" 2>/dev/null
```

## Pub/Sub Leaks

```bash
gcloud pubsub topics list --filter="name:hyperfleet" --format="table(name)" 2>/dev/null
gcloud pubsub subscriptions list --filter="name:hyperfleet" --format="table(name,ackDeadlineSeconds)" 2>/dev/null
```

## GCP Project Verification

```bash
gcloud config get-value project 2>/dev/null
```

If wrong project, add `--project=<project-id-from-step-1e>` to all gcloud commands. Do NOT run `gcloud config set project` — that mutates the user's local config.
