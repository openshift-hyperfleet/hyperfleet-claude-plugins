# Group 5 — Code quality and struct completeness (passes 5.A + 5.B)

### Pass 5.A — Constants and magic values

Identify package-level `var` declarations whose values never change and should be `const`. Flag inline literal strings used as fixed identifiers, config keys, filter expressions, or semantic values (e.g., `"gcp_pubsub"`, `"traceidratio"`, `"publish"`) — these should be named constants. Flag magic numbers used as thresholds, sizes, or multipliers.

### Pass 5.B — Struct field initialization completeness

For each struct in the diff that has new fields added, find all constructors and factory functions (e.g., `NewFoo()`, `newFoo()`) that create instances of that struct. Verify each constructor initializes the new field. Flag constructors that produce a zero-value for the new field when a meaningful default is expected.
