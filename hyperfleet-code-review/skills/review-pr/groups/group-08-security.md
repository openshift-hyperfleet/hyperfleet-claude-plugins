# Group 8 — Security (passes 8.A + 8.B + 8.C)

This group is **language-agnostic** and runs for every PR regardless of file types.

### Pass 8.A — Injection vulnerabilities

Per the HyperFleet error model standard (fetched in the data-gathering step), user input in error messages must be sanitized to prevent injection.

List every place in the diff where external input (HTTP parameters, environment variables, user-provided strings, file content) is incorporated into:

- **SQL queries** — flag string concatenation or `fmt.Sprintf` used to build queries instead of parameterized queries / prepared statements
- **Shell commands** — flag `exec.Command`, `os/exec`, subprocess calls, or equivalent where arguments are not properly sanitized or come directly from user input
- **Template rendering** — flag `html/template` or equivalent usage where user input is passed without escaping

- **Error messages** — flag `fmt.Errorf(...)`, Problem Details `detail` fields, or error response constructors where user-supplied input is interpolated without sanitization. User input in error messages can enable log injection (newlines, ANSI escape sequences) or be reflected unsanitized in HTTP responses. Per the error model standard, user input in error messages MUST be sanitized

Do NOT flag:
- Queries built with query-builder libraries that handle parameterization (e.g., `squirrel`, `sqlx` named queries)
- Commands where all arguments are hardcoded constants
- Error messages that only include internal identifiers (e.g., resource IDs, error codes) — not user-supplied strings

### Pass 8.B — Secrets exposure

Per the HyperFleet logging specification and error model standard (fetched in the data-gathering step), verify that sensitive data is properly redacted from logs and error responses. Check the standards for the specific list of items that MUST be redacted.

List every log statement, error message, HTTP response body, and metric label in the diff. For each, check if it could expose sensitive data:

- **Credentials** — passwords, tokens, API keys, certificates, private keys
- **Cloud provider credentials** — GCP service account JSON keys, AWS access key IDs (`AKIA*`), Azure client secrets. Per the logging specification, cloud provider access keys MUST be redacted
- **PII** — email addresses, usernames in combination with auth data
- **Full request/response bodies** — that may contain auth headers or tokens. Per the logging specification, full payloads are classified under `debug` level ("Variable values, event payloads") — flag any `log.Info` or `log.Warn` that logs complete request/response bodies
- **Stack traces in API responses** — flag error responses that include stack traces or internal implementation details (per error model standard, log full details internally but sanitize external responses)
- **System details in error responses** — flag error responses that expose internal hostnames, database connection strings, file system paths, or library version information. Per the error model standard, internal error messages that may reveal system details MUST NOT be exposed
- **Structured error log fields** — per the logging specification, `request_context` objects in error logs MUST have sensitive data masked. Flag structured logging calls that include a `request_context` or similar payload object without masking sensitive fields (auth headers, tokens, credentials)

Flag instances where sensitive data is logged, returned in error responses, or included in metric labels. Suggest redaction or structured logging that excludes sensitive fields.

Do NOT flag:
- Logging of request IDs, trace IDs, or non-sensitive metadata
- Debug-level logs that only log field names (not values)
- `request_context` fields that only contain non-sensitive data (method, path, resource IDs)

### Pass 8.C — Path traversal and input validation

List every place in the diff where external input is used to construct file paths, URLs, or resource identifiers. For each, check:

- **Path traversal** — flag if `../` sequences or absolute paths from user input are not sanitized (e.g., missing `filepath.Clean()`, `filepath.Rel()`, or base-path validation)
- **Input validation at system boundaries** — for HTTP handlers, CLI argument parsers, webhook receivers, and config file readers: flag missing validation of required fields, type assertions without checks, or unbounded input (e.g., no max length on string fields, no max size on uploaded files)

Do NOT flag:
- Internal function calls where input comes from trusted, already-validated sources
- Config files that are not user-facing
