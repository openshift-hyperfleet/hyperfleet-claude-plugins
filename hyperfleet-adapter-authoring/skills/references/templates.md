# Templates for Common Patterns

## Template 1: Kubernetes Cluster Adapter (Namespace + ConfigMap)

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

## Template 2: Maestro Cluster Adapter (ManifestWork)

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

## Template 3: NodePool Adapter (with parent cluster readiness check)

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

## Template 4: No-Op / Validation Adapter

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

## Template: AdapterConfig (use with any of the above)

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
