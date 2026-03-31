# Adapter Templates

## How to Use

Read the adapter authoring guide:

```bash
curl -sL https://raw.githubusercontent.com/openshift-hyperfleet/hyperfleet-adapter/main/docs/adapter-authoring-guide.md
```

Or browse it directly on GitHub: `https://github.com/openshift-hyperfleet/hyperfleet-adapter/blob/main/docs/adapter-authoring-guide.md`

Also fetch the example configurations:

```bash
# List available examples
gh api repos/openshift-hyperfleet/hyperfleet-adapter/contents/charts/examples --jq '.[].name'

# Fetch specific example (e.g., kubernetes adapter config)
gh api repos/openshift-hyperfleet/hyperfleet-adapter/contents/charts/examples/kubernetes/adapter-config.yaml --jq '.content' | base64 -d
```

The authoring guide and examples directory contain templates for:
- Kubernetes cluster adapter
- Maestro cluster adapter
- NodePool adapter
- No-Op/Validation adapter
- AdapterConfig for both Kubernetes direct and Maestro transports

Do NOT hardcode template content here -- always fetch the latest from the source repo.
