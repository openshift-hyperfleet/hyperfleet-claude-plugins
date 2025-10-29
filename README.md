# HyperFleet Claude Plugins

A collection of Claude plugins for the HyperFleet team, exposed as a Claude plugin marketplace.

## Documentation

- [Claude Plugins Documentation](https://docs.claude.com/en/docs/claude-code/plugins)
- [Claude Plugin Marketplaces Documentation](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)

## Using this Marketplace

### Within Claude Code
Optionally, use the `/plugin` slash command without any options for a simplified interactive experience.

To install the marketplace:
```bash
/plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
```

Install a plugin:
```bash
/plugin install <plugin-name>@openshift-hyperfleet/hyperfleet-claude-plugins
```

**Note:** After installing a plugin, restart Claude Code to load it.

## Adding a Plugin to this Repository

Plugins are defined in `.claude-plugin/marketplace.json`. Add your plugin entry to the `plugins` array:

### Option 1: Add Plugin Source Directly

For plugins maintained in this repository:

```json
{
  "name": "your-plugin-name",
  "source": "./your-plugin-name",
  "description": "Brief description of what your plugin does"
}
```

Then create your plugin in the specified directory:

```
hyperfleet-claude-plugins/
└── your-plugin-name/
    ├── .claude-plugin/
    │   └── plugin.json          # Required plugin metadata
    ├── skills/                   # Optional: for skill plugins
    │   └── skill-name/
    │       └── SKILL.md
    ├── commands/                 # Optional: for command plugins
    ├── agents/                   # Optional: for agent plugins
    ├── hooks/                    # Optional: for hook plugins
    ├── OWNERS                    # Required for PR workflow
    └── README.md                 # Recommended
```

### Option 2: Reference External GitHub Repository

For plugins maintained in a separate repository:

```json
{
  "name": "your-plugin-name",
  "source": {
    "type": "github",
    "repo": "openshift-hyperfleet/your-plugin-repo"
  },
  "description": "Brief description of what your plugin does"
}
```

### Versioning Plugins

Plugins follow [semantic versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes (e.g., changing skill behavior, removing functionality)
- **MINOR** - New features or enhancements (backwards compatible)
- **PATCH** - Bug fixes and minor improvements

**To version your plugin:**
1. Update the `version` field in `.claude-plugin/plugin.json`
2. Commit changes describing what changed
3. Merge to main

Team members get updates by running `/plugin marketplace update hyperfleet-claude-plugins` and restarting Claude Code.

### OWNERS file enablement

This repository utilizes k8s-style OWNERS files. Each plugin is expected to define an OWNERS file with a list of approvers and (optionally) reviewers. This enables the approvers to comment `/approve` on a PR making changes only to that plugin to merge the changes.

See [k8s OWNERS documentation](https://www.kubernetes.dev/docs/guide/owners/) for more information.

## Updating your Plugins

All plugins connected to this marketplace (commands, agents, skills, etc) must be updated manually within the Claude interface.

```
/plugin marketplace update hyperfleet-claude-plugins
```

Running this command within your Claude prompt will automatically refresh and update all plugins you've installed from the hyperfleet-claude-plugins marketplace!

## Feedback & Contributions

We welcome feedback and contributions from the HyperFleet team!

**Have feedback on an existing plugin?**
- Open an issue in this repository describing the problem or suggestion

**Want to suggest a new plugin?**
- Open an issue with the plugin idea and use case
- Include the plugin type (Command, Agent, Skill, Hook) if known

**Ready to contribute a plugin?**
- Follow the structure in "Adding a Plugin to this Repository" above
- Submit a PR with your plugin
- OWNERS will review using the `/approve` workflow

## Planned Plugins

The following plugins are planned for development as HyperFleet infrastructure matures.

### 1. Adapter Config Generator
- **Type**: Command plugin (`/generate-adapter-config`)
- **Purpose**: Generate adapter configuration YAML from template
- **Inputs**: Adapter name, cloud provider, job image
- **Output**: Validated YAML config following team schema

### 2. OpenAPI Spec Validator
- **Type**: Hook plugin (on-file-save)
- **Purpose**: Validate OpenAPI spec changes against versioning strategy
- **Triggers**: When `openapi.yaml` is modified
- **Checks**: Semantic versioning rules, backwards compatibility

### 3. HyperFleet Architecture Reviewer
- **Type**: Agent plugin
- **Purpose**: Review code changes against HyperFleet architecture principles
- **Checks**: Event-driven patterns, config-driven design, cloud-agnostic core

### 4. Status Contract Generator
- **Type**: Command plugin (`/generate-status-contract`)
- **Purpose**: Generate adapter status reporting code
- **Output**: Go code implementing condition-based status contract

### 5. Anti-Pattern Detector
- **Type**: Skill plugin
- **Purpose**: Detect patterns that caused issues in previous projects (lessons learned)
- **Examples**: API technical debt patterns, tight coupling, manual SDK releases
