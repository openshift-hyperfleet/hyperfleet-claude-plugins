# Output Format and Interactive Behavior

## Initial summary

First, show a brief summary:

```text
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** N (new, excluding already commented ones)
```

## Impact warnings (optional, only when impact analysis found files outside the PR)

If the impact analysis (step 4b) found files that **should have been updated but are NOT part of the PR**, show them in a separate section **before** the recommendations. These are NOT numbered recommendations — they are informational warnings so the author is aware.

**GitHub comment:**

```markdown
### Impact warnings

The following files are **NOT in this PR** but may need updating due to changes in the diff:

- **`docs/development.md`** (lines 31, 33, 40) — Still references `gcp.json` which was renamed to `nodepool-request.json` in this PR

These are outside the PR scope and shown for awareness only.
```

If there are no impact warnings, skip this section entirely.

## When N = 0 (no new recommendations)

```text
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** 0

No additional recommendations! Existing comments already cover the relevant points.
```

## Current recommendation (when N > 0)

After the summary (and impact warnings, if any), show "Showing recommendation 1 of N:" followed by the first recommendation. Show only ONE recommendation at a time:

```text
---

## Recommendation 1/N - Brief problem title

**File:** `path/to/file.ext`
**Line:** X
**Category:** [Bug/Security/Architecture/JIRA/Standards/Inconsistency/Deprecated/Pattern/Improvement]

**Problem:**
[Clear description of the problem]

**GitHub comment:**

```markdown
**Category:** [same category value from above]

[comment written as a human (casual and direct tone, not AI-generated sounding), formatted in Markdown ready to copy and paste on GitHub, with suggested fix when applicable]
```

---

Type **"next"** or **"n"** to see the next recommendation.
Type **"all"** to see a summary list of all recommendations.
```

## Doc <-> Code inconsistency variant

When the recommendation is a Doc <-> Code mismatch (from step 4c), use this format instead — showing both files involved:

```text
---

## Recommendation 1/N - Brief problem title

**Doc:** `path/to/design-doc.md` (line X)
**Code:** `path/to/implementation.go` (line Y — or "missing" if the code doesn't exist)
**Category:** Inconsistency

**Problem:**
[Clear description of what the doc says vs what the code does (or doesn't do)]

**GitHub comment:**

```markdown
**Category:** Inconsistency

[comment written as a human, referencing both files so the reviewer can cross-check]
```

---

Type **"next"** or **"n"** to see the next recommendation.
Type **"all"** to see a summary list of all recommendations.
```

## Interactive behavior

- **"next"** or **"n"**: shows the next recommendation
- **"all"** or **"list"**: shows a summary table with all:

```text
| # | File(s) | Line | Problem |
|---|---------|------|---------|
| 1 | path/file.ext | 42 | Brief description |
| 2 | doc.md <-> impl.go | 10, 55 | Doc <-> Code mismatch description |
| ... | ... | ... | ... |

Type "1" to "N" to see details of a specific recommendation.
```

- **Number (e.g. "3")**: shows details of the specific recommendation
- **Unrecognized input**: remind the user of the available commands ("next", "all", or a number)
- **When done**: "Review complete! All N recommendations have been shown."
