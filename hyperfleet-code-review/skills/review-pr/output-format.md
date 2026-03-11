# Output Format and Interactive Behavior

## Initial summary

First, show a brief summary:

```text
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** N (new, excluding already commented ones)

Showing recommendation 1 of N:
```

## Impact warnings (optional, only when impact analysis found files outside the PR)

If step 7 (impact analysis) found files that **should have been updated but are NOT part of the PR**, show them in a separate section **before** the recommendations. These are NOT numbered recommendations — they are informational warnings so the author is aware.

**GitHub comment:**

> ### Impact warnings
>
> The following files are **NOT in this PR** but may need updating due to changes in the diff:
>
> - **`docs/development.md`** (lines 31, 33, 40) — Still references `gcp.json` which was renamed to `nodepool-request.json` in this PR
>
> These are outside the PR scope and shown for awareness only.

If there are no impact warnings, skip this section entirely.

## When N = 0 (no new recommendations)

```text
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** 0

No additional recommendations! Existing comments already cover the relevant points.
```

## Current recommendation (when N > 0)

Show only ONE recommendation at a time:

```text
---

## Recommendation 1/N - Brief problem title

**File:** `path/to/file.ext`
**Line:** X
**Priority:** [Bug/Security/Architecture/JIRA/Inconsistency/Deprecated/Pattern/Improvement]

**Problem:**
[Clear description of the problem]

**GitHub comment:**

> **Priority:** [same priority value from above]
>
> [comment written as a human (casual and direct tone, not AI-generated sounding), formatted in Markdown ready to copy and paste on GitHub, with suggested fix when applicable]

---

> Type **"next"** or **"n"** to see the next recommendation.
> Type **"all"** to see a summary list of all recommendations.
```

## Doc <-> Code inconsistency variant

When the recommendation is a Doc <-> Code mismatch (from step 9), use this format instead — showing both files involved:

```text
---

## Recommendation 1/N - Brief problem title

**Doc:** `path/to/design-doc.md` (line X)
**Code:** `path/to/implementation.go` (line Y — or "missing" if the code doesn't exist)
**Priority:** Inconsistency

**Problem:**
[Clear description of what the doc says vs what the code does (or doesn't do)]

**GitHub comment:**

> **Priority:** Inconsistency
>
> [comment written as a human, referencing both files so the reviewer can cross-check]

---

> Type **"next"** or **"n"** to see the next recommendation.
> Type **"all"** to see a summary list of all recommendations.
```

## Notification

After showing each recommendation (including the first one), notify the user using the bundled cross-platform notification script. Use the **absolute path** from the `Notify script` entry in Dynamic context (NOT the `CLAUDE_SKILL_DIR` variable, which is not available at runtime):

```bash
bash "/absolute/path/from/dynamic-context/notify.sh" "Review PR" "Recommendation X/N ready"
```

Where `X` is the current recommendation number and `N` is the total count. For example: `"Recommendation 3/7 ready"`.

## Interactive behavior

- **"next"** or **"n"**: shows the next recommendation
- **"all"** or **"list"**: shows a summary table with all:

```text
| # | File(s) | Line | Problem |
|---|---------|------|---------|
| 1 | path/file.ext | 42 | Brief description |
| 2 | doc.md <-> impl.go | 10, 55 | Doc <-> Code mismatch description |
| ... | ... | ... | ... |

> Type "1" to "N" to see details of a specific recommendation.
```

- **Number (e.g. "3")**: shows details of the specific recommendation
- **Unrecognized input**: remind the user of the available commands ("next", "all", or a number)
- **When done**: "Review complete! All N recommendations have been shown."
