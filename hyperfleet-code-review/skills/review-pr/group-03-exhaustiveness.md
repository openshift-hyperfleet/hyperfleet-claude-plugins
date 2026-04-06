# Group 3 — Exhaustiveness and guards (passes 3a + 3b)

**Go-specific** — skip when the diff contains no `.go` files.

## Pass 3a — Switch/select exhaustiveness

List every `switch` and `select` statement added or modified in the diff. For each, verify it has a `default` case (or explicitly handles all known values). Flag missing `default` as a bug when unrecognized input would silently fall through to a wrong behavior.

## Pass 3b — Nil/bounds safety

List every array/slice indexing and pointer dereference in the diff on values that could be nil or empty. For each, verify a guard exists. Flag potential panics.
