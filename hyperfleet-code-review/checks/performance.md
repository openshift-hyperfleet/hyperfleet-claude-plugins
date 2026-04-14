# Performance

**Go-specific** — skip when the diff contains no `.go` files.

## Allocation and preallocation patterns

List every slice or map creation in the diff. For each, check:

- **Slice preallocation** — if the final size is known or estimable (e.g., `len(input)`), flag `var s []T` or `make([]T, 0)` without capacity hint. Suggest `make([]T, 0, expectedLen)`
- **Map preallocation** — same pattern: flag `make(map[K]V)` when the expected size is known. Suggest `make(map[K]V, expectedLen)`
- **String concatenation in loops** — flag `+=` on strings inside loops. Suggest `strings.Builder`
- **Unnecessary allocations in hot paths** — flag creating new slices, maps, or structs inside tight loops when they could be allocated once outside the loop and reused or reset

DO NOT flag:
- Small, fixed-size collections (e.g., `[]string{"a", "b"}`)
- One-time initialization code (e.g., in `main()` or `init()`)

## Defer and performance anti-patterns

List every `defer` statement in the diff. For each, check:

- **Defer in tight loops** — flag `defer` inside `for` loops, as deferred calls accumulate until the function returns, not per iteration. Suggest extracting the loop body into a separate function or calling cleanup explicitly
- **N+1 query patterns** — in code that iterates over a collection, flag individual database/API calls per item when a batch operation is available (e.g., fetching one record at a time in a loop instead of a single query with `WHERE IN`)

DO NOT flag:
- `defer` in loops with a statically known iteration count of 3 or fewer items (e.g.,
  `for _, item := range []string{"a", "b", "c"}`)
- `defer` in a loop that unconditionally executes exactly one iteration and returns
  immediately after (e.g., a `for range ch` that reads one value then returns)

DO flag (these are NOT exempt):
- `defer` in a loop that "usually returns early" or "often has one iteration" — ambiguous
  runtime behavior does not exempt the pattern
- `defer` in any loop where the iteration count depends on input or runtime state
