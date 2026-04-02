# Group 1 — Error handling and wrapping (passes 1.A + 1.B + 1.C + 1.D)

### Pass 1.A — Error handling completeness

List every function call in the diff that returns an `error`. For each, verify the error is checked. Flag silently ignored errors (`_, _ :=` or bare calls on error-returning functions).

### Pass 1.B — Log-and-continue vs return

List every error-logging statement in the diff where execution continues after the log. For each, verify this is intentional graceful degradation and not a missing `return`.

### Pass 1.C — HTTP handler missing return after error

List every call to `http.Error()`, `w.WriteHeader()`, or error-response helpers in the diff. For each, verify that execution does not continue to write additional data to `http.ResponseWriter`. Flag missing `return` statements after error responses.

### Pass 1.D — Error wrapping and sentinel errors

Compare against the HyperFleet error model standard fetched in the data-gathering step. The standard defines the canonical wrapping pattern and prohibited patterns. If the standard was not fetched or is partial, emit a mandatory finding stating "required error model standard unavailable" with fetch error details, then continue with the baseline checks below.

List every `return err` and `return fmt.Errorf(...)` in the diff. For each, check:

- **Missing context** — flag bare `return err` when the function could add context with `fmt.Errorf("operation failed: %w", err)`. Context should describe what the current function was trying to do
- **Wrong verb** — flag `fmt.Errorf("...: %v", err)` or `fmt.Errorf("...: %s", err)` when `%w` should be used to preserve the error chain for `errors.Is()`/`errors.As()` callers
- **Sentinel error comparison** — flag `err == ErrSomething` or `err.Error() == "..."` comparisons. Suggest `errors.Is(err, ErrSomething)` or `errors.As(err, &target)` which work correctly with wrapped errors
- **Error message style** — flag error messages that start with uppercase or end with punctuation, per Go conventions (errors should be lowercase, no trailing period, composable via wrapping)

Do NOT flag:
- `return err` at the top of a call stack (e.g., in `main()` or HTTP handler where context is already clear)
- Intentional use of `%v` to break the error chain (when documented with a comment)
- Third-party errors that don't follow Go conventions
