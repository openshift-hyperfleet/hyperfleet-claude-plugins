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

## Updating your Plugins

All plugins connected to this marketplace (commands, agents, skills, etc) must be updated manually within the Claude interface.

```
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

## Available Plugins

### Development Tools
- **hyperfleet-devtools** - Commit message generation, architecture impact analysis
- **hyperfleet-code-review** - Comprehensive PR review with 10 groups of automated checks and architecture validation

## Adoption Tracking

All plugins include opt-in usage tracking via dynamic context in each skill's `SKILL.md`. On first use of any skill, Claude will ask whether you'd like to enable usage tracking. The following fields are sent: your GitHub username, plugin name, skill name, and event type (installation/update/invocation). Your choice is stored in `~/.claude/.hyperfleet-tracking-consent` and applies to all plugins.

When enabled, a tracking script sends usage data (GitHub username, plugin name, skill name, event type) to this repository via GitHub `repository_dispatch` events. A GitHub Action aggregates the data on an orphan branch called `data`, which contains:

- `usage.json` - aggregated usage data per user
- `README.md` - auto-generated dashboard with installation counts, active users, and invocation metrics

Only publicly available information is collected -- the GitHub username is already visible on every commit and profile page. No extra credentials are needed (uses existing `gh` CLI authentication). The tracking runs in the background and does not block Claude Code.

To **reset your choice**, delete the consent file and you'll be asked again on next use:

```bash
rm ~/.claude/.hyperfleet-tracking-consent
```

Invocation events are rate-limited to **at most once per day** per plugin/skill to minimize GitHub API usage. Installation and update events are always sent.

See the [Usage Dashboard](https://github.com/openshift-hyperfleet/hyperfleet-claude-plugins/blob/data/README.md) for current adoption metrics.

### JIRA Integration
- **hyperfleet-jira** - Task management, sprint status, team updates, ticket creation and triage

### Architecture & Standards
- **hyperfleet-architecture** - Q&A access to HyperFleet architecture documentation
- **hyperfleet-standards** - Audit repositories against team architecture standards

### Adapter Development
- **hyperfleet-adapter-authoring** - Interactive guide for authoring adapter configurations
- **hyperfleet-operational-readiness** - Operational readiness audit for production deployments

For detailed information on each plugin, see their individual README files in the plugin directories.
