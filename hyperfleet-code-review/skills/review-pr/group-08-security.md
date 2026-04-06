# Group 8 — Security (passes 8a + 8b + 8c)

This group is **language-agnostic** and runs for every PR regardless of file types.

## Pass 8a — Injection vulnerabilities

Apply the injection prevention requirements from the HyperFleet error model standard fetched in step 4b. If the standard was not fetched, emit a mandatory finding stating "required error model standard unavailable" with details and skip this pass.

List every place in the diff where external input (HTTP parameters, environment variables, user-provided strings, file content) is incorporated into SQL queries, shell commands, template rendering, or any other injection vector identified in the standard. For each, check against the sanitization and validation requirements defined in the standard.

## Pass 8b — Secrets exposure

Apply the data redaction requirements from the HyperFleet logging specification and error model standard fetched in step 4b. These standards define the specific list of items that MUST be redacted and the rules for what can appear in logs, error responses, and metric labels. If the standards were not fetched, emit a mandatory finding stating "required logging/error model standards unavailable" with details and skip this pass.

List every log statement, error message, HTTP response body, and metric label in the diff. For each, check against the redaction and exposure requirements defined in the standards.

## Pass 8c — Path traversal and input validation

List every place in the diff where external input is used to construct file paths, URLs, or resource identifiers. For each, check:

- **Path traversal** — flag if `../` sequences or absolute paths from user input are not sanitized (e.g., missing `filepath.Clean()`, `filepath.Rel()`, or base-path validation)
- **Input validation at system boundaries** — for HTTP handlers, CLI argument parsers, webhook receivers, and config file readers: flag missing validation of required fields, type assertions without checks, or unbounded input (e.g., no max length on string fields, no max size on uploaded files)

Do NOT flag:
- Internal function calls where input comes from trusted, already-validated sources
- Config files that are not user-facing
