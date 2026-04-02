# Group 4 — Resource and context lifecycle (passes 4.A + 4.B + 4.C)

### Pass 4.A — Resource lifecycle

List every resource created in the diff (files, connections, contexts with cancel, HTTP bodies, exporters, tracer providers, database transactions). For each, trace ALL code paths (including early `return` and error branches) to verify cleanup (`defer Close()`/`cancel()`/`Shutdown()`). Flag any path where cleanup is skipped.

### Pass 4.B — Context propagation

Per the HyperFleet tracing standard (`tracing.md`), context MUST be propagated through the entire call chain so that trace/span IDs flow correctly. The standard defines specific rules for when `context.Background()` is acceptable (initialization only) and when it is not.

List every function in the diff that receives a `context.Context` parameter. For each, check if any downstream call inside that function uses `context.Background()` or `context.TODO()` instead of passing the received context. Flag instances where the parent context is available but not propagated.

### Pass 4.C — `time.After` in loops

List every use of `time.After` in the diff. For each, check if it appears inside a `for` loop or inside a `select` that is itself inside a loop. Flag these as memory leaks — each iteration allocates a timer that is not garbage collected until it fires. Suggest `time.NewTimer` with `Reset()` instead.
