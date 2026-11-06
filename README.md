# HyperFleet Claude Plugins

A collection of Claude plugins for the HyperFleet team, exposed as a Claude plugin marketplace.

## Documentation

- [Claude Plugins Documentation](https://docs.claude.com/en/docs/claude-code/plugins)
- [Claude Plugin Marketplaces Documentation](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)

## Using this Marketplace

### Within Claude Code
Optionally, use the `/plugin` slash command without any options for a simplified interactive experience.

To install the marketplace:
```text
/plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
```

Install a plugin:
```text
/plugin install <plugin-name>@openshift-hyperfleet/hyperfleet-claude-plugins
```

**Note:** After installing a plugin, restart Claude Code to load it.

## Updating your Plugins

All plugins connected to this marketplace (commands, agents, skills, etc) must be updated manually within the Claude interface.

```text
/plugin marketplace update hyperfleet-claude-plugins
```

Running this command within your Claude prompt will automatically refresh and update all plugins you've installed from the hyperfleet-claude-plugins marketplace!

## Contributing

Want to contribute a plugin or improve existing ones? See [CONTRIBUTING.md](./CONTRIBUTING.md) for:

- Adding new plugins to the marketplace
- Local development and debugging workflow
- Versioning guidelines
- Pull request process

Questions or feedback? Open an issue in this repository.

## Testing

List available targets and run all discovered test suites from the repository root:

```bash
make help
make test
```

See [Testing in CONTRIBUTING.md](./CONTRIBUTING.md#testing) for the authoritative
runner convention, dependencies, and isolated suite execution.

## Available Plugins

### Development Tools
- **hyperfleet-devtools** - Commit message generation, architecture impact analysis
- **hyperfleet-code-review** - Local branch review and PR review with automated checks and architecture validation
- **hyperfleet-hooks** - Automated quality checks

### JIRA Integration
- **hyperfleet-jira** - Task management, sprint status, team updates, ticket creation and triage

### Architecture & Standards
- **hyperfleet-architecture** - Q&A access to HyperFleet architecture documentation
- **hyperfleet-standards** - Audit repositories against team architecture standards

### Work Triage
- **hyperfleet-work-triage** - Bug triage (JIRA + GitHub issues) and open PR prioritization across the org

### Adapter Development
- **hyperfleet-adapter-authoring** - Interactive guide for authoring adapter configurations
- **hyperfleet-operational-readiness** - Operational readiness audit for production deployments

For detailed information on each plugin, see their individual README files in the plugin directories.
