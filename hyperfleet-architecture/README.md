# HyperFleet Architecture Skill

A Claude Code skill plugin that provides instant access to HyperFleet architecture documentation and design decisions.

## What It Does

This skill enables Claude to automatically pull in HyperFleet architecture documentation when you ask questions about:
- Architecture patterns and design principles
- Versioning strategies (API, Sentinel, adapters, config)
- Status aggregation and cluster lifecycle
- Event-driven architecture and CloudEvents
- Adapter framework and deployment model
- Git workflow and release processes

## How It Works

The skill instructs Claude to read relevant documentation from the HyperFleet architecture repository (`/Users/alexvulaj/Workspace/architecture/hyperfleet/docs/`) when answering questions. This ensures:
- **Always up-to-date**: Uses the latest documentation as the single source of truth
- **Accurate answers**: Based on actual team decisions, not Claude's general knowledge
- **No manual invocation**: Claude automatically uses the skill when relevant

## Installation

1. Install the HyperFleet plugin marketplace (if not already installed):
   ```
   /plugin marketplace add openshift-hyperfleet/hyperfleet-claude-plugins
   ```

2. Install this skill:
   ```
   /plugin install hyperfleet-architecture@openshift-hyperfleet/hyperfleet-claude-plugins
   ```

3. Update to get the latest version:
   ```
   /plugin marketplace update hyperfleet-claude-plugins
   ```

## Example Usage

Just ask Claude questions naturally:

- "How does HyperFleet handle API versioning?"
- "What's the adapter config versioning strategy?"
- "How do we version CloudEvents schemas?"
- "What's our Git branching model?"
- "How does the status aggregation work?"
- "What are the cluster lifecycle phases?"

Claude will automatically invoke this skill, read the relevant docs, and provide accurate answers based on the team's documented decisions.

## Documentation Coverage

This skill provides access to:
- API versioning strategy
- Sentinel and CloudEvents versioning
- Adapter binary and config versioning
- Git workflow and release strategy
- Versioning trade-offs and post-MVP considerations
- Cluster status and lifecycle management
- Architecture spikes and investigations

## Maintenance

The skill remains lightweight and maintenance-free. As the architecture docs are updated in the architecture repository, this skill automatically uses the latest content - no plugin updates needed for content changes.
