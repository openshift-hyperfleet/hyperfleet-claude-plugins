# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Security

## hyperfleet-devtools [0.4.0] - 2026-03-27

### Added
- E2E test case design skill for generating comprehensive end-to-end test scenarios ([HYPERFLEET-778](https://issues.redhat.com/browse/HYPERFLEET-778))

## hyperfleet-jira [0.4.0] - 2026-03-25

### Changed
- Updated team-weekly-update command with improved Jira generation and Epic complete ratio in report output ([HYPERFLEET-800](https://issues.redhat.com/browse/HYPERFLEET-800))
- Enhanced weekly update report format with activity tracking improvements

### Security
- Added untrusted input warnings for skills and commands processing external content ([HYPERFLEET-131](https://issues.redhat.com/browse/HYPERFLEET-131))

## Repository [0.3.0] - 2026-03-25

### Added
- CONTRIBUTING.md with comprehensive contributor guidelines ([HYPERFLEET-807](https://issues.redhat.com/browse/HYPERFLEET-807))
- Local development and debugging workflow documentation using `--plugin-dir` flag
- Security guidelines section covering least privilege, external system access, dynamic context risks, and untrusted input handling

### Changed
- Restructured documentation to separate user and contributor content
- Moved plugin addition guide, versioning, and OWNERS sections to CONTRIBUTING.md
- Streamlined README to focus on end-user installation and updates
- Updated review workflow to align with bot-based review process

## hyperfleet-devtools [0.3.0] - 2026-03-20

### Changed
- Enhanced commit-message command to generate complete commit messages with body content ([HYPERFLEET-787](https://issues.redhat.com/browse/HYPERFLEET-787))
- Automatic commit body generation with summary and bullet points
- Messages now saved to `/tmp/commit-msg-<ticket>.txt` files for easier committing
- Improved output presentation with detailed validation feedback

## hyperfleet-code-review [0.2.0] - 2026-03-20

### Added
- Five new mechanical pass categories covering security, performance, error wrapping, naming, and testing quality
- Security passes (R, S, T) for credential handling, injection vulnerabilities, and TLS validation
- Performance passes (U, V) for unnecessary allocations and loop optimizations
- Error wrapping pass (W) ensuring Go 1.13+ error chains
- Naming and organization passes (X, Y) for Go conventions and struct organization
- Testing quality passes (I, Z, AA) for coverage and test reliability
- References to HyperFleet standards (error-model, logging-specification)

### Changed
- Rebalanced mechanical passes from 8 to 10 groups
- Merged single-pass groups and moved thematically related passes together

## hyperfleet-jira [0.3.0] - 2026-03-16

### Changed
- Updated jira-cli setup documentation for Atlassian Cloud migration
- Replaced generic jira init instructions with HyperFleet-specific command (server: redhat.atlassian.net, auth-type: basic)
- Added cross-reference from hyperfleet-code-review troubleshooting to hyperfleet-jira setup guide

## hyperfleet-code-review [0.1.3] - 2026-03-16

### Fixed
- Replaced blockquotes with fenced code blocks in review-pr output for better terminal readability ([HYPERFLEET-703](https://issues.redhat.com/browse/HYPERFLEET-703))
- Blockquotes rendered as vertical bars making output hard to read; now using markdown code blocks for GitHub comments

## hyperfleet-code-review [0.1.2] - 2026-03-13

### Added
- Three new language-agnostic mechanical pass groups
- Pass O: Flags TODOs/FIXMEs/HACKs without a JIRA ticket reference
- Pass P: Validates log level matches event severity and flags log spam in loops
- Pass Q: Detects misspelled words, identifiers, and inconsistent spelling within PRs
- CLAUDE.md for repository-specific guidance

## hyperfleet-code-review [0.1.1] - 2026-03-12

### Changed
- Renamed "Priority" to "Category" in review output for clarity ([HYPERFLEET-703](https://issues.redhat.com/browse/HYPERFLEET-703))

## hyperfleet-code-review [0.1.0] - 2026-03-11

### Added
- Initial release of hyperfleet-code-review plugin ([HYPERFLEET-703](https://issues.redhat.com/browse/HYPERFLEET-703))
- Standardized, interactive PR review workflow with `/review-pr` command
- JIRA validation ensuring PRs are linked to valid tickets
- Architecture checks against HyperFleet standards
- Impact analysis for code changes
- 14 mechanical code pattern checks for Go code
- Skills 2.0 format with supporting files (mechanical-passes.md, output-format.md)
- Dynamic context for tool detection (jira, gh, architecture skill)
- Cross-platform notification support (macOS and Linux)
- Intra-PR link and anchor validation for runbook URLs

### Changed
- Migrated from commands format to Skills 2.0 format

## hyperfleet-jira [0.2.0] - 2026-03-06

### Added
- team-weekly-update command for team managers to generate weekly activity reports

## hyperfleet-devtools [0.2.0] - 2026-03-04

### Added
- commit-message generator command ([HYPERFLEET-670](https://issues.redhat.com/browse/HYPERFLEET-670))
- Automated commit message generation following HyperFleet commit standards

## Repository [0.2.0] - 2026-03-03

### Changed
- Updated OWNERS file with current maintainers ([HYPERFLEET-702](https://issues.redhat.com/browse/HYPERFLEET-702))
- Removed AlexVulaj from OWNERS and maintainers lists

## hyperfleet-devtools [0.1.0] - 2026-02-27

### Added
- architecture-impact skill for analyzing architectural impact of changes ([HYPERFLEET-507](https://issues.redhat.com/browse/HYPERFLEET-507))

### Fixed
- Improved architecture-impact skill to reduce false positives ([HYPERFLEET-684](https://issues.redhat.com/browse/HYPERFLEET-684))

## hyperfleet-adapter-authoring [0.1.0] - 2026-02-24

### Added
- Initial skill to author HyperFleet adapter configurations
- Guidance for creating and validating adapter YAML files

## Repository [0.1.0] - 2026-02-14

### Added
- Initial repository setup with marketplace structure
- hyperfleet-architecture plugin (v0.1.0) - Architecture knowledge base for design patterns and principles
- hyperfleet-jira plugin (v0.1.0) - JIRA integration for sprint management and task tracking
- hyperfleet-standards plugin (v0.1.0) - Architecture standards audit tool
- hyperfleet-operational-readiness plugin (v0.1.0) - Operational readiness audit tool
- hyperfleet-devtools plugin (initial version) - Development assistance tools
- Marketplace configuration in `.claude-plugin/marketplace.json`
- OWNERS file for PR review workflow

---

<!-- Changelog Guidelines:

Follow these guidelines when updating the changelog:

1. **What to include:**
   - All notable changes that affect users
   - New features, bug fixes, security fixes
   - Breaking changes (mark with "BREAKING CHANGE" in description)
   - Deprecations and removals

2. **What NOT to include:**
   - Internal refactoring that doesn't affect users
   - Development tooling changes
   - Documentation typo fixes
   - Code formatting changes

3. **How to categorize changes:**
   - **Added** for new features
   - **Changed** for changes in existing functionality
   - **Deprecated** for soon-to-be removed features
   - **Removed** for now removed features
   - **Fixed** for any bug fixes
   - **Security** for vulnerability fixes

4. **Version format:**
   - Plugin versions: `<plugin-name> [x.y.z]` for individual plugin releases
   - Repository versions: `Repository [x.y.z]` for repository-wide changes
   - Use semantic versioning (MAJOR.MINOR.PATCH)
   - Include release date in YYYY-MM-DD format

5. **Entry format:**
   ```markdown
   ### Added
   - Brief description of the change ([HYPERFLEET-XXX](link))
   ```

-->
