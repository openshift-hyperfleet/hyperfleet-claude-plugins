# Contributing to HyperFleet Claude Plugins

Thank you for contributing to the HyperFleet Claude Plugins marketplace! This guide covers everything you need to know about adding, developing, and maintaining plugins.

## Table of Contents

- [Adding a Plugin](#adding-a-plugin)
- [Local Development and Debugging](#local-development-and-debugging)
- [Versioning](#versioning)
- [Pull Request Workflow](#pull-request-workflow)
- [Feedback and Issues](#feedback-and-issues)

## Adding a Plugin

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

```text
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

## Local Development and Debugging

When developing or debugging a plugin, use the `--plugin-dir` flag to load the plugin directly from your local directory:

```bash
claude --plugin-dir /path/to/hyperfleet-claude-plugins/<plugin-name>
```

This bypasses the marketplace installation and loads your local working copy, making changes immediately available on restart.

### Development Workflow

1. Make changes to plugin files (`SKILL.md`, `commands/*.md`, `AGENT.md`, etc.)
2. Bump the `version` in `.claude-plugin/plugin.json`
3. Restart Claude Code with `--plugin-dir` pointing to your plugin directory
4. Test your changes by invoking the skill/command

### Debugging Tips

- Add a debug indicator at the start of your skill/command output to confirm the local version is running (e.g., "🔧 LOCAL VERSION ACTIVE")
- Changes require a restart of Claude Code to take effect
- The `--plugin-dir` flag overrides any marketplace-installed version of the same plugin

## Versioning

Plugins follow [semantic versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes (e.g., changing skill behavior, removing functionality)
- **MINOR** - New features or enhancements (backwards compatible)
- **PATCH** - Bug fixes and minor improvements

### To Version Your Plugin

1. Update the `version` field in `.claude-plugin/plugin.json`
2. Commit changes describing what changed
3. Merge to main

Team members get updates by running `/plugin marketplace update hyperfleet-claude-plugins` and restarting Claude Code.

## Pull Request Workflow

### OWNERS Files

This repository utilizes k8s-style OWNERS files. Each plugin is expected to define an OWNERS file with a list of approvers and (optionally) reviewers. PRs making changes to a plugin must be reviewed by the reviewers/approvers listed in that plugin's OWNERS file.

See [k8s OWNERS documentation](https://www.kubernetes.dev/docs/guide/owners/) for more information.

### Submitting Changes

1. Follow the plugin structure outlined in "Adding a Plugin" above
2. Bump the version number according to semantic versioning
3. Submit a PR with your changes
4. Request review from reviewers/approvers listed in the OWNERS file

## Feedback and Issues

We welcome feedback and contributions from the HyperFleet team!

**Have feedback on an existing plugin?**
- Open an issue in this repository describing the problem or suggestion

**Want to suggest a new plugin?**
- Open an issue with the plugin idea and use case
- Include the plugin type (Command, Agent, Skill, Hook) if known

**Ready to contribute a plugin?**
- Follow the structure in "Adding a Plugin" above
- Submit a PR with your plugin
- Request review from reviewers/approvers listed in the OWNERS file
