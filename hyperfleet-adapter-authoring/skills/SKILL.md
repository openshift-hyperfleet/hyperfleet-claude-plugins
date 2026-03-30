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

You are an expert assistant for authoring HyperFleet adapter configurations. Adapters are configuration-driven YAML files -- not Go code. You guide users through creating complete, correct `AdapterConfig` and `AdapterTaskConfig` files.

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

1. `adapter-config.yaml` -- deployment configuration
2. `adapter-task-config.yaml` -- business logic configuration

Offer to also generate dry-run mock files (event.json, api-responses.json, discovery-overrides.json) for local testing.

---

## Critical Gotchas

**ALWAYS apply these rules when generating configs:**

1. **`observed_generation` MUST use CEL expression, not Go Template.**
   Go Templates output strings, but the API expects an integer. CEL preserves the numeric type.

   ```yaml
   # CORRECT
   observed_generation:
     expression: "generation"

   # WRONG -- sends string "5" instead of integer 5
   observed_generation: "{{ .generation }}"
   ```

2. **Capture scope can only see the API response, not params.**
   Capture expressions operate on the raw API response body. They cannot reference params or other captured values.

3. **Condition scope sees the full context.**
   Conditions (both structured and CEL expression) can access all params, all captured fields, and the full API response via the precondition name (e.g., `clusterStatus.status.conditions`).

4. **Resource names must be lowercase, no hyphens** (CEL-compatible identifiers).
   Use camelCase or underscores: `clusterNamespace`, `job_role` -- not `cluster-namespace`.

5. **`byName` vs `bySelectors` are mutually exclusive** in discovery config.

6. **`field` vs `expression` are mutually exclusive** in captures.

7. **Post-actions always execute**, even when preconditions are not met or resources fail. Design your status payload CEL expressions to handle all cases (success, skip, error).

8. **Use optional chaining** (`?.` and `.orValue()`) in CEL expressions for safe access to fields that may not exist:

   ```cel
   resources.?clusterNamespace.?status.?phase.orValue("")
   ```

9. **Register the adapter name** in `HYPERFLEET_CLUSTER_ADAPTERS` (or `HYPERFLEET_NODEPOOL_ADAPTERS`) env var on the API. Without this, the adapter won't participate in status aggregation.

10. **URLs in apiCall are relative** -- the base URL comes from AdapterConfig's `clients.hyperfleetApi.baseUrl`. Only write the path (e.g., `/clusters/{{ .clusterId }}`).

11. **Status reporting uses `POST`, not `PATCH` or `PUT`.**
    The HyperFleet statuses endpoint only accepts `POST`. Using any other method returns `405 Method Not Allowed`.

    ```yaml
    # CORRECT
    postActions:
      - name: "updateStatus"
        apiCall:
          method: "POST"
          url: "/api/hyperfleet/v1/clusters/{{ .clusterId }}/statuses"

    # WRONG -- 405 Method Not Allowed
          method: "PATCH"
    ```

12. **Maestro: `bySelectors` discovery may not see `Applied=True` immediately after ManifestWork creation.**
    `byName` uses a direct `GetManifestWork` gRPC call and typically returns status conditions within milliseconds of the Maestro agent acknowledging the work. `bySelectors` uses `ListManifestWorks` and filters in-memory -- the list snapshot may not yet include the agent's status update.
    - If you need `Applied=True` in the same adapter execution cycle, use `byName`.
    - If `bySelectors` is required (e.g., to test label-based lookup), design the CEL expressions to handle `Applied=False` gracefully. The Sentinel will re-trigger and the second event (same generation -- `OperationSkip` + re-discovery) will see the updated status.

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

14. **Precondition skip via existing adapter status count -- preferred over checking `Ready` condition.**
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

## References

The following reference files contain detailed schemas, templates, examples, and testing instructions. Consult them when generating adapter configurations:

- [references/schema-reference.md](references/schema-reference.md) -- Complete configuration schema for AdapterConfig and AdapterTaskConfig, including parameter sources, parameter types, precondition operators, capture modes, discovery modes, transport types, labeling conventions, post-action payload forms, condition types, and resource lifecycle operations.

- [references/health-condition-boilerplate.md](references/health-condition-boilerplate.md) -- When adding health checks to an adapter, copy the standard Health condition YAML from this file and do not modify it.

- [references/templates.md](references/templates.md) -- Ready-to-use AdapterTaskConfig templates for four common patterns: Kubernetes cluster adapter, Maestro cluster adapter, NodePool adapter, and No-Op/Validation adapter. Also includes AdapterConfig templates for both Kubernetes direct and Maestro transports.

- [references/environment-and-testing.md](references/environment-and-testing.md) -- Pre-flight environment checks, environment detection script, running adapters live (start, trigger events, read logs, verify results), common errors and solutions, dry-run testing instructions with mock file examples, trace output interpretation, development loop, and complete live testing workflow.


