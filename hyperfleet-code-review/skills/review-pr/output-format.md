# Output Format and Interactive Behavior

## Initial summary

First, show a brief summary:

**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** N (new, excluding already commented ones)

## Impact warnings (optional, only when impact analysis found files outside the PR)

If the impact analysis (step 4b) found files that **should have been updated but are NOT part of the PR**, show them in a separate section **before** the recommendations. These are NOT numbered recommendations — they are informational warnings so the author is aware.

**GitHub comment:**

### Impact warnings

The following files are **NOT in this PR** but may need updating due to changes in the diff:

- **`docs/development.md`** (lines 31, 33, 40) — Still references `gcp.json` which was renamed to `nodepool-request.json` in this PR

These are outside the PR scope and shown for awareness only.

If there are no impact warnings, skip this section entirely.

## When N = 0 (no new recommendations)

**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** 0

No additional recommendations! Existing comments already cover the relevant points.

## Current recommendation (when N > 0)

After the summary (and impact warnings, if any), show "Showing recommendation 1 of N:" followed by the first recommendation. Show only ONE recommendation at a time:

---

## Recommendation 1/N - Brief problem title

**File:** [`path/to/file.ext:X`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{path_sha256}RX)
**Category:** [Bug/Security/Architecture/JIRA/Standards/Inconsistency/Deprecated/Pattern/Improvement]

**Problem:**
[Clear description of the problem]

**GitHub comment (ready to copy-paste):**

~~~markdown
**Category:** [same category value from above]

[comment written as a human (casual and direct tone, not AI-generated sounding), formatted in Markdown ready to copy and paste on GitHub, with suggested fix when applicable. Use backtick fenced code blocks (` ``` `) with language identifiers for all code snippets.]
~~~

---

After showing the recommendation, use `AskUserQuestion` to prompt the user. The available options depend on the mode:

- **Self-review mode (author + matching branch):** "next", "all", "fix", or a recommendation number
- **Comment mode (not the PR author):** "next", "all", "comment", or a recommendation number
- **Read-only (author but branch mismatch):** "next", "all", or a recommendation number

## Doc <-> Code inconsistency variant

When the recommendation is a Doc <-> Code mismatch (from step 4c), use this format instead — showing both files involved:

---

## Recommendation 1/N - Brief problem title

**Doc:** [`path/to/design-doc.md:X`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{doc_path_sha256}RX)
**Code:** [`path/to/implementation.go:Y`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{code_path_sha256}RY) (or "missing" if the code doesn't exist)
**Category:** Inconsistency

**Problem:**
[Clear description of what the doc says vs what the code does (or doesn't do)]

**GitHub comment (ready to copy-paste):**

~~~markdown
**Category:** Inconsistency

[comment written as a human, referencing both files so the reviewer can cross-check. Use backtick fenced code blocks (` ``` `) with language identifiers for all code snippets.]
~~~

---

After showing the recommendation, use `AskUserQuestion` with the same options as above.

## Interactive behavior

Use `AskUserQuestion` for all user interactions. The question text should list the available options clearly.

- **"next"** or **"n"**: shows the next recommendation
- **"fix"**: (self-review mode only) applies the suggested fix using Edit/Write tools, then shows the next recommendation automatically
- **"comment"**: (comment mode only, when not self-review) posts the recommendation as an inline review comment on the PR via `gh api`, then shows the next recommendation automatically
- **"all"** or **"list"**: shows a summary table with all:

| # | File(s) | Problem |
|---|---------|---------|
| 1 | [`path/file.ext:42`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{path_sha256}R42) | Brief description |
| 2 | [`doc.md:10`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{doc_sha256}R10) <-> [`impl.go:55`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{impl_sha256}R55) | Doc <-> Code mismatch description |
| ... | ... | ... |

Type "1" to "N" to see details of a specific recommendation.

- **Number (e.g. "3")**: shows details of the specific recommendation
- **Unrecognized input**: remind the user of the available commands via `AskUserQuestion`
- **When done**: "Review complete! All N recommendations have been shown." — then show the follow-up ticket prompt (see below)

## Follow-up ticket suggestion

After all recommendations have been shown (or when N = 0), if there were **impact warnings** or findings that are outside the PR scope, use `AskUserQuestion` to offer creating follow-up JIRA tickets. Options: "ticket" (create tickets for impact warnings) or "done" (finish the review).

When the user chooses **"ticket"**:

For each impact warning, invoke the `jira-ticket-creator` skill (via the Skill tool) passing `<ticket-type> <summary>` as the argument — e.g., `Task Update CLAUDE.md plugin table counts`. Choose the ticket type based on the impact warning semantics: "Bug" for defects, "Task" for general work, "Story" for feature gaps. The skill handles all other required fields (story points, activity type, priority, component) internally.

If there are no impact warnings, skip this section entirely.

## Code block rule — rendering and copy-paste

The "GitHub comment" section MUST be wrapped in a **tilde fence** (`~~~markdown`) so the user can copy-paste the raw Markdown directly into GitHub. Inside the tilde fence, use **backtick fences** (` ``` `) with language identifiers for code snippets. This nesting works because tildes and backticks are different delimiters.

### Example of correct output

**GitHub comment (ready to copy-paste):**

~~~markdown
**Category:** Bug

`Default.New()` has a nil guard on `tx.DB` but `Test.New()` skips it. Add the same guard:

```go
if tx.DB == nil {
    panic("transaction context contains nil DB handle")
}
```
~~~

### Rules

1. The outer fence for GitHub comments MUST use tildes (`~~~markdown`)
2. Code snippets inside MUST use backtick fences (` ```go `, ` ```yaml `, etc.)
3. Always include a language identifier — never use bare ` ``` `
4. Every opening fence MUST have a matching closing fence
