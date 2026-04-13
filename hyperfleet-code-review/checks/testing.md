# Testing and coverage

**Go-specific** — skip when the diff contains no `.go` files.

## Test coverage for new code

List every new exported function, method, or significant code path added in the diff. For each, check if there is a corresponding test (in a `_test.go` file or test directory) that exercises it. Flag new logic without any test coverage.

## Test structure patterns

List every test function added or modified in the diff. For each, check:

- **Table-driven tests** — flag test functions that repeat similar setup/assertion patterns for different inputs. Suggest converting to table-driven tests with `t.Run()` subtests
- **Missing `t.Helper()`** — flag test helper functions (called from multiple tests, accept `*testing.T`) that don't call `t.Helper()`. Without it, test failure line numbers point to the helper, not the caller
- **Missing `t.Parallel()`** — flag test functions that are independent (don't share mutable state, don't use shared resources) but don't call `t.Parallel()`. Only flag when the test file already uses `t.Parallel()` in other tests (respect existing convention)
- **Assertion messages** — flag assertions using `t.Error()` or `t.Fatal()` without descriptive messages that would help diagnose failures (e.g., bare `t.Error(err)` without context)

Do NOT flag:
- Tests that intentionally cannot be parallel (shared database, global state)
- Small test files with 1-2 simple test cases where table-driven tests would add unnecessary complexity

## Test isolation and cleanup

List every test function in the diff that creates resources (files, goroutines, servers, database records, environment variable changes, global state modifications). For each, check:

- **Cleanup** — flag tests that modify global state (e.g., `os.Setenv`, package-level variables) without restoring it. Suggest `t.Cleanup()` or `t.Setenv()` (Go 1.17+)
- **Temporary files** — flag tests that create files without using `t.TempDir()` (Go 1.15+) or explicit cleanup
- **Test server cleanup** — flag `httptest.NewServer` without `defer s.Close()`
- **Goroutine leaks in tests** — flag tests that start goroutines without ensuring they complete before the test ends (missing `sync.WaitGroup`, channel synchronization, or context cancellation)

Do NOT flag:
- Tests using `t.Cleanup()` or `defer` for resource management (already handled)
- Integration test files that are clearly marked and expected to have external dependencies
