# Group 7 — Naming and code organization (passes 7a + 7b)

**Go-specific** — skip when the diff contains no `.go` files.

## Pass 7a — Naming conventions

List every new or renamed identifier (variable, function, type, const, package) in the diff. Apply any project-specific naming conventions from the HyperFleet standards fetched in step 4b in addition to the standard Go conventions below. If the standards were not fetched, apply only the Go conventions. For each, check:

- **Stuttering** — flag exported identifiers that repeat the package name (e.g., package `user` with type `UserService` should be `Service`; `user.UserID` should be `user.ID`)
- **Acronym casing** — flag inconsistent acronym casing: `Id` should be `ID`, `Url` should be `URL`, `Http` should be `HTTP`, `Api` should be `API`, `Json` should be `JSON`, `Sql` should be `SQL`
- **Getter naming** — flag methods named `GetX()` that are simple field accessors. Go convention is `X()` not `GetX()` (setters remain `SetX()`)
- **Interface naming** — flag single-method interfaces that don't follow the `-er` suffix convention (e.g., an interface with method `Read` should be `Reader`, not `Readable` or `IReader`)

Do NOT flag:
- Names required by interfaces from external packages (e.g., `ServeHTTP` from `net/http`)
- Names in generated code or protobuf definitions
- Names that would conflict with existing identifiers if renamed

## Pass 7b — Function complexity

List every function added or modified in the diff that is longer than 50 lines or has more than 4 levels of nesting. For each, check:

- **Guard clauses** — flag deep nesting caused by `if err != nil` or validation checks that could be early returns
- **Function length** — flag functions over 60 lines that could be split into smaller, well-named helpers for readability
- **Cyclomatic complexity** — flag functions with more than 5 branching paths (if/else, switch cases, loops) suggesting decomposition

Do NOT flag:
- Table-driven test functions that are long but structurally simple (list of test cases)
- Generated code
- Functions that are inherently sequential (e.g., multi-step initialization) where splitting would hurt readability
