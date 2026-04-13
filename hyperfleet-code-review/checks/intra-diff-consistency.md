# Intra-diff consistency

This check is **language-agnostic** and runs for every diff regardless of file types.

If the standards fetch returned empty or errored, run only the consistency checks (items marked
*[consistency]* below), emit a mandatory "HyperFleet standards unavailable — skipping
standards-based validation" note in the output, and skip all items marked *[standards]*.

For patterns that appear more than once across different files in the diff, verify ALL occurrences
use the same approach **and** that the approach matches the HyperFleet standards (when available):

- *[consistency]* Synchronization primitives (some goroutines use `atomic`, others use plain `int`)
- *[consistency]* Test setup/teardown patterns (some tests restore global state, others don't)
- *[consistency]* Flag inconsistencies within the diff itself — if the author did it right in one
  place, they likely intended to do it everywhere
- *[standards]* Error handling style (some places check errors, others ignore) — compare against
  **Error Model Standard**
- *[standards]* Naming conventions — compare against **Naming Standard**
- *[standards]* Logging patterns — compare against **Logging Specification**
- *[standards]* Config access patterns — compare against **Config Standard**
- *[standards]* Flag deviations from team standards — if the diff introduces a pattern that
  contradicts a HyperFleet standard, flag it
