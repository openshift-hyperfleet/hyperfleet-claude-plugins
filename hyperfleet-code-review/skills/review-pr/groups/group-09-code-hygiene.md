# Group 9 — Code hygiene (passes 9.A + 9.B + 9.C)

This group is **language-agnostic** and runs for every PR regardless of file types.

### Pass 9.A — TODOs/FIXMEs without ticket

Per the HyperFleet commit message standard (`commit-standard.md`), all work items should be tracked. TODOs without ticket references become invisible technical debt.

List every `TODO`, `FIXME`, `HACK`, and `XXX` comment added or modified in the diff. For each, check whether it references a JIRA ticket ID (e.g., `// TODO(HYPERFLEET-123): ...` or `// FIXME HYPERFLEET-456: ...`). Flag TODOs that have no ticket reference — these become invisible technical debt. Suggest adding a ticket ID or creating a JIRA ticket to track the work.

Do NOT flag:
- TODOs that already reference a ticket ID in any common format (`TODO(TICKET-123)`, `TODO TICKET-123:`, `TODO: TICKET-123 -`)
- TODOs in test files that describe test improvements with clear intent (e.g., `// TODO: add table-driven test cases for edge X`)

### Pass 9.B — Log level appropriateness

Per the HyperFleet logging specification (`logging-specification.md`), each log level has a defined purpose. The standard specifies what events belong at each level and the consequences of misuse (e.g., error-level log spam triggers false alerts).

List every log statement added or modified in the diff (e.g., `log.Error`, `log.Warn`, `log.Info`, `log.Debug`, `slog.Error`, `slog.Info`, `logger.Error`, `logger.Info`, `klog.*`). For each, evaluate whether the log level matches the severity of the event:

- **Error** — should only be used for conditions that require human intervention or indicate a broken invariant. Flag `log.Error` used for expected/recoverable conditions (e.g., resource not found, validation failure, retry-able transient errors)
- **Warn** — should be used for unexpected but recoverable situations. Flag `log.Warn` used for normal operational events
- **Info** — should be used for significant operational events (startup, shutdown, configuration changes). Flag `log.Info` inside tight loops or hot paths where it would produce excessive output
- **Debug** — should be used for detailed diagnostic information. Flag `log.Debug` that contains sensitive data (credentials, tokens, full request bodies)

Also flag:
- Log statements inside loops that execute per-item without rate limiting or level guarding — these can produce log spam at scale
- Inconsistent log levels for the same type of event within the PR (e.g., logging "connection failed" as Error in one place and Warn in another)

### Pass 9.C — Typo detection

List every added or modified line in the diff that contains text written by humans (identifiers, comments, strings, log messages, error messages, documentation, YAML values, markdown prose). For each, check for:

- **Misspelled words** in comments, doc strings, log/error messages, markdown, and YAML descriptions
- **Misspelled identifiers** — variable names, function names, struct fields, constants, and type names that contain common English misspellings (e.g., `recieve` instead of `receive`, `seperator` instead of `separator`, `retreive` instead of `retrieve`)
- **Inconsistent spelling** within the PR — the same concept spelled differently in different places (e.g., `canceled` vs `cancelled`, `color` vs `colour`)

Do NOT flag:
- Intentional abbreviations or domain-specific jargon (e.g., `k8s`, `ctx`, `cfg`, `mgr`, `msg`, `req`, `resp`)
- Third-party identifiers (imported package names, external API fields)
- Code-generated content
- Single-letter variables in small scopes
