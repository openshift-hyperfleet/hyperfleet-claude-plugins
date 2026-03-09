# Changelog

All notable changes to the hyperfleet-jira plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-03-09

### Added

- `team-weekly-update` command for team managers - weekly progress report grouped by activity type and epic
- CLI support for story points (`--custom story-points=X`), priority (`--priority`), and activity type (`--custom activity-type`) in jira-ticket-creator skill

### Changed

- **Breaking:** Renamed skill `jira-hygiene` to `jira-triage` and command `hygiene-check` to `triage`. The old names have been removed with no aliases — update any automation or references that use `/hygiene-check` or the `jira-hygiene` skill to use `/triage` and `jira-triage` instead
- Updated required fields from 7 to 6 (removed Assignee check) in triage skill
- Added specific component validation (Adapter, API, Architecture, Sentinel) to triage skill
- Added duplicate detection as critical quality check in triage skill
- Refactored `team-weekly-update` to use a single `ACTIVITY_TYPES` array and reduce repetition

### Fixed

- HYPERFLEET-635: Removed unsupported `-b` flag from sprint commands
- HYPERFLEET-635: Replaced `--json` with `--raw` and added `-b 23064` to target scrum board

## [0.3.3] - 2025-11-25

### Fixed

- Added critical JIRA wiki markup vs Markdown warning table at top of jira-ticket-creator skill
- Added curly braces `{}` warning - breaks JIRA rendering entirely
- Documented alternatives: SCREAMING_CASE, colon notation, angle/square brackets
- Added real examples from HYPERFLEET-255 (Markdown issue) and HYPERFLEET-258 (curly braces issue)
- Updated API endpoints section with correct patterns

## [0.3.0] - 2025-11-25

### Added

- `jira-ticket-creator` skill for creating well-structured JIRA tickets with What/Why/Acceptance Criteria format
- `jira-story-pointer` skill for story point estimation

## [0.1.0] - 2025-11-24

### Added

- Initial release
- Commands: `my-sprint`, `my-tasks`, `new-comments`, `sprint-status`, `hygiene-check`
- Skill: `jira-hygiene` for ticket quality validation
- Configured for HYPERFLEET project

### Fixed

- Simplified `plugin.json` to match working format (removed unsupported `keywords` and `repository` fields)
- Added `project = HYPERFLEET` filter to all JQL queries
