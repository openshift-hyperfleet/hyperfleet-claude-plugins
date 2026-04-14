# Exhaustiveness and guards

**Go-specific** — skip when the diff contains no `.go` files.

## Switch exhaustiveness

List every `switch` statement added or modified in the diff. For each, verify it either includes a `default` case or explicitly handles all known values of the switched type. Flag missing `default` as a bug when unrecognized input would silently fall through to a wrong behavior.

## Select blocking behavior

List every `select` statement added or modified in the diff. For each, verify the blocking vs non-blocking behavior is intentional:

- A `select` without `default` blocks until a channel is ready — flag if this appears unintentional (e.g., could deadlock or stall a goroutine indefinitely)
- A `select` with `default` is non-blocking — flag if `default` was added without clear intent, as it can introduce spin loops when used inside a `for` loop

## Nil/bounds safety

List every array/slice indexing and pointer dereference in the diff on values that could be nil or empty. For each, verify a guard exists. Flag potential panics.
