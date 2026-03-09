# Changelog

All notable changes to the hyperfleet-code-review plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-09

### Added

- Initial release
- `review-pr` command for standardized, interactive PR review workflow
- JIRA ticket validation against PR changes
- HyperFleet architecture documentation consistency checks
- Impact analysis for breaking changes detection
- Call chain tracing across the codebase
- Doc-Code cross-referencing for mismatches
- Mechanical code pattern checks (8 passes: switch exhaustiveness, error handling, resource lifecycle, concurrency safety, goroutine lifecycle, nil/bounds safety, constants, log-and-continue)
- Deduplication against CodeRabbit, human reviewers, and prior conversation context
- Interactive navigation (next, all, jump to specific recommendation)
- GitHub-ready comments with accurate line numbers
