# Mechanical Code Pattern Checks

Launch 5 grouped agents in parallel using a single tool-call block (`subagent_type=general-purpose`). Each agent receives the diff content, the list of changed files, and the HyperFleet standards fetched in step 2. Each agent must: list every instance found in the diff before evaluating it, then return a JSON array of findings (or empty array if none). Do NOT skip a check because "it looks fine" — enumerate first, then judge.

These checks are written for Go codebases (HyperFleet's primary language). Skip all groups when the diff contains no `.go` files. If a check finds zero instances, it naturally produces no findings.

## Group 1 — Error handling (passes B + H + M)

### Pass B — Error handling completeness

List every function call in the diff that returns an `error`. For each, verify the error is checked. Flag silently ignored errors (`_, _ :=` or bare calls on error-returning functions).

### Pass H — Log-and-continue vs return

List every error-logging statement in the diff where execution continues after the log. For each, verify this is intentional graceful degradation and not a missing `return`.

### Pass M — HTTP handler missing return after error

List every call to `http.Error()`, `w.WriteHeader()`, or error-response helpers in the diff. For each, verify that execution does not continue to write additional data to `http.ResponseWriter`. Flag missing `return` statements after error responses.

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

## Group 5 — Code quality (passes G + I + N)

### Pass G — Constants and magic values

Identify package-level `var` declarations whose values never change and should be `const`. Flag inline literal strings used as fixed identifiers, config keys, filter expressions, or semantic values (e.g., `"gcp_pubsub"`, `"traceidratio"`, `"publish"`) — these should be named constants. Flag magic numbers used as thresholds, sizes, or multipliers.

### Pass I — Test coverage for new code

List every new exported function, method, or significant code path added in the diff. For each, check if there is a corresponding test (in a `_test.go` file or test directory) that exercises it. Flag new logic without any test coverage.

### Pass N — Struct field initialization completeness

For each struct in the diff that has new fields added, find all constructors and factory functions (e.g., `NewFoo()`, `newFoo()`) that create instances of that struct. Verify each constructor initializes the new field. Flag constructors that produce a zero-value for the new field when a meaningful default is expected.
