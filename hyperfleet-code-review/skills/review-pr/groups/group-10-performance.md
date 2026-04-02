# Group 10 — Performance (passes 10.A + 10.B)

### Pass 10.A — Allocation and preallocation patterns

List every slice or map creation in the diff. For each, check:

- **Slice preallocation** — if the final size is known or estimable (e.g., `len(input)`), flag `var s []T` or `make([]T, 0)` without capacity hint. Suggest `make([]T, 0, expectedLen)`
- **Map preallocation** — same pattern: flag `make(map[K]V)` when the expected size is known. Suggest `make(map[K]V, expectedLen)`
- **String concatenation in loops** — flag `+=` on strings inside loops. Suggest `strings.Builder`
- **Unnecessary allocations in hot paths** — flag creating new slices, maps, or structs inside tight loops when they could be allocated once outside the loop and reused or reset

Do NOT flag:
- Small, fixed-size collections (e.g., `[]string{"a", "b"}`)
- One-time initialization code (e.g., in `main()` or `init()`)

### Pass 10.B — Defer and performance anti-patterns

List every `defer` statement in the diff. For each, check:

- **Defer in tight loops** — flag `defer` inside `for` loops, as deferred calls accumulate until the function returns, not per iteration. Suggest extracting the loop body into a separate function or calling cleanup explicitly
- **N+1 query patterns** — in code that iterates over a collection, flag individual database/API calls per item when a batch operation is available (e.g., fetching one record at a time in a loop instead of a single query with `WHERE IN`)

Do NOT flag:
- `defer` in functions that return after the loop (single iteration patterns)
- Loops with very small, bounded iteration counts (e.g., iterating over 2-3 known items)
