# Exhaustiveness and guards

**Go-specific** — skip when the diff contains no `.go` files.

## Switch/select exhaustiveness

List every `switch` and `select` statement added or modified in the diff. For each, verify it has a `default` case (or explicitly handles all known values). Flag missing `default` as a bug when unrecognized input would silently fall through to a wrong behavior.

## Nil/bounds safety

List every array/slice indexing and pointer dereference in the diff on values that could be nil or empty. For each, verify a guard exists. Flag potential panics.
