# adapter-config-author

An interactive Claude Code skill that guides you through authoring HyperFleet adapter configurations — the YAML files that define how an adapter behaves, not Go code.

## What it does

When activated, this skill walks you step-by-step through generating two configuration files:

- **`adapter-config.yaml`** (`AdapterConfig`) — deployment settings: logging, clients, broker subscription, transport
- **`adapter-task-config.yaml`** (`AdapterTaskConfig`) — business logic: params, preconditions, resources, and post-actions

It also offers to generate dry-run mock files (`event.json`, `api-responses.json`, `discovery-overrides.json`) so you can test your adapter locally before running against real infrastructure.

## How to trigger it

Use any of these phrases:

- "create adapter"
- "write adapter"
- "new adapter"
- "adapter config"
- "adapter task config"
- "AdapterConfig" / "AdapterTaskConfig"

## What it covers

| Topic | Details |
|-------|---------|
| Resource types | Cluster adapters and NodePool adapters |
| Transport types | Kubernetes direct and Maestro (ManifestWork via OCM) |
| Config schema | Full `AdapterConfig` and `AdapterTaskConfig` structure with all fields |
| Param sources | `event.*`, `env.*`, `secret.*`, `configmap.*` |
| Preconditions | API calls, captures (`field` / `expression`), condition operators |
| Resources | Inline manifests, discovery (`byName` / `bySelectors`), lifecycle operations |
| Post-actions | Payload building, CEL expressions, status reporting |
| Dry-run testing | Mock files and how to interpret the phase-by-phase trace |
| Live testing | End-to-end workflow from startup to verification |
| Common gotchas | 16 documented pitfalls with correct patterns |

## Templates included

1. **Kubernetes Cluster Adapter** — Namespace + ConfigMap via direct Kubernetes transport
2. **Maestro Cluster Adapter** — ManifestWork delivered to a remote spoke cluster via OCM/Maestro
3. **NodePool Adapter** — with parent cluster readiness dependency check
4. **No-Op / Validation Adapter** — preconditions and status reporting only, no resource creation

## Reference material

The full authoring guide is at `references/authoring-guide.md` and is loaded automatically when the skill runs.
