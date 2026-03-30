# Configuration Schema Reference

## AdapterConfig Structure

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

## AdapterTaskConfig Structure

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

## Parameter Sources

| Prefix | Source | Example |
|--------|--------|---------|
| `event.` | CloudEvent data fields | `event.id`, `event.generation`, `event.kind` |
| `event.owned_reference.` | Parent resource (NodePools) | `event.owned_reference.id` |
| `env.` | Environment variables | `env.REGION`, `env.NAMESPACE` |
| `secret.` | Kubernetes Secret | `secret.my-ns.my-secret.api-key` |
| `configmap.` | Kubernetes ConfigMap | `configmap.my-ns.my-config.setting` |

## Parameter Types

| Type | Accepts |
|------|---------|
| `string` | Any value (default) |
| `int`, `int64` | Integers, numeric strings |
| `float`, `float64` | Numeric values |
| `bool` | `true/false`, `yes/no`, `on/off`, `1/0` |

## Precondition Operators

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

## Capture Modes

Two modes available -- use one per capture, **never both**:

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

## Discovery Modes

Two modes -- **mutually exclusive**:

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

## Transport Types

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

## Labeling Conventions

Always label resources for discovery and traceability:

| Label | Purpose |
|-------|---------|
| `hyperfleet.io/cluster-id` | Associate resource with a cluster |
| `hyperfleet.io/managed-by` | Adapter that owns this resource |
| `hyperfleet.io/resource-type` | Resource category for discovery |
| `hyperfleet.io/nodepool-id` | Associate with a nodepool (if applicable) |
| `hyperfleet.io/generation` | Generation that created/updated this (use as annotation) |

## Post-Action Payload Field Forms

| Form | Example | Use when |
|------|---------|----------|
| Direct string | `adapter: "my-adapter"` | Static values |
| Go Template | `adapter: "{{ .metadata.name }}"` | Dynamic string interpolation |
| CEL expression | `status: { expression: "..." }` | Computed values, conditionals |
| Field extraction | `status: { field: "path", default: "..." }` | Simple field reads |

## Condition Types

Every adapter status reports three conditions:

| Type | Question it answers |
|------|---------------------|
| **Applied** | Were the Kubernetes resources created/configured? |
| **Available** | Are the resources operational and serving? |
| **Health** | Did the adapter execution itself succeed? |

Possible status values: `"True"`, `"False"`, `"Unknown"`

## Resource Lifecycle Operations

| Operation | When | Behavior |
|-----------|------|----------|
| `create` | Resource doesn't exist | Apply the manifest |
| `update` | Resource exists, generation changed | Patch the resource |
| `skip` | Resource exists, generation unchanged | No-op (idempotent) |
| `recreate` | `recreateOnChange: true` is set | Delete then create |
