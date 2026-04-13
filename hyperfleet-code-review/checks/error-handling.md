# Error handling and wrapping

**Go-specific** — skip when the diff contains no `.go` files.

## Error handling completeness

List every function call in the diff that returns an `error`. For each, verify the error is checked. Flag silently ignored errors (`_, _ :=` or bare calls on error-returning functions).

## Log-and-continue vs return

List every error-logging statement in the diff where execution continues after the log. For each, verify this is intentional graceful degradation and not a missing `return`.

## HTTP handler missing return after error

List every call to `http.Error()`, `w.WriteHeader()`, or error-response helpers in the diff. For each, verify that execution does not continue to write additional data to `http.ResponseWriter`. Flag missing `return` statements after error responses.

## Error wrapping and sentinel errors

Apply the requirements from the HyperFleet **Error Model Standard** fetched in the Standards section. The standard defines the canonical wrapping pattern, prohibited patterns, and all error-handling rules — do not use hardcoded rules. If the standard was not fetched or is partial, emit a mandatory finding stating "required Error Model Standard unavailable" with details and skip this pass.

List every `return err` and `return fmt.Errorf(...)` in the diff. For each, check against the requirements defined in the **Error Model Standard**.
