# Output Format and Interactive Behavior

## Initial summary

First, show a brief summary:

**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** N (X blocking, Y nit)

## Impact warnings (optional, only when impact analysis found files outside the PR)

If the impact analysis (step 4c) found files that **should have been updated but are NOT part of the PR**, show them in a separate section **before** the recommendations. These are NOT numbered recommendations — they are informational warnings so the author is aware.

**GitHub comment:**

### Impact warnings

The following files are **NOT in this PR** but may need updating due to changes in the diff:

- **`docs/development.md`** (lines 31, 33, 40) — Still references `old-name.json` which was renamed to `new-name.json` in this PR

These are outside the PR scope and shown for awareness only.

If there are no impact warnings, skip this section entirely.

## When N = 0 (no new recommendations)

**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** 0 (0 blocking, 0 nit)

No additional recommendations! Existing comments already cover the relevant points.

## Current recommendation (when N > 0)

After the summary (and impact warnings, if any), show "Showing recommendation 1 of N:" followed by the first recommendation. Show only ONE recommendation at a time:

---

## Recommendation 1/N - Brief problem title

**File:** [`path/to/file.ext:X`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{path_sha256}RX)
**Category:** [Bug/Security/Architecture/JIRA/Standards/Inconsistency/Deprecated/Pattern/Improvement]
**Severity:** Blocking
**Confidence:** High

**Problem:**
[Clear description of the problem]

**GitHub comment (ready to copy-paste):**

~~~markdown
> [!WARNING]
> **Blocking**

**Category:** [same category value from above]

[comment written as a human (casual and direct tone, not AI-generated sounding), formatted in Markdown ready to copy and paste on GitHub, with suggested fix when applicable. Use backtick fenced code blocks (` ``` `) with language identifiers for all code snippets.]
~~~

### nit variant

For **nit** (non-blocking) recommendations, apply these differences:

1. Prefix the title with `nit:` — e.g., `## Recommendation 2/N - nit: Brief problem title`
2. Set severity to `nit` — i.e., `**Severity:** nit`
3. Set confidence to the appropriate level — i.e., `**Confidence:** High`, `Medium`, or `Low`
4. Use a GitHub `[!TIP]` alert instead of `[!WARNING]` in the GitHub comment:

~~~markdown
> [!TIP]
> **nit** — non-blocking suggestion

**Category:** [same category value from above]

[comment content]
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

(Or `## Recommendation 1/N - nit: Brief problem title` for non-blocking items)

**Doc:** [`path/to/design-doc.md:X`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{doc_path_sha256}RX)
**Code:** [`path/to/implementation.go:Y`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{code_path_sha256}RY) (or "missing" if the code doesn't exist)
**Category:** Inconsistency
**Severity:** Blocking (or nit)
**Confidence:** High (or Medium, or Low)

**Problem:**
[Clear description of what the doc says vs what the code does (or doesn't do)]

**GitHub comment (ready to copy-paste):**

~~~markdown
> [!WARNING]
> **Blocking**

**Category:** Inconsistency

[comment written as a human, referencing both files so the reviewer can cross-check. Use backtick fenced code blocks (` ``` `) with language identifiers for all code snippets.]
~~~

(For **nit** items, apply the same nit variant rules: prefix the title with `nit:`, set severity to `nit`, and use `[!TIP]` alert with `**nit** — non-blocking suggestion` instead of `[!WARNING]` alert in the GitHub comment.)

---

After showing the recommendation, use `AskUserQuestion` with the same options as above.

## Interactive behavior

Use `AskUserQuestion` for all user interactions. The question text should list the available options clearly.

- **"next"** or **"n"**: shows the next recommendation
- **"fix"**: (self-review mode only) applies the suggested fix using Edit/Write tools, then shows the next recommendation automatically
- **"comment"**: (comment mode only, when not self-review) posts the recommendation as an inline review comment on the PR via `gh api`, then shows the next recommendation automatically
- **"all"** or **"list"**: shows a summary table with all:

| # | Severity | Confidence | File(s) | Problem |
|---|----------|------------|---------|---------|
| 1 | Blocking | High | [`path/file.ext:42`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{path_sha256}R42) | Brief description |
| 2 | nit | Medium | [`doc.md:10`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{doc_sha256}R10) <-> [`impl.go:55`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{impl_sha256}R55) | Doc <-> Code mismatch description |
| ... | ... | ... | ... | ... |

Type "1" to "N" to see details of a specific recommendation.

- **Number (e.g. "3")**: shows details of the specific recommendation
- **Unrecognized input**: remind the user of the available commands via `AskUserQuestion`
- **When done**: "Review complete! All N recommendations have been shown." — then show the follow-up ticket prompt (see below)

## Existing review comment responses (self-review mode only)

After all recommendations have been shown, if there are unresponded review comments from other reviewers (see SKILL.md for filtering logic), present them one at a time:

---

### Review comment from @reviewer-login

**File:** [`path/to/file.ext:X`](https://github.com/{owner}/{repo}/pull/{number}/files#diff-{path_sha256}RX)

> Original comment text quoted here

**Analysis:** [Brief analysis — does this require a fix, is the author in disagreement, or is it just an observation?]

**Proposed reply:**

~~~markdown
[Draft reply content — e.g., "Fixed — added nil guard before the dereference" or "This is intentional because the context is always non-nil at this call site" or "Good catch, thanks!"]
~~~

---

After showing the proposed reply, use `AskUserQuestion` with options:

- **"post"**: post the reply as shown
- **"edit"**: user provides custom reply text, then confirm with "post"
- **"fix"**: (only when the comment requests a code change) apply the fix first, then show the reply preview and confirm with "post"
- **"next"** or **"n"**: skip this comment without responding

When all comments have been processed (or skipped), show:

**Review comments:** X responded, Y skipped

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
> [!WARNING]
> **Blocking**

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
