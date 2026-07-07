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

## Maestro DB Accumulation

```bash
MAESTRO_NS=$(kubectl get svc --all-namespaces --no-headers 2>/dev/null | grep maestro | awk '{print $1}' | head -1)

# All commands in a single Bash invocation (shell state does not persist between calls)
timeout 10 kubectl port-forward -n "$MAESTRO_NS" svc/maestro 8001:8000 & PF_PID=$!; sleep 2; kill -0 $PF_PID 2>/dev/null && curl -s --max-time 5 "http://localhost:8001/api/maestro/v1/resource-bundles?size=1" | jq '.total'; kill $PF_PID 2>/dev/null
```

If `total` >> 100, the Maestro REST API's default page size may be excluding test resources. See hyperfleet-e2e PR #79, HYPERFLEET-992.

## Orphaned K8s Resources

```bash
# Stale ClusterRoles from prior runs
kubectl get clusterroles -o name | grep adapter-

# Orphaned test namespaces
kubectl get namespaces -o name | grep -E 'e2e-|test-'

# Orphaned ManifestWorks
kubectl get appliedmanifestworks -A --no-headers 2>/dev/null | wc -l
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
PLATFORM_NS=$(kubectl get svc --all-namespaces --no-headers 2>/dev/null | grep hyperfleet-sentinel | awk '{print $1}' | head -1)
timeout 10 kubectl port-forward -n "$PLATFORM_NS" svc/hyperfleet-sentinel 9090:9090 & PF_PID=$!; sleep 2; kill -0 $PF_PID 2>/dev/null && curl -s --max-time 5 http://localhost:9090/metrics | grep -E 'hyperfleet_sentinel_(events_published_total|pending_resources)'; kill $PF_PID 2>/dev/null
```

## Live API Status Check

```bash
timeout 10 kubectl port-forward -n "$PLATFORM_NS" svc/hyperfleet-api 8000:8000 & PF_PID=$!; sleep 2; kill -0 $PF_PID 2>/dev/null && curl -s --max-time 5 "http://localhost:8000/api/hyperfleet/v1/clusters/<cluster-id>/statuses" | jq '.items[] | {adapter, conditions: [.conditions[] | {type, status, reason}]}'; kill $PF_PID 2>/dev/null
```

## GKE Node Operations

```bash
# Check for node upgrades/repairs overlapping the test run
gcloud container operations list --zone=<zone-from-step-1e> --filter="operationType:(UPGRADE_NODES OR REPAIR_CLUSTER OR UPGRADE_MASTER) AND startTime>='<run-date>T00:00:00Z' AND startTime<='<run-date>T23:59:59Z'" --format="table(name,operationType,startTime,endTime,status)" 2>/dev/null

# Also check the day before
gcloud container operations list --zone=<zone-from-step-1e> --filter="operationType:(UPGRADE_NODES OR REPAIR_CLUSTER OR UPGRADE_MASTER) AND startTime>='<day-before-run>T00:00:00Z' AND startTime<='<run-date>T23:59:59Z'" --format="table(name,operationType,startTime,endTime,status)" 2>/dev/null
```

**Do NOT use `--limit`.** Date-filter instead.

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
