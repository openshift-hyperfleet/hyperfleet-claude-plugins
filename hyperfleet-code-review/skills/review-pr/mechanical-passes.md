# Mechanical Code Pattern Checks

Launch 10 grouped agents in parallel using a single tool-call block (`subagent_type=general-purpose`). Each agent receives the diff content, the list of changed files, and the HyperFleet standards fetched in step 2. Each agent must: list every instance found in the diff before evaluating it, then return a JSON array of findings (or empty array if none). Do NOT skip a check because "it looks fine" — enumerate first, then judge.

Groups 1–7 and 10 are written for Go codebases (HyperFleet's primary language). Skip these groups when the diff contains no `.go` files. If a check finds zero instances, it naturally produces no findings. Groups 8–9 are language-agnostic and run for every PR.

## Group 1 — Error handling and wrapping (passes B + H + M + W)

### Pass B — Error handling completeness

List every function call in the diff that returns an `error`. For each, verify the error is checked. Flag silently ignored errors (`_, _ :=` or bare calls on error-returning functions).

### Pass H — Log-and-continue vs return

List every error-logging statement in the diff where execution continues after the log. For each, verify this is intentional graceful degradation and not a missing `return`.

### Pass M — HTTP handler missing return after error

List every call to `http.Error()`, `w.WriteHeader()`, or error-response helpers in the diff. For each, verify that execution does not continue to write additional data to `http.ResponseWriter`. Flag missing `return` statements after error responses.

### Pass W — Error wrapping and sentinel errors

The HyperFleet error model standard defines the canonical wrapping pattern: `fmt.Errorf("failed to get cluster %s: %w", id, err)` — always add context describing what the current function was doing, and always use `%w` to preserve the error chain. Bare `return errors.New("database error")` that discards the original error is explicitly prohibited.

List every `return err` and `return fmt.Errorf(...)` in the diff. For each, check:

- **Missing context** — flag bare `return err` when the function could add context with `fmt.Errorf("operation failed: %w", err)`. Context should describe what the current function was trying to do
- **Wrong verb** — flag `fmt.Errorf("...: %v", err)` or `fmt.Errorf("...: %s", err)` when `%w` should be used to preserve the error chain for `errors.Is()`/`errors.As()` callers
- **Sentinel error comparison** — flag `err == ErrSomething` or `err.Error() == "..."` comparisons. Suggest `errors.Is(err, ErrSomething)` or `errors.As(err, &target)` which work correctly with wrapped errors
- **Error message style** — flag error messages that start with uppercase or end with punctuation, per Go conventions (errors should be lowercase, no trailing period, composable via wrapping)

Do NOT flag:
- `return err` at the top of a call stack (e.g., in `main()` or HTTP handler where context is already clear)
- Intentional use of `%v` to break the error chain (when documented with a comment)
- Third-party errors that don't follow Go conventions

## Group 2 — Concurrency and goroutine safety (passes D + E + K)

### Pass D — Concurrency safety

List every variable captured by a goroutine or closure in the diff, AND every variable accessed from HTTP handlers (which run in separate goroutines). For each, verify proper synchronization (mutex, atomic, channel). Flag unprotected shared reads/writes.

### Pass E — Goroutine lifecycle

List every goroutine started in the diff. For each, verify it has a clear shutdown mechanism (context, channel, WaitGroup). Flag fire-and-forget goroutines with no way to stop them.

### Pass K — Loop variable capture

List every `for` loop in the diff that launches a goroutine (`go func()`) or creates a closure. For each, check if the closure references the loop iteration variable directly. Flag captures where the variable is not passed as a function argument or re-bound with a local copy. Note: Go 1.22+ fixes this with per-iteration scoping — check the project's `go.mod` minimum Go version before flagging.

## Group 3 — Exhaustiveness and guards (passes A + F)

### Pass A — Switch/select exhaustiveness

List every `switch` and `select` statement added or modified in the diff. For each, verify it has a `default` case (or explicitly handles all known values). Flag missing `default` as a bug when unrecognized input would silently fall through to a wrong behavior.

### Pass F — Nil/bounds safety

List every array/slice indexing and pointer dereference in the diff on values that could be nil or empty. For each, verify a guard exists. Flag potential panics.

## Group 4 — Resource and context lifecycle (passes C + J + L)

### Pass C — Resource lifecycle

List every resource created in the diff (files, connections, contexts with cancel, HTTP bodies, exporters, tracer providers, database transactions). For each, trace ALL code paths (including early `return` and error branches) to verify cleanup (`defer Close()`/`cancel()`/`Shutdown()`). Flag any path where cleanup is skipped.

### Pass J — Context propagation

List every function in the diff that receives a `context.Context` parameter. For each, check if any downstream call inside that function uses `context.Background()` or `context.TODO()` instead of passing the received context. Flag instances where the parent context is available but not propagated.

### Pass L — `time.After` in loops

List every use of `time.After` in the diff. For each, check if it appears inside a `for` loop or inside a `select` that is itself inside a loop. Flag these as memory leaks — each iteration allocates a timer that is not garbage collected until it fires. Suggest `time.NewTimer` with `Reset()` instead.

## Group 5 — Code quality and struct completeness (passes G + N)

### Pass G — Constants and magic values

Identify package-level `var` declarations whose values never change and should be `const`. Flag inline literal strings used as fixed identifiers, config keys, filter expressions, or semantic values (e.g., `"gcp_pubsub"`, `"traceidratio"`, `"publish"`) — these should be named constants. Flag magic numbers used as thresholds, sizes, or multipliers.

### Pass N — Struct field initialization completeness

For each struct in the diff that has new fields added, find all constructors and factory functions (e.g., `NewFoo()`, `newFoo()`) that create instances of that struct. Verify each constructor initializes the new field. Flag constructors that produce a zero-value for the new field when a meaningful default is expected.

## Group 6 — Testing and coverage (passes I + Z + AA)

### Pass I — Test coverage for new code

List every new exported function, method, or significant code path added in the diff. For each, check if there is a corresponding test (in a `_test.go` file or test directory) that exercises it. Flag new logic without any test coverage.

### Pass Z — Test structure patterns

List every test function added or modified in the diff. For each, check:

- **Table-driven tests** — flag test functions that repeat similar setup/assertion patterns for different inputs. Suggest converting to table-driven tests with `t.Run()` subtests
- **Missing `t.Helper()`** — flag test helper functions (called from multiple tests, accept `*testing.T`) that don't call `t.Helper()`. Without it, test failure line numbers point to the helper, not the caller
- **Missing `t.Parallel()`** — flag test functions that are independent (don't share mutable state, don't use shared resources) but don't call `t.Parallel()`. Only flag when the test file already uses `t.Parallel()` in other tests (respect existing convention)
- **Assertion messages** — flag assertions using `t.Error()` or `t.Fatal()` without descriptive messages that would help diagnose failures (e.g., bare `t.Error(err)` without context)

Do NOT flag:
- Tests that intentionally cannot be parallel (shared database, global state)
- Small test files with 1-2 simple test cases where table-driven tests would add unnecessary complexity

### Pass AA — Test isolation and cleanup

List every test function in the diff that creates resources (files, goroutines, servers, database records, environment variable changes, global state modifications). For each, check:

- **Cleanup** — flag tests that modify global state (e.g., `os.Setenv`, package-level variables) without restoring it. Suggest `t.Cleanup()` or `t.Setenv()` (Go 1.17+)
- **Temporary files** — flag tests that create files without using `t.TempDir()` (Go 1.15+) or explicit cleanup
- **Test server cleanup** — flag `httptest.NewServer` without `defer s.Close()`
- **Goroutine leaks in tests** — flag tests that start goroutines without ensuring they complete before the test ends (missing `sync.WaitGroup`, channel synchronization, or context cancellation)

Do NOT flag:
- Tests using `t.Cleanup()` or `defer` for resource management (already handled)
- Integration test files that are clearly marked and expected to have external dependencies

## Group 7 — Naming and code organization (passes X + Y)

### Pass X — Naming conventions

List every new or renamed identifier (variable, function, type, const, package) in the diff. For each, check:

- **Stuttering** — flag exported identifiers that repeat the package name (e.g., package `user` with type `UserService` should be `Service`; `user.UserID` should be `user.ID`)
- **Acronym casing** — flag inconsistent acronym casing: `Id` should be `ID`, `Url` should be `URL`, `Http` should be `HTTP`, `Api` should be `API`, `Json` should be `JSON`, `Sql` should be `SQL`
- **Getter naming** — flag methods named `GetX()` that are simple field accessors. Go convention is `X()` not `GetX()` (setters remain `SetX()`)
- **Interface naming** — flag single-method interfaces that don't follow the `-er` suffix convention (e.g., an interface with method `Read` should be `Reader`, not `Readable` or `IReader`)

Do NOT flag:
- Names required by interfaces from external packages (e.g., `ServeHTTP` from `net/http`)
- Names in generated code or protobuf definitions
- Names that would conflict with existing identifiers if renamed

### Pass Y — Function complexity

List every function added or modified in the diff that is longer than 50 lines or has more than 4 levels of nesting. For each, check:

- **Guard clauses** — flag deep nesting caused by `if err != nil` or validation checks that could be early returns
- **Function length** — flag functions over 60 lines that could be split into smaller, well-named helpers for readability
- **Cyclomatic complexity** — flag functions with more than 5 branching paths (if/else, switch cases, loops) suggesting decomposition

Do NOT flag:
- Table-driven test functions that are long but structurally simple (list of test cases)
- Generated code
- Functions that are inherently sequential (e.g., multi-step initialization) where splitting would hurt readability

## Group 8 — Security (passes R + S + T)

This group is **language-agnostic** and runs for every PR regardless of file types.

### Pass R — Injection vulnerabilities

Per the HyperFleet error model standard, user input in error messages must be sanitized to prevent injection.

List every place in the diff where external input (HTTP parameters, environment variables, user-provided strings, file content) is incorporated into:

- **SQL queries** — flag string concatenation or `fmt.Sprintf` used to build queries instead of parameterized queries / prepared statements
- **Shell commands** — flag `exec.Command`, `os/exec`, subprocess calls, or equivalent where arguments are not properly sanitized or come directly from user input
- **Template rendering** — flag `html/template` or equivalent usage where user input is passed without escaping

Do NOT flag:
- Queries built with query-builder libraries that handle parameterization (e.g., `squirrel`, `sqlx` named queries)
- Commands where all arguments are hardcoded constants

### Pass S — Secrets exposure

Per the HyperFleet logging specification, the following MUST be redacted or omitted from logs: API tokens and credentials, passwords and secrets, cloud provider access keys, and PII. Per the error model standard, production API responses MUST NOT expose stack traces or internal error messages that may reveal system details.

List every log statement, error message, HTTP response body, and metric label in the diff. For each, check if it could expose sensitive data:

- **Credentials** — passwords, tokens, API keys, certificates, private keys
- **PII** — email addresses, usernames in combination with auth data
- **Full request/response bodies** — that may contain auth headers or tokens
- **Stack traces in API responses** — flag error responses that include stack traces or internal implementation details (per error model standard, log full details internally but sanitize external responses)

Flag instances where sensitive data is logged, returned in error responses, or included in metric labels. Suggest redaction or structured logging that excludes sensitive fields.

Do NOT flag:
- Logging of request IDs, trace IDs, or non-sensitive metadata
- Debug-level logs that only log field names (not values)

### Pass T — Path traversal and input validation

List every place in the diff where external input is used to construct file paths, URLs, or resource identifiers. For each, check:

- **Path traversal** — flag if `../` sequences or absolute paths from user input are not sanitized (e.g., missing `filepath.Clean()`, `filepath.Rel()`, or base-path validation)
- **Input validation at system boundaries** — for HTTP handlers, CLI argument parsers, webhook receivers, and config file readers: flag missing validation of required fields, type assertions without checks, or unbounded input (e.g., no max length on string fields, no max size on uploaded files)

Do NOT flag:
- Internal function calls where input comes from trusted, already-validated sources
- Config files that are not user-facing

## Group 9 — Code hygiene (passes O + P + Q)

This group is **language-agnostic** and runs for every PR regardless of file types.

### Pass O — TODOs/FIXMEs without ticket

List every `TODO`, `FIXME`, `HACK`, and `XXX` comment added or modified in the diff. For each, check whether it references a JIRA ticket ID (e.g., `// TODO(HYPERFLEET-123): ...` or `// FIXME HYPERFLEET-456: ...`). Flag TODOs that have no ticket reference — these become invisible technical debt. Suggest adding a ticket ID or creating a JIRA ticket to track the work.

Do NOT flag:
- TODOs that already reference a ticket ID in any common format (`TODO(TICKET-123)`, `TODO TICKET-123:`, `TODO: TICKET-123 -`)
- TODOs in test files that describe test improvements with clear intent (e.g., `// TODO: add table-driven test cases for edge X`)

### Pass P — Log level appropriateness

List every log statement added or modified in the diff (e.g., `log.Error`, `log.Warn`, `log.Info`, `log.Debug`, `slog.Error`, `slog.Info`, `logger.Error`, `logger.Info`, `klog.*`). For each, evaluate whether the log level matches the severity of the event:

- **Error** — should only be used for conditions that require human intervention or indicate a broken invariant. Flag `log.Error` used for expected/recoverable conditions (e.g., resource not found, validation failure, retry-able transient errors)
- **Warn** — should be used for unexpected but recoverable situations. Flag `log.Warn` used for normal operational events
- **Info** — should be used for significant operational events (startup, shutdown, configuration changes). Flag `log.Info` inside tight loops or hot paths where it would produce excessive output
- **Debug** — should be used for detailed diagnostic information. Flag `log.Debug` that contains sensitive data (credentials, tokens, full request bodies)

Also flag:
- Log statements inside loops that execute per-item without rate limiting or level guarding — these can produce log spam at scale
- Inconsistent log levels for the same type of event within the PR (e.g., logging "connection failed" as Error in one place and Warn in another)

### Pass Q — Typo detection

List every added or modified line in the diff that contains text written by humans (identifiers, comments, strings, log messages, error messages, documentation, YAML values, markdown prose). For each, check for:

- **Misspelled words** in comments, doc strings, log/error messages, markdown, and YAML descriptions
- **Misspelled identifiers** — variable names, function names, struct fields, constants, and type names that contain common English misspellings (e.g., `recieve` instead of `receive`, `seperator` instead of `separator`, `retreive` instead of `retrieve`)
- **Inconsistent spelling** within the PR — the same concept spelled differently in different places (e.g., `canceled` vs `cancelled`, `color` vs `colour`)

Do NOT flag:
- Intentional abbreviations or domain-specific jargon (e.g., `k8s`, `ctx`, `cfg`, `mgr`, `msg`, `req`, `resp`)
- Third-party identifiers (imported package names, external API fields)
- Code-generated content
- Single-letter variables in small scopes

## Group 10 — Performance (passes U + V)

### Pass U — Allocation and preallocation patterns

List every slice or map creation in the diff. For each, check:

- **Slice preallocation** — if the final size is known or estimable (e.g., `len(input)`), flag `var s []T` or `make([]T, 0)` without capacity hint. Suggest `make([]T, 0, expectedLen)`
- **Map preallocation** — same pattern: flag `make(map[K]V)` when the expected size is known. Suggest `make(map[K]V, expectedLen)`
- **String concatenation in loops** — flag `+=` on strings inside loops. Suggest `strings.Builder`
- **Unnecessary allocations in hot paths** — flag creating new slices, maps, or structs inside tight loops when they could be allocated once outside the loop and reused or reset

Do NOT flag:
- Small, fixed-size collections (e.g., `[]string{"a", "b"}`)
- One-time initialization code (e.g., in `main()` or `init()`)

### Pass V — Defer and performance anti-patterns

List every `defer` statement in the diff. For each, check:

- **Defer in tight loops** — flag `defer` inside `for` loops, as deferred calls accumulate until the function returns, not per iteration. Suggest extracting the loop body into a separate function or calling cleanup explicitly
- **N+1 query patterns** — in code that iterates over a collection, flag individual database/API calls per item when a batch operation is available (e.g., fetching one record at a time in a loop instead of a single query with `WHERE IN`)

Do NOT flag:
- `defer` in functions that return after the loop (single iteration patterns)
- Loops with very small, bounded iteration counts (e.g., iterating over 2-3 known items)
