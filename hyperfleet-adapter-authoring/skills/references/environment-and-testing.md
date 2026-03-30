# Environment Setup and Testing

## Pre-Flight Environment Check

**Before creating an adapter**, verify your infrastructure is accessible. This prevents configuration errors later.

### Quick Environment Check

Run these commands to validate your environment:

```bash
# 1. Check GCP project (if using Google Pub/Sub)
gcloud config get-value project

# 2. List available Maestro consumers (if using Maestro transport)
curl -s http://host.docker.internal:8100/api/maestro/v1/consumers | jq '.items[] | {name, id}'

# 3. Verify HyperFleet API access
curl -s http://host.docker.internal:8000/api/hyperfleet/v1/clusters | jq '.total'

# 4. Check Pub/Sub subscription exists
gcloud pubsub subscriptions describe <subscription-name>
```

### Environment Detection Script

Save this as `detect-environment.sh` to auto-detect your settings:

```bash
#!/bin/bash
echo "=== HyperFleet Adapter Environment Detection ==="

# Detect GCP project
PROJECT=$(gcloud config get-value project 2>/dev/null)
echo -e "\n[1] GCP Project:"
echo "    ${PROJECT:-NOT SET}"

# List Maestro consumers
echo -e "\n[2] Available Maestro consumers:"
CONSUMERS=$(curl -s http://host.docker.internal:8100/api/maestro/v1/consumers 2>/dev/null | \
  jq -r '.items[]? | "    - \(.name) (id: \(.id))"' 2>/dev/null)
if [ -n "$CONSUMERS" ]; then
  echo "$CONSUMERS"
else
  echo "    Could not connect to Maestro (is it running?)"
fi

# Check HyperFleet API
echo -e "\n[3] HyperFleet API:"
CLUSTER_COUNT=$(curl -s http://host.docker.internal:8000/api/hyperfleet/v1/clusters 2>/dev/null | \
  jq -r '.total? // "error"' 2>/dev/null)
if [ "$CLUSTER_COUNT" != "error" ]; then
  echo "    Connected - $CLUSTER_COUNT clusters found"
else
  echo "    Could not connect to HyperFleet API"
fi

# Suggest configuration
echo -e "\n[4] Suggested adapter-config.yaml settings:"
echo "    hyperfleetApi.baseUrl: http://host.docker.internal:8000"
echo "    maestro.httpServerAddress: http://host.docker.internal:8100"
echo "    maestro.grpcServerAddress: host.docker.internal:8090"
echo "    broker.googlepubsub.project_id: \"$PROJECT\""
echo ""
```

### What to Check

| Check | Purpose | Fix if Missing |
|-------|---------|----------------|
| GCP project | Pub/Sub event delivery | Run `gcloud auth login` and `gcloud config set project PROJECT_ID` |
| Maestro consumers | ManifestWork target | Check Maestro deployment, verify consumer registration |
| HyperFleet API | Cluster data and status reporting | Verify HyperFleet API is running on port 8000 |
| Pub/Sub subscription | Event reception | Create subscription with `gcloud pubsub subscriptions create` |

---

## Running Live (Real Infrastructure)

### Start the adapter

```bash
# Required environment variables
export BROKER_CONFIG_FILE=/path/to/broker-config.yaml   # separate from adapter-config
export KUBECONFIG=/path/to/kubeconfig                   # K8s credentials

hyperfleet-adapter serve \
  -c adapter-config.yaml \
  -t adapter-task-config.yaml \
  --log-level debug                   # debug | info | warn | error
```

The broker config is a **separate file** from the adapter config (the broker library reads it via `BROKER_CONFIG_FILE`, not from AdapterConfig). For Google Pub/Sub:

```yaml
# broker-config.yaml
broker:
  type: googlepubsub
  googlepubsub:
    project_id: "my-gcp-project"
    ack_deadline_seconds: 60
    create_topic_if_missing: false
    create_subscription_if_missing: false
subscriber:
  parallelism: 1
```

### Trigger an event manually

```bash
CLUSTER_ID="abc123"
gcloud pubsub topics publish cluster-events \
  --message="$(jq -n \
    --arg id "$CLUSTER_ID" \
    --arg source "/api/hyperfleet/v1/clusters/$CLUSTER_ID" \
    --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{
      specversion: "1.0",
      id: $id,
      type: "io.hyperfleet.cluster.updated",
      source: $source,
      time: $time,
      datacontenttype: "application/json",
      data: { id: $id, kind: "Cluster",
               href: ("/api/hyperfleet/v1/clusters/" + $id), generation: 1 }
    }')"
```

### Read the logs

With `--log-level debug`, the adapter emits structured log lines for each pipeline phase. Key patterns:

| Log message | Meaning |
|-------------|---------|
| `Phase param_extraction: RUNNING` | Event received, extracting params |
| `Phase preconditions: SUCCESS - MET` | Conditions passed, resources will run |
| `Phase preconditions: SUCCESS - NOT MET` | Conditions not met, resources skipped (normal convergence behavior) |
| `Resource[name] processed: operation=create` | Resource created |
| `Resource[name] processed: operation=skip` | Same generation, no-op (idempotent) |
| `Resource[name] discovered and stored in context` | Post-apply discovery succeeded |
| `Phase post_actions: SUCCESS` | Status payload posted to HyperFleet |
| `Event execution finished: event_execution_status=success` | Full pipeline completed |
| `HyperFleet API response: 400 Bad Request` | Payload shape wrong -- check method/body |
| `HyperFleet API response: 405 Method Not Allowed` | Wrong HTTP method -- statuses endpoint requires `POST` |

An error in any phase sets `adapter.executionStatus=failed` but post-actions **always** run.

### Verify results

```bash
CLUSTER_ID="abc123"

# Check status reported to HyperFleet
curl -s "http://localhost:8000/api/hyperfleet/v1/clusters/$CLUSTER_ID/statuses" | jq .

# Check Kubernetes resource (direct transport)
kubectl get ns "${CLUSTER_ID,,}"
kubectl get all -n "${CLUSTER_ID,,}"

# Check ManifestWork applied on spoke cluster (Maestro transport)
kubectl --context "$GKE_CONTEXT" get appliedmanifestworks
kubectl --context "$GKE_CONTEXT" get ns "${CLUSTER_ID,,}"
```

Expected status payload when the adapter is healthy:

```json
{
  "items": [{
    "adapter": "my-adapter",
    "conditions": [
      { "type": "Applied",   "status": "True", "reason": "..." },
      { "type": "Available", "status": "True", "reason": "..." },
      { "type": "Health",    "status": "True", "reason": "Healthy" }
    ],
    "observed_generation": 1
  }]
}
```

If `observed_generation` appears as a quoted string (`"1"`) instead of an integer, your payload config is using `"{{ .generation }}"` -- fix it to `expression: "generation"`.

### Common Errors and Solutions

| Error Message | Root Cause | Solution |
|---------------|------------|----------|
| `maestro sourceID is required` | Missing `sourceId` in adapter-config.yaml | Add `sourceId: adapter-name` to `clients.maestro` section |
| `maestro server address is required` | Wrong field names in config | Use `httpServerAddress` and `grpcServerAddress` (not `baseUrl`/`grpcUrl`) |
| `fk_resources_consumers` constraint violation | Target consumer doesn't exist in Maestro | List consumers with `curl http://host.docker.internal:8100/api/maestro/v1/consumers \| jq '.items[].name'` and update `placementClusterName` capture to match |
| `Cluster with id='...' not found` (404) | Cluster doesn't exist in HyperFleet API | Create cluster first or verify cluster ID in event matches actual cluster |
| `405 Method Not Allowed` on status endpoint | Using PATCH/PUT instead of POST | Change `method: "POST"` in postActions apiCall |
| `observed_generation` is string not int | Using Go template for generation | Change to `expression: "generation"` (CEL) instead of `"{{ .generation }}"` |
| Adapter not receiving events | Subscription misconfigured | Verify subscription exists: `gcloud pubsub subscriptions describe sub-name` |
| ManifestWork created but resources not applied | Maestro agent not running on target | Check agent pods: `kubectl get pods -n open-cluster-management-agent` |
| `Phase preconditions: FAILED` | API returned unexpected status | Check adapter logs with `--log-level debug` to see full API response |
| Resources skipped unexpectedly | Precondition conditions evaluated to NOT MET | Review condition logic and captured field values in logs |

### Verification Quick Commands

```bash
# Check adapter is running
ps aux | grep "[a]dapter serve"

# View last 50 log lines
tail -50 /path/to/adapter.log

# Get latest status for a cluster (sorted by time)
CLUSTER_ID="abc123"
curl -s http://host.docker.internal:8000/api/hyperfleet/v1/clusters/$CLUSTER_ID/statuses | \
  jq '.items | sort_by(.updated_time // .created_time) | reverse | .[0] | {adapter, conditions: .conditions | map({type, status, reason})}'

# Check if ManifestWork was created in Maestro
curl -s "http://host.docker.internal:8100/api/maestro/v1/resources" | \
  jq '.items[] | select(.manifest.kind=="ManifestWork") | .manifest.metadata.name'

# Trigger a test event
CLUSTER_ID="test-123"
gcloud pubsub topics publish cluster-events --message="$(jq -n \
  --arg id "$CLUSTER_ID" \
  '{specversion:"1.0",id:$id,type:"io.hyperfleet.cluster.updated",source:("/api/hyperfleet/v1/clusters/"+$id),data:{id:$id,kind:"Cluster",generation:1}}')"
```

---

## Dry-Run Testing Instructions

After generating configs, offer to create dry-run mock files. The command to test:

```bash
hyperfleet-adapter serve \
  --config ./adapter-config.yaml \
  --task-config ./adapter-task-config.yaml \
  --dry-run-event ./event.json \
  --dry-run-api-responses ./api-responses.json \
  --dry-run-discovery ./discovery-overrides.json \
  --dry-run-verbose \
  --dry-run-output text
```

### Mock event.json (Cluster)

```json
{
  "specversion": "1.0",
  "id": "test-event-001",
  "type": "io.hyperfleet.cluster.updated",
  "source": "/api/hyperfleet/v1/clusters/abc123",
  "data": {
    "id": "abc123",
    "kind": "Cluster",
    "href": "/api/hyperfleet/v1/clusters/abc123",
    "generation": 5
  }
}
```

### Mock event.json (NodePool)

```json
{
  "specversion": "1.0",
  "id": "test-event-002",
  "type": "io.hyperfleet.nodepool.updated",
  "source": "/api/hyperfleet/v1/clusters/abc123/nodepools/np456",
  "data": {
    "id": "np456",
    "kind": "NodePool",
    "href": "/api/hyperfleet/v1/clusters/abc123/nodepools/np456",
    "generation": 3,
    "owned_reference": {
      "id": "abc123",
      "kind": "Cluster"
    }
  }
}
```

### Mock api-responses.json

```json
{
  "responses": [
    {
      "match": {
        "method": "GET",
        "urlPattern": "/clusters/.*"
      },
      "responses": [
        {
          "statusCode": 200,
          "body": {
            "id": "abc123",
            "name": "my-cluster",
            "generation": 5,
            "status": {
              "conditions": [
                { "type": "Ready", "status": "False" }
              ]
            }
          }
        }
      ]
    },
    {
      "match": {
        "method": "POST",
        "urlPattern": "/clusters/.*/statuses"
      },
      "responses": [
        { "statusCode": 200, "body": {} }
      ]
    }
  ]
}
```

### Mock discovery-overrides.json (Namespace example)

```json
{
  "abc123": {
    "apiVersion": "v1",
    "kind": "Namespace",
    "metadata": {
      "name": "abc123",
      "uid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "resourceVersion": "100",
      "labels": {
        "hyperfleet.io/cluster-id": "abc123",
        "hyperfleet.io/resource-type": "namespace"
      }
    },
    "status": {
      "phase": "Active"
    }
  }
}
```

### Reading the Trace Output

The dry-run produces a phase-by-phase trace showing exactly what happened. Use `--dry-run-verbose` to see rendered manifests and full API request/response bodies. Use `--dry-run-output json` for machine-readable output you can pipe into `jq`.

Example trace:

```text
Dry-Run Execution Trace
========================
Event: id=abc123 type=io.hyperfleet.cluster.updated

Phase 1: Parameter Extraction .............. SUCCESS
  clusterId        = "abc123"
  generation       = 5
  region           = "us-east-1"

Phase 2: Preconditions ..................... SUCCESS (MET)
  [1/1] fetch-cluster                      PASS
    API Call: GET /api/hyperfleet/v1/clusters/abc123 -> 200
    Captured: clusterName = "my-cluster"
    Captured: readyStatus = "False"

Phase 3: Resources ........................ SUCCESS
  [1/2] namespace0                         CREATE
    Kind: Namespace    Namespace:            Name: abc123
  [2/2] configmap0                         CREATE
    Kind: ConfigMap    Namespace: abc123     Name: abc123-config

Phase 3.5: Discovery Results ................. (available as resources.* in payload)
  namespace0:
    {"apiVersion":"v1","kind":"Namespace","metadata":{"name":"abc123",...},"status":{"phase":"Active"}}

Phase 4: Post Actions ..................... SUCCESS
  [1/1] update-status                      EXECUTED
    API Call: POST /api/hyperfleet/v1/clusters/abc123/statuses -> 200

Result: SUCCESS
```

**What to look for in the trace:**

| Phase | What to check |
|-------|---------------|
| **Phase 1** | All params extracted with expected values. Missing required params cause `FAIL`. |
| **Phase 2** | API calls return expected status codes. Captures extract the right values. Conditions evaluate to `MET` (resources will execute) or `NOT MET` (resources skipped). |
| **Phase 3** | Resources show `CREATE`, `UPDATE`, or `SKIP`. Check the rendered Kind/Namespace/Name match expectations. |
| **Phase 3.5** | Discovery results show the mock data you provided. These are what `resources.*` CEL expressions will see in Phase 4. |
| **Phase 4** | Post-actions execute. Check the status payload body contains correct condition statuses (`True`/`False`/`Unknown`) and `observed_generation` is an integer, not a string. |

### Development Loop

1. **Write** your `adapter-task-config.yaml`
2. **Create mock files** for a representative cluster state
3. **Run dry-run**, inspect the trace
4. **Fix config issues**, re-run -- iterate until the trace shows expected behavior
5. **Test edge cases** by modifying mock files:
   - Change `readyConditionStatus` to `"True"` in API response -- preconditions should evaluate to `NOT MET`, resources should be skipped
   - Remove fields from API response -- CEL optional chaining (`?.orValue()`) should handle missing data gracefully
   - Change discovery overrides to simulate pending resources (e.g., Namespace with `status.phase: "Pending"`) -- `Available` condition should report `"False"` or `"Unknown"`
   - Return error status codes (404, 500) from mock API responses -- Health condition should surface the error details
   - Test with empty `discovery-overrides.json` (`{}`) -- `Applied` condition should report `"False"` since `has(resources.xxx)` will be false
6. **Deploy** when the trace shows correct behavior for all cases

### Common Dry-Run Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `observed_generation` shows as `"5"` (string) in payload | Using Go Template `"{{ .generation }}"` | Use CEL: `expression: "generation"` |
| Capture returns empty/nil | CEL expression references a param instead of API response field | Captures can only see the API response body, not params |
| Resources phase shows `SKIP` unexpectedly | Discovery override key doesn't match the rendered resource name | Check the resource name after Go Template rendering |
| `Phase 2: NOT MET` when you expect `MET` | Condition logic is inverted or captured value doesn't match | Add `--dry-run-verbose` to see exact captured values |
| Post-action payload missing fields | CEL optional chaining not used, field doesn't exist in discovery | Use `resources.?name.?field.orValue("")` pattern |

---

## Complete Live Testing Workflow

Follow this workflow after generating adapter configs to ensure everything works end-to-end:

### Step 1: Pre-Flight Checks

Run the environment detection script (see "Pre-Flight Environment Check" section above) to verify:
- GCP project is set
- Maestro consumers exist (if using Maestro)
- HyperFleet API is accessible
- Pub/Sub subscription exists

### Step 2: Dry-Run Test

Always test with dry-run first:

```bash
hyperfleet-adapter serve \
  --config adapter-config.yaml \
  --task-config adapter-task-config.yaml \
  --dry-run-event event.json \
  --dry-run-api-responses api-responses.json \
  --dry-run-discovery discovery-overrides.json \
  --dry-run-verbose \
  --dry-run-output text
```

Verify all 4 phases succeed and status payload looks correct.

### Step 3: Create Test Data (if needed)

If testing with a real cluster that doesn't exist yet, create it:

```bash
# Example: Create test cluster in HyperFleet API
curl -X POST http://host.docker.internal:8000/api/hyperfleet/v1/clusters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-cluster-001",
    "kind": "Cluster",
    "spec": {
      "region": "us-east-1",
      "version": "4.15.0"
    }
  }'
```

### Step 4: Start Live Adapter

```bash
export BROKER_CONFIG_FILE=/path/to/broker-config.yaml

hyperfleet-adapter serve \
  -c adapter-config.yaml \
  -t adapter-task-config.yaml \
  --log-level debug
```

Watch for these log messages confirming successful startup:
- `Maestro client created successfully` (if using Maestro)
- `Successfully subscribed to topic ... subscription ...`
- `Adapter is ready to process events`

### Step 5: Trigger Test Event

```bash
CLUSTER_ID="test-cluster-001"  # Use actual cluster ID from Step 3

gcloud pubsub topics publish cluster-events --message="$(jq -n \
  --arg id "$CLUSTER_ID" \
  --arg source "/api/hyperfleet/v1/clusters/$CLUSTER_ID" \
  --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    specversion: "1.0",
    id: $id,
    type: "io.hyperfleet.cluster.updated",
    source: $source,
    time: $time,
    datacontenttype: "application/json",
    data: {
      id: $id,
      kind: "Cluster",
      href: ("/api/hyperfleet/v1/clusters/" + $id),
      generation: 1
    }
  }')"
```

### Step 6: Verify in 4 Places

**1. Adapter Logs**
Look for:

```text
Event execution finished: event_execution_status=success
```

**2. HyperFleet API Status**

```bash
curl -s http://host.docker.internal:8000/api/hyperfleet/v1/clusters/$CLUSTER_ID/statuses | \
  jq '.items | map(select(.adapter=="your-adapter-name")) | .[0] | {
    conditions: .conditions | map({type, status, reason})
  }'
```

Expected: All three conditions (Applied, Available, Health) present with appropriate statuses.

**3. Maestro Resources** (if using Maestro)

```bash
curl -s http://host.docker.internal:8100/api/maestro/v1/resources | \
  jq '.items[] | select(.manifest.metadata.name | contains("'$CLUSTER_ID'"))'
```

Expected: ManifestWork created with correct manifests.

**4. Target Cluster Resources** (if accessible)

```bash
# For Kubernetes direct transport
kubectl get ns $CLUSTER_ID
kubectl get all -n $CLUSTER_ID

# For Maestro transport (on spoke cluster)
kubectl --context spoke-cluster get ns $CLUSTER_ID
kubectl --context spoke-cluster get all -n $CLUSTER_ID
```

Expected: Resources actually exist on target cluster.

### Step 7: Test Edge Cases

Trigger multiple events to test idempotency and updates:

```bash
# Same generation - should skip
# (increment generation in event data to trigger update)

# Different generation - should update
# (change generation to 2, then trigger again)
```

### Common Issues During Live Testing

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Adapter doesn't start | Maestro config missing/wrong | Check "Common Errors" table above |
| Event not received | Subscription misconfigured | Verify with `gcloud pubsub subscriptions describe` |
| 404 from HyperFleet API | Cluster doesn't exist | Create cluster first (see Step 3) |
| ManifestWork not created | Consumer doesn't exist | List consumers, update placementClusterName |
| Resources not applied | Maestro agent down | Check agent pods on target cluster |

### Success Criteria

Your adapter is working correctly when:
- Dry-run test passes
- Adapter starts without errors
- Events are received and processed (check logs)
- Status is reported to HyperFleet API
- Resources exist in Maestro (if using Maestro)
- Resources exist on target cluster
- Re-running same event (same generation) skips resources (idempotent)
- Running with new generation updates resources
