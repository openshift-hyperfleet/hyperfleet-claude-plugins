# Group 9 — Code hygiene (passes 9a + 9b + 9c)

This group is **language-agnostic** and runs for every PR regardless of file types.

## Pass 9a — TODOs/FIXMEs without ticket

Apply the commit message and code comment requirements from the HyperFleet **Commit Message Standard** fetched in step 4b. The standard defines the expected ticket reference format and TODO conventions. If the standard was not fetched, emit a mandatory finding stating "required Commit Message Standard unavailable" with details and skip this pass.

List every `TODO`, `FIXME`, `HACK`, and `XXX` comment added or modified in the diff. For each, check whether it references a ticket ID per the format defined in the standards. Flag TODOs that have no ticket reference.

## Pass 9b — Log level appropriateness

Apply the log level requirements from the HyperFleet **Logging Specification** fetched in step 4b. The standard defines which log levels to use for each type of event, the expected logging library/framework, and rules for log output in loops and hot paths. If the standard was not fetched, emit a mandatory finding stating "required Logging Specification unavailable" with details and skip this pass.

List every log statement added or modified in the diff. For each:

1. Verify the logging framework/library matches the one required by the standard
2. Evaluate whether the log level matches the requirements defined in the **Logging Specification**
3. Flag log statements in loops or hot paths that violate the standard's rules (e.g., expensive formatting, synchronous I/O, high-frequency debug logs)
4. Flag inconsistent log levels for the same type of event within the PR

## Pass 9c — Typo detection

List every added or modified line in the diff that contains text written by humans (identifiers, comments, strings, log messages, error messages, documentation, YAML values, markdown prose). For each, check for:

- **Misspelled words** in comments, doc strings, log/error messages, markdown, and YAML descriptions
- **Misspelled identifiers** — variable names, function names, struct fields, constants, and type names that contain common English misspellings (e.g., `recieve` instead of `receive`, `seperator` instead of `separator`, `retreive` instead of `retrieve`)
- **Inconsistent spelling** within the PR — the same concept spelled differently in different places (e.g., `canceled` vs `cancelled`, `color` vs `colour`)

Do NOT flag:
- Intentional abbreviations or domain-specific jargon (e.g., `k8s`, `ctx`, `cfg`, `mgr`, `msg`, `req`, `resp`)
- Third-party identifiers (imported package names, external API fields)
- Code-generated content
- Single-letter variables in small scopes
