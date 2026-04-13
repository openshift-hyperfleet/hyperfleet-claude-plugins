# Code quality and struct completeness

**Go-specific** — skip when the diff contains no `.go` files.

## Constants and magic values

Identify package-level `var` declarations whose values never change and should be `const`. Flag inline literal strings used as fixed identifiers, config keys, filter expressions, or semantic values — these should be named constants. Flag magic numbers used as thresholds, sizes, or multipliers. If the HyperFleet standards fetched in the Standards section define naming or configuration conventions for constants, apply those conventions when evaluating findings. If the standard was not fetched, skip convention-based validation and focus only on the hardcoded rules (package-level var, inline literals, magic numbers).

## Struct field initialization completeness

For each struct in the diff that has new fields added, find all constructors and factory functions (e.g., `NewFoo()`, `newFoo()`) that create instances of that struct. Verify each constructor initializes the new field. Flag constructors that produce a zero-value for the new field when a meaningful default is expected.
