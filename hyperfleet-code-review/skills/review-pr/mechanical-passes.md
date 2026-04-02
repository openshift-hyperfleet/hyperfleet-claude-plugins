# Mechanical Code Pattern Checks

Launch 10 grouped agents in parallel using a single tool-call block (`subagent_type=general-purpose`). Each agent receives the diff content, the list of changed files, the HyperFleet standards fetched in the data-gathering step, and its group file from the `groups/` directory. Each agent must: list every instance found in the diff before evaluating it, then return a JSON array of findings (or empty array if none). Do NOT skip a check because "it looks fine" — enumerate first, then judge.

Groups 1–7 and 10 are written for Go codebases (HyperFleet's primary language). Skip these groups when the diff contains no `.go` files. If a check finds zero instances, it naturally produces no findings. Groups 8–9 are language-agnostic and run for every PR.

| Group | Name | Passes | Language | Standards Referenced | File |
|-------|------|--------|----------|---------------------|------|
| 1 | Error handling & wrapping | 1.A, 1.B, 1.C, 1.D | Go | `error-model.md` (1.D) | [group-01-error-handling.md](groups/group-01-error-handling.md) |
| 2 | Concurrency | 2.A, 2.B, 2.C | Go | — | [group-02-concurrency.md](groups/group-02-concurrency.md) |
| 3 | Exhaustiveness & guards | 3.A, 3.B | Go | — | [group-03-exhaustiveness.md](groups/group-03-exhaustiveness.md) |
| 4 | Resource & context lifecycle | 4.A, 4.B, 4.C | Go | `tracing.md` (4.B) | [group-04-resource-lifecycle.md](groups/group-04-resource-lifecycle.md) |
| 5 | Code quality & struct completeness | 5.A, 5.B | Go | — | [group-05-code-quality.md](groups/group-05-code-quality.md) |
| 6 | Testing & coverage | 6.A, 6.B, 6.C | Go | — | [group-06-testing.md](groups/group-06-testing.md) |
| 7 | Naming & code organization | 7.A, 7.B | Go | — | [group-07-naming.md](groups/group-07-naming.md) |
| 8 | Security | 8.A, 8.B, 8.C | All | `error-model.md` (8.A, 8.B), `logging-specification.md` (8.B) | [group-08-security.md](groups/group-08-security.md) |
| 9 | Code hygiene | 9.A, 9.B, 9.C | All | `commit-standard.md` (9.A), `logging-specification.md` (9.B) | [group-09-code-hygiene.md](groups/group-09-code-hygiene.md) |
| 10 | Performance | 10.A, 10.B | Go | — | [group-10-performance.md](groups/group-10-performance.md) |
