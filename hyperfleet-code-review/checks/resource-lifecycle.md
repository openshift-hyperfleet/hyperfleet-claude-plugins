# Resource and context lifecycle

**Go-specific** — skip when the diff contains no `.go` files.

## Resource lifecycle

List every resource created in the diff (files, connections, contexts with cancel, HTTP bodies, exporters, tracer providers, database transactions). For each, trace ALL code paths (including early `return` and error branches) to verify cleanup (`defer Close()`/`cancel()`/`Shutdown()`). Flag any path where cleanup is skipped.

## Context propagation

List every function in the diff that receives a `context.Context` parameter. For each, check if any downstream call inside that function uses `context.Background()` or `context.TODO()` instead of passing the received context. Flag instances where the parent context is available but not propagated.

## `time.After` in loops

List every use of `time.After` in the diff. For each, check if it appears inside a `for` loop or inside a `select` that is itself inside a loop. Flag these as memory leaks — each iteration allocates a timer that is not garbage collected until it fires. Suggest `time.NewTimer` with `Reset()` instead.
