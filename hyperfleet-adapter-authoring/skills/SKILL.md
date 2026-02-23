---
name: adapter-config-author
description: Interactive assistant for authoring HyperFleet adapter configurations (AdapterConfig + AdapterTaskConfig YAML files)
triggers:
  - adapter config
  - adapter task config
  - new adapter
  - AdapterTaskConfig
  - AdapterConfig
  - create adapter
  - write adapter
---

# HyperFleet Adapter Config Authoring Skill

You are an expert assistant for authoring HyperFleet adapter configurations. Adapters are configuration-driven YAML files — not Go code. You guide users through creating complete, correct `AdapterConfig` and `AdapterTaskConfig` files.

For detailed examples and reference material, fetch the authoring guide from: https://raw.githubusercontent.com/openshift-hyperfleet/hyperfleet-adapter/main/docs/adapter-authoring-guide.md

---

## Interactive Workflow

When the user wants to create a new adapter, walk through these questions **one at a time**, gathering answers before generating config:

### Step 1: Basic Identity

Ask the user:

- **What is the adapter name?** (e.g., `dns-manager`, `landing-zone`, `certificate-provisioner`)
- **What does it do?** (one sentence describing its purpose)

### Step 2: Resource Type

Ask the user:

- **Does this adapter manage Clusters or NodePools?**
  - **Cluster**: Events come from cluster changes, params use `event.id` for clusterId
  - **NodePool**: Events come from nodepool changes, params use `event.id` for nodepoolId and `event.owned_reference.id` for parent clusterId

### Step 3: Transport Type

Ask the user:

- **How should resources be delivered?**
  - **Kubernetes (direct)**: Resources applied directly to the management cluster via Kubernetes API
  - **Maestro**: Resources wrapped in a ManifestWork and sent to a remote spoke cluster via Maestro/OCM

**If Maestro is selected**, also ask:
- **What Maestro endpoint URLs should be used?** (default: http://host.docker.internal:8100 for HTTP, host.docker.internal:8090 for gRPC)
- Run this command to list available consumers:
  ```bash
  curl -s http://host.docker.internal:8100/api/maestro/v1/consumers | jq '.items[].name'
  ```
- **Which consumer should be used?** (e.g., "cluster1", "local-cluster")

### Step 4: Resources to Create

Ask the user:

- **What Kubernetes resources should this adapter create?** (e.g., Namespace, ConfigMap, Job, Deployment, CRD instance, Secret)
- **Should manifests be inline or external file references?**
  - Inline: Small manifests embedded directly in the task config
  - External ref: Larger manifests stored in separate files mounted via ConfigMap

### Step 5: Dependencies

Ask the user:

- **Does this adapter depend on another adapter completing first?** (e.g., wait for `landing-zone` namespace to be Active)
- If yes: **Which adapter and what condition should be checked?**

### Step 6: Additional Parameters

Ask the user:

- **Does this adapter need any environment variables beyond the standard ones?** (e.g., REGION, NAMESPACE, SERVICE_ACCOUNT)

### Step 7: Generate

Generate both files:

1. `adapter-config.yaml` — deployment configuration
2. `adapter-task-config.yaml` — business logic configuration

Offer to also generate dry-run mock files (event.json, api-responses.json, discovery-overrides.json) for local testing.

---

## Configuration Schema Reference

### AdapterConfig Structure

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterConfig
metadata:
  name: <adapter-name>
  labels:
    hyperfleet.io/adapter-type: <adapter-name>
    hyperfleet.io/component: adapter
spec:
  adapter:
    version: "0.1.0"
  debugConfig: false           # Log full merged config at startup
  log:
    level: info                # debug, info, warn, error
  clients:
    hyperfleetApi:
      baseUrl: http://hyperfleet-api:8000
      version: v1
      timeout: 2s
      retryAttempts: 3
      retryBackoff: exponential  # linear, constant, exponential
    broker:
      subscriptionId: "<adapter-name>-sub"
      topic: "cluster-events"    # or "nodepool-events"
    kubernetes:
      apiVersion: "v1"
      # kubeConfigPath: ""      # For local dev only
    # maestro:                  # Only if using Maestro transport
    #   httpServerAddress: http://host.docker.internal:8100   # REQUIRED: Maestro HTTP endpoint
    #   grpcServerAddress: host.docker.internal:8090          # REQUIRED: Maestro gRPC endpoint
    #   sourceId: <adapter-name>                              # REQUIRED: Must match adapter name
    #   timeout: 30s                                          # Optional: default 30s
    #   insecure: true                                        # Optional: for dev environments without TLS
```

### AdapterTaskConfig Structure

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterTaskConfig
metadata:
  name: <adapter-name>
  labels:
    hyperfleet.io/adapter-type: <adapter-name>
    hyperfleet.io/component: adapter
spec:
  params: []           # Phase 1: Extract variables
  preconditions: []    # Phase 2: Validate state
  resources: []        # Phase 3: Create K8s resources
  post:                # Phase 4: Report status
    payloads: []
    postActions: []
```

### Parameter Sources

| Prefix | Source | Example |
|--------|--------|---------|
| `event.` | CloudEvent data fields | `event.id`, `event.generation`, `event.kind` |
| `event.owned_reference.` | Parent resource (NodePools) | `event.owned_reference.id` |
| `env.` | Environment variables | `env.REGION`, `env.NAMESPACE` |
| `secret.` | Kubernetes Secret | `secret.my-ns.my-secret.api-key` |
| `configmap.` | Kubernetes ConfigMap | `configmap.my-ns.my-config.setting` |

### Parameter Types

| Type | Accepts |
|------|---------|
| `string` | Any value (default) |
| `int`, `int64` | Integers, numeric strings |
| `float`, `float64` | Numeric values |
| `bool` | `true/false`, `yes/no`, `on/off`, `1/0` |

### Precondition Operators

| Operator | Description |
|----------|-------------|
| `equals` | Exact match |
| `notEquals` | Not equal |
| `in` | Value is in array |
| `notIn` | Value is not in array |
| `contains` | String contains substring |
| `greaterThan` | Numeric greater than |
| `lessThan` | Numeric less than |
| `greaterThanOrEqual` | Numeric >= |
| `lessThanOrEqual` | Numeric <= |
| `exists` | Field exists (no value needed) |
| `notExists` | Field does not exist |

### Capture Modes

Two modes available — use one per capture, **never both**:

- **`field`**: Simple field extraction using dot notation or JSONPath

  ```yaml
  - name: "clusterName"
    field: "name"
  - name: "lzStatus"
    field: "{.items[?(@.adapter=='landing-zone')].data.namespace.status}"
  ```

- **`expression`**: CEL expression for computed values

  ```yaml
  - name: "readyStatus"
    expression: |
      status.conditions.filter(c, c.type == "Ready").size() > 0
        ? status.conditions.filter(c, c.type == "Ready")[0].status
        : "False"
  ```

### Discovery Modes

Two modes — **mutually exclusive**:

- **`byName`**: Direct lookup by rendered name

  ```yaml
  discovery:
    byName: "{{ .clusterId | lower }}"
  ```

- **`bySelectors`**: Label selector lookup

  ```yaml
  discovery:
    namespace: "{{ .clusterId }}"   # omit or "*" for cluster-scoped
    bySelectors:
      labelSelector:
        hyperfleet.io/cluster-id: "{{ .clusterId }}"
        hyperfleet.io/resource-type: "namespace"
  ```

### Transport Types

- **Kubernetes direct**:

  ```yaml
  transport:
    client: "kubernetes"
  ```

- **Maestro** (remote cluster via ManifestWork):

  ```yaml
  transport:
    client: "maestro"
    maestro:
      targetCluster: "{{ .placementClusterName }}"
  ```

### Labeling Conventions

Always label resources for discovery and traceability:

| Label | Purpose |
|-------|---------|
| `hyperfleet.io/cluster-id` | Associate resource with a cluster |
| `hyperfleet.io/managed-by` | Adapter that owns this resource |
| `hyperfleet.io/resource-type` | Resource category for discovery |
| `hyperfleet.io/nodepool-id` | Associate with a nodepool (if applicable) |
| `hyperfleet.io/generation` | Generation that created/updated this (use as annotation) |

### Post-Action Payload Field Forms

| Form | Example | Use when |
|------|---------|----------|
| Direct string | `adapter: "my-adapter"` | Static values |
| Go Template | `adapter: "{{ .metadata.name }}"` | Dynamic string interpolation |
| CEL expression | `status: { expression: "..." }` | Computed values, conditionals |
| Field extraction | `status: { field: "path", default: "..." }` | Simple field reads |

### Condition Types

Every adapter status reports three conditions:

| Type | Question it answers |
|------|---------------------|
| **Applied** | Were the Kubernetes resources created/configured? |
| **Available** | Are the resources operational and serving? |
| **Health** | Did the adapter execution itself succeed? |

Possible status values: `"True"`, `"False"`, `"Unknown"`

### Resource Lifecycle Operations

| Operation | When | Behavior |
|-----------|------|----------|
| `create` | Resource doesn't exist | Apply the manifest |
| `update` | Resource exists, generation changed | Patch the resource |
| `skip` | Resource exists, generation unchanged | No-op (idempotent) |
| `recreate` | `recreateOnChange: true` is set | Delete then create |

---

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

## Critical Gotchas

**ALWAYS apply these rules when generating configs:**

1. **`observed_generation` MUST use CEL expression, not Go Template.**
   Go Templates output strings, but the API expects an integer. CEL preserves the numeric type.

   ```yaml
   # CORRECT
   observed_generation:
     expression: "generation"

   # WRONG — sends string "5" instead of integer 5
   observed_generation: "{{ .generation }}"
   ```

2. **Capture scope can only see the API response, not params.**
   Capture expressions operate on the raw API response body. They cannot reference params or other captured values.

3. **Condition scope sees the full context.**
   Conditions (both structured and CEL expression) can access all params, all captured fields, and the full API response via the precondition name (e.g., `clusterStatus.status.conditions`).

4. **Resource names must be lowercase, no hyphens** (CEL-compatible identifiers).
   Use camelCase or underscores: `clusterNamespace`, `job_role` — not `cluster-namespace`.

5. **`byName` vs `bySelectors` are mutually exclusive** in discovery config.

6. **`field` vs `expression` are mutually exclusive** in captures.

7. **Post-actions always execute**, even when preconditions are not met or resources fail. Design your status payload CEL expressions to handle all cases (success, skip, error).

8. **Use optional chaining** (`?.` and `.orValue()`) in CEL expressions for safe access to fields that may not exist:

   ```cel
   resources.?clusterNamespace.?status.?phase.orValue("")
   ```

9. **Register the adapter name** in `HYPERFLEET_CLUSTER_ADAPTERS` (or `HYPERFLEET_NODEPOOL_ADAPTERS`) env var on the API. Without this, the adapter won't participate in status aggregation.

10. **URLs in apiCall are relative** — the base URL comes from AdapterConfig's `clients.hyperfleetApi.baseUrl`. Only write the path (e.g., `/clusters/{{ .clusterId }}`).

11. **Status reporting uses `POST`, not `PATCH` or `PUT`.**
    The HyperFleet statuses endpoint only accepts `POST`. Using any other method returns `405 Method Not Allowed`.

    ```yaml
    # CORRECT
    postActions:
      - name: "updateStatus"
        apiCall:
          method: "POST"
          url: "/api/hyperfleet/v1/clusters/{{ .clusterId }}/statuses"

    # WRONG — 405 Method Not Allowed
          method: "PATCH"
    ```

12. **Maestro: `bySelectors` discovery may not see `Applied=True` immediately after ManifestWork creation.**
    `byName` uses a direct `GetManifestWork` gRPC call and typically returns status conditions within milliseconds of the Maestro agent acknowledging the work. `bySelectors` uses `ListManifestWorks` and filters in-memory — the list snapshot may not yet include the agent's status update.
    - If you need `Applied=True` in the same adapter execution cycle, use `byName`.
    - If `bySelectors` is required (e.g., to test label-based lookup), design the CEL expressions to handle `Applied=False` gracefully. The Sentinel will re-trigger and the second event (same generation → `OperationSkip` + re-discovery) will see the updated status.

13. **Maestro ManifestWork: `hyperfleet.io/generation` annotation is required on the ManifestWork AND on every nested manifest inside `spec.workload.manifests`.**
    The framework validates both levels. Missing the annotation on any nested manifest causes the apply to fail.

    ```yaml
    metadata:
      annotations:
        hyperfleet.io/generation: "{{ .generation }}"   # on ManifestWork
    spec:
      workload:
        manifests:
          - apiVersion: v1
            kind: Namespace
            metadata:
              annotations:
                hyperfleet.io/generation: "{{ .generation }}"  # also on each manifest
    ```

14. **Precondition skip via existing adapter status count — preferred over checking `Ready` condition.**
    The `Ready` condition on a cluster is managed internally by HyperFleet and cannot be set via the API. To implement a "skip if already processed" pattern (e.g., for one-shot adapters), capture the count of existing adapter statuses and skip if non-zero:

    ```yaml
    preconditions:
      - name: "fetchAdapterStatuses"
        apiCall:
          method: "GET"
          url: "/api/hyperfleet/v1/clusters/{{ .clusterId }}/statuses"
        capture:
          - name: "existingStatusCount"
            expression: "items.size()"
        conditions:
          - field: "existingStatusCount"
            operator: "equals"
            value: "0"
    ```

    To test the skip path in integration tests, pre-POST a dummy adapter status before publishing the CloudEvent so `existingStatusCount` will be 1 when the adapter checks.

15. **Maestro configuration must use specific field names.**
    The AdapterConfig `maestro` section requires exact field names. Common mistakes:

    ```yaml
    # WRONG - these field names don't work
    maestro:
      baseUrl: http://maestro:8000
      grpcUrl: maestro:8090

    # CORRECT - use these exact field names
    maestro:
      httpServerAddress: http://host.docker.internal:8100
      grpcServerAddress: host.docker.internal:8090
      sourceId: my-adapter-name  # REQUIRED
      timeout: 30s
      insecure: true
    ```

16. **Maestro consumer must exist before creating ManifestWorks.**
    The `placementClusterName` in your task config must match an existing consumer registered in Maestro. If you get a foreign key constraint error like `fk_resources_consumers`, the consumer doesn't exist.

    List available consumers:
    ```bash
    curl -s http://host.docker.internal:8100/api/maestro/v1/consumers | jq '.items[].name'
    ```

    Update your placementClusterName capture to match:
    ```yaml
    - name: "placementClusterName"
      expression: "\"cluster1\""  # Must be an existing Maestro consumer
    ```

---

## Standard Health Condition Boilerplate

**Copy this exactly into every adapter's Health condition. Do not modify it.**

```yaml
- type: "Health"
  status:
    expression: |
      adapter.?executionStatus.orValue("") == "success"
        && !adapter.?resourcesSkipped.orValue(false)
      ? "True"
      : "False"
  reason:
    expression: |
      adapter.?executionStatus.orValue("") != "success"
      ? "ExecutionFailed:" + adapter.?executionError.?phase.orValue("unknown")
      : adapter.?resourcesSkipped.orValue(false)
        ? "ResourcesSkipped"
        : "Healthy"
  message:
    expression: |
      adapter.?executionStatus.orValue("") != "success"
      ? "Adapter failed at phase ["
          + adapter.?executionError.?phase.orValue("unknown")
          + "] step ["
          + adapter.?executionError.?step.orValue("unknown")
          + "]: "
          + adapter.?executionError.?message.orValue(
              adapter.?errorMessage.orValue("no details"))
      : adapter.?resourcesSkipped.orValue(false)
        ? "Resources skipped: " + adapter.?skipReason.orValue("unknown reason")
        : "Adapter execution completed successfully"
```

---

## Templates for Common Patterns

### Template 1: Kubernetes Cluster Adapter (Namespace + ConfigMap)

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterTaskConfig
metadata:
  name: ADAPTER_NAME
  labels:
    hyperfleet.io/adapter-type: ADAPTER_NAME
    hyperfleet.io/component: adapter
spec:
  params:
    - name: "clusterId"
      source: "event.id"
      type: "string"
      required: true
    - name: "generation"
      source: "event.generation"
      type: "int"
      required: true

  preconditions:
    - name: "clusterStatus"
      apiCall:
        method: "GET"
        url: "/clusters/{{ .clusterId }}"
        timeout: 10s
        retryAttempts: 3
        retryBackoff: "exponential"
      capture:
        - name: "clusterName"
          field: "name"
        - name: "generation"
          field: "generation"
        - name: "readyConditionStatus"
          expression: |
            status.conditions.filter(c, c.type == "Ready").size() > 0
              ? status.conditions.filter(c, c.type == "Ready")[0].status
              : "False"
      conditions:
        - field: "readyConditionStatus"
          operator: "equals"
          value: "False"

  resources:
    - name: "clusterNamespace"
      transport:
        client: "kubernetes"
      manifest:
        apiVersion: v1
        kind: Namespace
        metadata:
          name: "{{ .clusterId | lower }}"
          labels:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/managed-by: "{{ .metadata.name }}"
            hyperfleet.io/resource-type: "namespace"
          annotations:
            hyperfleet.io/generation: "{{ .generation }}"
      discovery:
        byName: "{{ .clusterId | lower }}"

    - name: "clusterConfigMap"
      transport:
        client: "kubernetes"
      manifest:
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: "{{ .clusterId }}-config"
          namespace: "{{ .clusterId | lower }}"
          labels:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/managed-by: "{{ .metadata.name }}"
            hyperfleet.io/resource-type: "configmap"
        data:
          cluster_id: "{{ .clusterId }}"
          cluster_name: "{{ .clusterName }}"
      discovery:
        namespace: "{{ .clusterId | lower }}"
        bySelectors:
          labelSelector:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/resource-type: "configmap"

  post:
    payloads:
      - name: "clusterStatusPayload"
        build:
          adapter: "{{ .metadata.name }}"
          conditions:
            - type: "Applied"
              status:
                expression: |
                  has(resources.clusterNamespace) ? "True" : "False"
              reason:
                expression: |
                  has(resources.clusterNamespace) ? "Applied" : "Pending"
              message:
                expression: |
                  has(resources.clusterNamespace)
                    ? "Resources applied successfully"
                    : "Resources pending"
            - type: "Available"
              status:
                expression: |
                  resources.?clusterNamespace.?status.?phase.orValue("") == "Active"
                    ? "True" : "False"
              reason:
                expression: |
                  resources.?clusterNamespace.?status.?phase.orValue("") == "Active"
                    ? "NamespaceReady" : "NamespaceNotReady"
              message:
                expression: |
                  resources.?clusterNamespace.?status.?phase.orValue("") == "Active"
                    ? "Namespace is active" : "Namespace not yet active"
            - type: "Health"
              status:
                expression: |
                  adapter.?executionStatus.orValue("") == "success"
                    && !adapter.?resourcesSkipped.orValue(false)
                  ? "True"
                  : "False"
              reason:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "ExecutionFailed:" + adapter.?executionError.?phase.orValue("unknown")
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "ResourcesSkipped"
                    : "Healthy"
              message:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "Adapter failed at phase ["
                      + adapter.?executionError.?phase.orValue("unknown")
                      + "] step ["
                      + adapter.?executionError.?step.orValue("unknown")
                      + "]: "
                      + adapter.?executionError.?message.orValue(
                          adapter.?errorMessage.orValue("no details"))
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "Resources skipped: " + adapter.?skipReason.orValue("unknown reason")
                    : "Adapter execution completed successfully"
          observed_generation:
            expression: "generation"
          observed_time: "{{ now | date \"2006-01-02T15:04:05Z07:00\" }}"
          data:
            namespace:
              name:
                expression: |
                  resources.?clusterNamespace.?metadata.?name.orValue("")
              phase:
                expression: |
                  resources.?clusterNamespace.?status.?phase.orValue("")

    postActions:
      - name: "reportClusterStatus"
        apiCall:
          method: "POST"
          url: "/clusters/{{ .clusterId }}/statuses"
          headers:
            - name: "Content-Type"
              value: "application/json"
          body: "{{ .clusterStatusPayload }}"
```

### Template 2: Maestro Cluster Adapter (ManifestWork)

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterTaskConfig
metadata:
  name: ADAPTER_NAME
  labels:
    hyperfleet.io/adapter-type: ADAPTER_NAME
    hyperfleet.io/component: adapter
spec:
  params:
    - name: "clusterId"
      source: "event.id"
      type: "string"
      required: true
    - name: "generation"
      source: "event.generation"
      type: "int"
      required: true

  preconditions:
    - name: "clusterStatus"
      apiCall:
        method: "GET"
        url: "/clusters/{{ .clusterId }}"
        timeout: 10s
        retryAttempts: 3
        retryBackoff: "exponential"
      capture:
        - name: "clusterName"
          field: "name"
        - name: "generation"
          field: "generation"
        - name: "placementClusterName"
          expression: "\"cluster1\""  # IMPORTANT: Must match an existing Maestro consumer
          # To find available consumers: curl http://host.docker.internal:8100/api/maestro/v1/consumers | jq '.items[].name'
          # Or use dynamic placement: has(spec.placement.cluster) ? spec.placement.cluster : "cluster1"
        - name: "readyConditionStatus"
          expression: |
            status.conditions.filter(c, c.type == "Ready").size() > 0
              ? status.conditions.filter(c, c.type == "Ready")[0].status
              : "False"
      conditions:
        - field: "readyConditionStatus"
          operator: "equals"
          value: "False"

  resources:
    - name: "clusterManifestWork"
      transport:
        client: "maestro"
        maestro:
          targetCluster: "{{ .placementClusterName }}"
      manifest:
        apiVersion: work.open-cluster-management.io/v1
        kind: ManifestWork
        metadata:
          name: "{{ .clusterId }}"
          labels:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/managed-by: "{{ .metadata.name }}"
          annotations:
            hyperfleet.io/generation: "{{ .generation }}"   # required on ManifestWork
        spec:
          workload:
            manifests:
              - apiVersion: v1
                kind: Namespace
                metadata:
                  name: "{{ .clusterId | lower }}"
                  labels:
                    hyperfleet.io/cluster-id: "{{ .clusterId }}"
                    hyperfleet.io/resource-type: "namespace"
                  annotations:
                    hyperfleet.io/generation: "{{ .generation }}"  # required on each manifest
              - apiVersion: v1
                kind: ConfigMap
                metadata:
                  name: "{{ .clusterId }}-config"
                  namespace: "{{ .clusterId | lower }}"
                  labels:
                    hyperfleet.io/cluster-id: "{{ .clusterId }}"
                    hyperfleet.io/resource-type: "configmap"
                  annotations:
                    hyperfleet.io/generation: "{{ .generation }}"  # required on each manifest
                data:
                  cluster_id: "{{ .clusterId }}"
          manifestConfigs:
            - resourceIdentifier:
                group: ""
                resource: "namespaces"
                name: "{{ .clusterId | lower }}"
              updateStrategy:
                type: "ServerSideApply"
              feedbackRules:
                - type: "JSONPaths"
                  jsonPaths:
                    - name: "phase"
                      path: ".status.phase"
      discovery:
        byName: "{{ .clusterId }}"
      nestedDiscoveries:
        - name: "mgmtNamespace"
          discovery:
            bySelectors:
              labelSelector:
                hyperfleet.io/resource-type: "namespace"
                hyperfleet.io/cluster-id: "{{ .clusterId }}"
        - name: "mgmtConfigMap"
          discovery:
            byName: "{{ .clusterId }}-config"

  post:
    payloads:
      - name: "clusterStatusPayload"
        build:
          adapter: "{{ .metadata.name }}"
          conditions:
            - type: "Applied"
              status:
                expression: |
                  has(resources.clusterManifestWork) ? "True" : "False"
              reason:
                expression: |
                  has(resources.clusterManifestWork) ? "ManifestWorkApplied" : "ManifestWorkPending"
              message:
                expression: |
                  has(resources.clusterManifestWork)
                    ? "ManifestWork applied successfully"
                    : "ManifestWork pending"
            - type: "Available"
              status:
                expression: |
                  resources.?clusterManifestWork.?status.?conditions.orValue([])
                    .filter(c, c.type == "Available").size() > 0
                  ? resources.clusterManifestWork.status.conditions
                      .filter(c, c.type == "Available")[0].status
                  : "Unknown"
              reason:
                expression: |
                  resources.?clusterManifestWork.?status.?conditions.orValue([])
                    .filter(c, c.type == "Available").size() > 0
                  ? resources.clusterManifestWork.status.conditions
                      .filter(c, c.type == "Available")[0].reason
                  : "ManifestWorkNotReady"
              message:
                expression: |
                  resources.?clusterManifestWork.?status.?conditions.orValue([])
                    .filter(c, c.type == "Available").size() > 0
                  ? resources.clusterManifestWork.status.conditions
                      .filter(c, c.type == "Available")[0].message
                  : "ManifestWork not yet available"
            - type: "Health"
              status:
                expression: |
                  adapter.?executionStatus.orValue("") == "success"
                    && !adapter.?resourcesSkipped.orValue(false)
                  ? "True"
                  : "False"
              reason:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "ExecutionFailed:" + adapter.?executionError.?phase.orValue("unknown")
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "ResourcesSkipped"
                    : "Healthy"
              message:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "Adapter failed at phase ["
                      + adapter.?executionError.?phase.orValue("unknown")
                      + "] step ["
                      + adapter.?executionError.?step.orValue("unknown")
                      + "]: "
                      + adapter.?executionError.?message.orValue(
                          adapter.?errorMessage.orValue("no details"))
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "Resources skipped: " + adapter.?skipReason.orValue("unknown reason")
                    : "Adapter execution completed successfully"
          observed_generation:
            expression: "generation"
          observed_time: "{{ now | date \"2006-01-02T15:04:05Z07:00\" }}"

    postActions:
      - name: "reportClusterStatus"
        apiCall:
          method: "POST"
          url: "/clusters/{{ .clusterId }}/statuses"
          headers:
            - name: "Content-Type"
              value: "application/json"
          body: "{{ .clusterStatusPayload }}"
```

### Template 3: NodePool Adapter (with parent cluster readiness check)

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterTaskConfig
metadata:
  name: ADAPTER_NAME
  labels:
    hyperfleet.io/adapter-type: ADAPTER_NAME
    hyperfleet.io/component: adapter
spec:
  params:
    - name: "clusterId"
      source: "event.owned_reference.id"
      type: "string"
      required: true
    - name: "nodepoolId"
      source: "event.id"
      type: "string"
      required: true

  preconditions:
    - name: "nodepoolStatus"
      apiCall:
        method: "GET"
        url: "/clusters/{{ .clusterId }}/nodepools/{{ .nodepoolId }}"
        timeout: 10s
        retryAttempts: 3
        retryBackoff: "exponential"
      capture:
        - name: "nodepoolName"
          field: "name"
        - name: "generation"
          field: "generation"
        - name: "readyConditionStatus"
          expression: |
            status.conditions.filter(c, c.type == "Ready").size() > 0
              ? status.conditions.filter(c, c.type == "Ready")[0].status
              : "False"
      conditions:
        - field: "readyConditionStatus"
          operator: "equals"
          value: "False"

    - name: "clusterAdapterStatus"
      apiCall:
        method: "GET"
        url: "/clusters/{{ .clusterId }}/statuses"
        timeout: 10s
        retryAttempts: 3
        retryBackoff: "exponential"
      capture:
        - name: "clusterNamespaceStatus"
          field: "{.items[?(@.adapter=='landing-zone')].data.namespace.status}"
      conditions:
        - field: "clusterNamespaceStatus"
          operator: "equals"
          value: "Active"

  resources:
    - name: "nodepoolConfigMap"
      transport:
        client: "kubernetes"
      manifest:
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: "{{ .nodepoolId }}-config"
          namespace: "{{ .clusterId | lower }}"
          labels:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/nodepool-id: "{{ .nodepoolId }}"
            hyperfleet.io/managed-by: "{{ .metadata.name }}"
            hyperfleet.io/resource-type: "configmap"
        data:
          nodepool_id: "{{ .nodepoolId }}"
          nodepool_name: "{{ .nodepoolName }}"
          cluster_id: "{{ .clusterId }}"
      discovery:
        namespace: "{{ .clusterId | lower }}"
        bySelectors:
          labelSelector:
            hyperfleet.io/cluster-id: "{{ .clusterId }}"
            hyperfleet.io/nodepool-id: "{{ .nodepoolId }}"
            hyperfleet.io/resource-type: "configmap"

  post:
    payloads:
      - name: "nodepoolStatusPayload"
        build:
          adapter: "{{ .metadata.name }}"
          conditions:
            - type: "Applied"
              status:
                expression: |
                  has(resources.nodepoolConfigMap) ? "True" : "False"
              reason:
                expression: |
                  has(resources.nodepoolConfigMap) ? "ConfigMapApplied" : "ConfigMapPending"
              message:
                expression: |
                  has(resources.nodepoolConfigMap)
                    ? "ConfigMap applied successfully"
                    : "ConfigMap pending"
            - type: "Available"
              status:
                expression: |
                  has(resources.nodepoolConfigMap) && has(resources.nodepoolConfigMap.data)
                    ? "True" : "False"
              reason:
                expression: |
                  has(resources.nodepoolConfigMap) && has(resources.nodepoolConfigMap.data)
                    ? "ConfigMapReady" : "ConfigMapNotReady"
              message:
                expression: |
                  has(resources.nodepoolConfigMap) && has(resources.nodepoolConfigMap.data)
                    ? "ConfigMap is available" : "ConfigMap not yet available"
            - type: "Health"
              status:
                expression: |
                  adapter.?executionStatus.orValue("") == "success"
                    && !adapter.?resourcesSkipped.orValue(false)
                  ? "True"
                  : "False"
              reason:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "ExecutionFailed:" + adapter.?executionError.?phase.orValue("unknown")
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "ResourcesSkipped"
                    : "Healthy"
              message:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "Adapter failed at phase ["
                      + adapter.?executionError.?phase.orValue("unknown")
                      + "] step ["
                      + adapter.?executionError.?step.orValue("unknown")
                      + "]: "
                      + adapter.?executionError.?message.orValue(
                          adapter.?errorMessage.orValue("no details"))
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "Resources skipped: " + adapter.?skipReason.orValue("unknown reason")
                    : "Adapter execution completed successfully"
          observed_generation:
            expression: "generation"
          observed_time: "{{ now | date \"2006-01-02T15:04:05Z07:00\" }}"

    postActions:
      - name: "reportNodepoolStatus"
        apiCall:
          method: "POST"
          url: "/clusters/{{ .clusterId }}/nodepools/{{ .nodepoolId }}/statuses"
          headers:
            - name: "Content-Type"
              value: "application/json"
          body: "{{ .nodepoolStatusPayload }}"
```

### Template 4: No-Op / Validation Adapter

Use when you only need preconditions and status reporting, with no resource creation:

```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterTaskConfig
metadata:
  name: ADAPTER_NAME
  labels:
    hyperfleet.io/adapter-type: ADAPTER_NAME
    hyperfleet.io/component: adapter
spec:
  params:
    - name: "clusterId"
      source: "event.id"
      type: "string"
      required: true
    - name: "generation"
      source: "event.generation"
      type: "int"
      required: true

  preconditions:
    - name: "clusterStatus"
      apiCall:
        method: "GET"
        url: "/clusters/{{ .clusterId }}"
        timeout: 10s
        retryAttempts: 3
        retryBackoff: "exponential"
      capture:
        - name: "generation"
          field: "generation"
        - name: "readyConditionStatus"
          expression: |
            status.conditions.filter(c, c.type == "Ready").size() > 0
              ? status.conditions.filter(c, c.type == "Ready")[0].status
              : "False"
      conditions:
        - field: "readyConditionStatus"
          operator: "equals"
          value: "False"

  resources: []

  post:
    payloads:
      - name: "clusterStatusPayload"
        build:
          adapter: "{{ .metadata.name }}"
          conditions:
            - type: "Applied"
              status:
                expression: |
                  "True"
              reason:
                expression: |
                  "NoResourcesNeeded"
              message:
                expression: |
                  "No-op adapter: no resources to apply"
            - type: "Available"
              status:
                expression: |
                  "True"
              reason:
                expression: |
                  "ValidationPassed"
              message:
                expression: |
                  "Validation completed successfully"
            - type: "Health"
              status:
                expression: |
                  adapter.?executionStatus.orValue("") == "success"
                    && !adapter.?resourcesSkipped.orValue(false)
                  ? "True"
                  : "False"
              reason:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "ExecutionFailed:" + adapter.?executionError.?phase.orValue("unknown")
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "ResourcesSkipped"
                    : "Healthy"
              message:
                expression: |
                  adapter.?executionStatus.orValue("") != "success"
                  ? "Adapter failed at phase ["
                      + adapter.?executionError.?phase.orValue("unknown")
                      + "] step ["
                      + adapter.?executionError.?step.orValue("unknown")
                      + "]: "
                      + adapter.?executionError.?message.orValue(
                          adapter.?errorMessage.orValue("no details"))
                  : adapter.?resourcesSkipped.orValue(false)
                    ? "Resources skipped: " + adapter.?skipReason.orValue("unknown reason")
                    : "Adapter execution completed successfully"
          observed_generation:
            expression: "generation"
          observed_time: "{{ now | date \"2006-01-02T15:04:05Z07:00\" }}"

    postActions:
      - name: "reportClusterStatus"
        apiCall:
          method: "POST"
          url: "/clusters/{{ .clusterId }}/statuses"
          headers:
            - name: "Content-Type"
              value: "application/json"
          body: "{{ .clusterStatusPayload }}"
```

### Template: AdapterConfig (use with any of the above)

**For Kubernetes direct transport:**
```yaml
apiVersion: hyperfleet.redhat.com/v1alpha1
kind: AdapterConfig
metadata:
  name: ADAPTER_NAME
  labels:
    hyperfleet.io/adapter-type: ADAPTER_NAME
    hyperfleet.io/component: adapter
spec:
  adapter:
    version: "0.1.0"
  debugConfig: false
  log:
    level: info
  clients:
    hyperfleetApi:
      baseUrl: http://host.docker.internal:8000
      version: v1
      timeout: 2s
      retryAttempts: 3
      retryBackoff: exponential
    broker:
      subscriptionId: "ADAPTER_NAME-sub"
      topic: "cluster-events"
    kubernetes:
      apiVersion: "v1"
```

**For Maestro transport (add this to clients section):**
```yaml
  clients:
    hyperfleetApi:
      baseUrl: http://host.docker.internal:8000
      version: v1
      timeout: 2s
      retryAttempts: 3
      retryBackoff: exponential
    broker:
      subscriptionId: "ADAPTER_NAME-sub"
      topic: "cluster-events"
    kubernetes:
      apiVersion: "v1"
    maestro:
      httpServerAddress: http://host.docker.internal:8100
      grpcServerAddress: host.docker.internal:8090
      sourceId: ADAPTER_NAME  # Must match adapter name
      timeout: 30s
      insecure: true  # For dev environments
```

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
| `HyperFleet API response: 400 Bad Request` | Payload shape wrong — check method/body |
| `HyperFleet API response: 405 Method Not Allowed` | Wrong HTTP method — statuses endpoint requires `POST` |

An error in any phase sets `adapter.executionStatus=failed` but post-actions **always** run.

### Verify results

```bash
CLUSTER_ID="abc123"

# Check status reported to HyperFleet
curl -s "http://localhost:8000/api/hyperfleet/v1/clusters/$CLUSTER_ID/statuses" | jq .

# Check Kubernetes resource (direct transport)
kubectl get ns "hf-$CLUSTER_ID"
kubectl get all -n "hf-$CLUSTER_ID"

# Check ManifestWork applied on spoke cluster (Maestro transport)
kubectl --context "$GKE_CONTEXT" get appliedmanifestworks
kubectl --context "$GKE_CONTEXT" get ns "hf-$CLUSTER_ID"
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

If `observed_generation` appears as a quoted string (`"1"`) instead of an integer, your payload config is using `"{{ .generation }}"` — fix it to `expression: "generation"`.

### Common Errors & Solutions

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

```
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
4. **Fix config issues**, re-run — iterate until the trace shows expected behavior
5. **Test edge cases** by modifying mock files:
   - Change `readyConditionStatus` to `"True"` in API response — preconditions should evaluate to `NOT MET`, resources should be skipped
   - Remove fields from API response — CEL optional chaining (`?.orValue()`) should handle missing data gracefully
   - Change discovery overrides to simulate pending resources (e.g., Namespace with `status.phase: "Pending"`) — `Available` condition should report `"False"` or `"Unknown"`
   - Return error status codes (404, 500) from mock API responses — Health condition should surface the error details
   - Test with empty `discovery-overrides.json` (`{}`) — `Applied` condition should report `"False"` since `has(resources.xxx)` will be false
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

## CEL Quick Reference

```cel
# Optional chaining — safe access to fields that may not exist
resources.?clusterNamespace.?status.?phase.orValue("")

# Existence check
has(resources.clusterNamespace)

# Array filtering
status.conditions.filter(c, c.type == "Ready")

# Array existence check
status.conditions.exists(c, c.type == "Ready" && c.status == "True")

# Get first matching element with fallback
status.conditions.filter(c, c.type == "Ready").size() > 0
  ? status.conditions.filter(c, c.type == "Ready")[0].status
  : "False"

# Ternary
condition ? "yes" : "no"

# String concatenation
"prefix-" + clusterId + "-suffix"
```

## Go Template Quick Reference

```
{{ .variableName }}                              Variable interpolation
{{ .clusterId | lower }}                         Lowercase filter
{{ now | date "2006-01-02T15:04:05Z07:00" }}     Current timestamp (RFC 3339)
{{ .metadata.name }}                             Adapter name from config metadata
```

---

## Complete Live Testing Workflow

Follow this workflow after generating adapter configs to ensure everything works end-to-end:

### Step 1: Pre-Flight Checks

Run the environment detection script (see "Pre-Flight Environment Check" section) to verify:
- ✅ GCP project is set
- ✅ Maestro consumers exist (if using Maestro)
- ✅ HyperFleet API is accessible
- ✅ Pub/Sub subscription exists

### Step 2: Dry-Run Test

Always test with dry-run first:

```bash
/adapter serve \
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

/adapter serve \
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
```
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
- ✅ Dry-run test passes
- ✅ Adapter starts without errors
- ✅ Events are received and processed (check logs)
- ✅ Status is reported to HyperFleet API
- ✅ Resources exist in Maestro (if using Maestro)
- ✅ Resources exist on target cluster
- ✅ Re-running same event (same generation) skips resources (idempotent)
- ✅ Running with new generation updates resources
