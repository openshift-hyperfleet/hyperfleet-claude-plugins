# Concurrency and goroutine safety

**Go-specific** — skip when the diff contains no `.go` files.

## Concurrency safety

List every variable captured by a goroutine or closure in the diff, AND every variable accessed from HTTP handlers (which run in separate goroutines). For each, verify proper synchronization (mutex, atomic, channel). Flag unprotected shared reads/writes.

## Goroutine lifecycle

List every goroutine started in the diff. For each, verify it has a clear shutdown mechanism (context, channel, WaitGroup). Flag fire-and-forget goroutines with no way to stop them.

## Loop variable capture

List every `for` loop in the diff that launches a goroutine (`go func()`) or creates a closure. For each, check if the closure references the loop iteration variable directly. Flag captures where the variable is not passed as a function argument or re-bound with a local copy. Note: Go 1.22+ fixes this with per-iteration scoping — check the project's `go.mod` minimum Go version before flagging.
