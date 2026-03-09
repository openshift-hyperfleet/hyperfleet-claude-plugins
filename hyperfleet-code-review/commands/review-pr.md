---
description: Review a PR with JIRA validation, architecture checks, impact analysis, and interactive recommendations
allowed-tools: Bash, Read, Grep, Glob, Agent
argument-hint: <PR-URL-or-owner/repo#number>
---

# Review PR

Review the given PR and list the main recommendations, one at a time.

## Arguments

- `$1`: PR URL (e.g. `https://github.com/org/repo/pull/123`) or `owner/repo#123`

## Instructions

1. Use `gh pr view <PR> --json files,body,title,comments` to get PR details
2. Use `gh pr diff <PR>` to get the full diff
3. Use `gh api repos/{owner}/{repo}/pulls/{number}/comments` to see existing comments from CodeRabbit or other reviewers
4. **If there is a JIRA ticket in the PR title** (e.g. HYPERFLEET-123):
   - Run `jira issue view HYPERFLEET-123 --comments 50` to get the ticket description **and all comments**
   - Understand the ticket's goal, acceptance criteria, and any clarifications or additional requirements discussed in the comments
   - Validate whether the PR meets **all** requirements — including those added or refined in comments (e.g., "we also need X", "please use Y approach", "don't forget to handle Z")
5. **Use the `hyperfleet-architecture` skill** to check the HyperFleet architecture docs and verify there are no inconsistencies between the PR changes and the defined architecture patterns
6. **Impact analysis — check if the diff introduced breaking changes for consumers:**
   - For each changed struct, config field, or function signature **in the diff**, search the codebase (`Grep`/`Glob`) for callers that may need updates
   - Check if any file **should have been modified but wasn't** due to a change in the diff (e.g., a Helm template that renders a config field whose type changed in the diff)
   - This is NOT about reviewing pre-existing code — only about verifying the diff's impact on the rest of the codebase
   - **Important**: if the impacted file is NOT part of the PR's file list, do NOT create a numbered recommendation for it. Instead, include it in the **Impact warnings** section of the output (see output format below). Only create numbered recommendations for files that ARE in the PR diff.
7. **Compare the diff against the current codebase on `main`** — read the original files to understand context, but only to detect problems **introduced by the diff** (e.g., the new code contradicts an existing pattern, or a comment updated in the diff became inaccurate)
8. **Trace the full call chain for each change in the diff:**
   - For code changes: trace callers AND callees of modified functions/types to verify the change is consistent in all contexts where it's used
   - For documentation changes: trace the full implementation path (handler -> service -> db/helpers) to verify each documented claim
   - Cross-reference: if the diff introduces N options/operators/fields/modes, verify that ALL N work in ALL contexts (e.g., an operator that works for regular fields may fail for JSONB fields; a config that works for clusters may not work for nodepools)
   - Use the Agent tool with subagent_type=Explore if the call chain spans more than 3 files
9. **Doc <-> Code cross-referencing (only when at least one side is in the diff):**
   - If the diff adds/modifies a spec or design doc (e.g., test-design, ADR, runbook): read the corresponding implementation code and verify every step/claim in the doc is actually implemented
   - If the diff adds/modifies implementation code: read the corresponding spec/design doc (if one exists in the repo) and verify the code matches what the doc describes
   - Only flag mismatches where the **diff-side** introduced the inconsistency (a new doc step with no code, or new code that contradicts the doc)
   - Common pairs: test-design docs <-> test files, API docs <-> handlers, deploy runbooks <-> deploy scripts
10. **Mechanical code pattern checks — run as separate passes with explicit enumeration.** Each pass MUST list every instance found in the diff before evaluating it. Do NOT skip a pass because "it looks fine" — enumerate first, then judge.

    **Pass A — Switch/select exhaustiveness:**
    List every `switch` and `select` statement added or modified in the diff. For each, verify it has a `default` case (or explicitly handles all known values). Flag missing `default` as a bug when unrecognized input would silently fall through to a wrong behavior.

    **Pass B — Error handling completeness:**
    List every function call in the diff that returns an `error`. For each, verify the error is checked. Flag silently ignored errors (`_, _ :=` or bare calls on error-returning functions).

    **Pass C — Resource lifecycle:**
    List every resource created in the diff (files, connections, contexts with cancel, HTTP bodies, exporters, tracer providers, database transactions). For each, trace ALL code paths (including early `return` and error branches) to verify cleanup (`defer Close()`/`cancel()`/`Shutdown()`). Flag any path where cleanup is skipped.

    **Pass D — Concurrency safety:**
    List every variable captured by a goroutine or closure in the diff, AND every variable accessed from HTTP handlers (which run in separate goroutines). For each, verify proper synchronization (mutex, atomic, channel). Flag unprotected shared reads/writes.

    **Pass E — Goroutine lifecycle:**
    List every goroutine started in the diff. For each, verify it has a clear shutdown mechanism (context, channel, WaitGroup). Flag fire-and-forget goroutines with no way to stop them.

    **Pass F — Nil/bounds safety:**
    List every array/slice indexing and pointer dereference in the diff on values that could be nil or empty. For each, verify a guard exists. Flag potential panics.

    **Pass G — Constants and magic values:**
    Identify package-level `var` declarations whose values never change and should be `const`. Flag inline literal strings used as fixed identifiers, config keys, filter expressions, or semantic values (e.g., `"gcp_pubsub"`, `"traceidratio"`, `"publish"`) — these should be named constants. Flag magic numbers used as thresholds, sizes, or multipliers.

    **Pass H — Log-and-continue vs return:**
    List every error-logging statement in the diff where execution continues after the log. For each, verify this is intentional graceful degradation and not a missing `return`.

11. **Intra-PR consistency check** — For patterns that appear more than once across different files in the diff, verify ALL occurrences use the same approach. Examples:
    - Error handling style (some places check errors, others ignore)
    - Synchronization primitives (some goroutines use `atomic`, others use plain `int`)
    - Test setup/teardown patterns (some tests restore global state, others don't)
    - Naming conventions, logging patterns, config access patterns
    - Flag inconsistencies within the PR itself — if the author did it right in one place, they likely intended to do it everywhere.
12. Analyze **only the code changed in the diff** (added or modified lines) and identify all problems not yet pointed out by steps above
13. Prioritize problems by impact
14. Show **only the first recommendation** (the most important one)

## Exclusions — DO NOT repeat problems already pointed out by:

- CodeRabbit or other review bots
- Other human reviewers (PR comments)
- **The user in this conversation** (if the user already suggested something before calling /review-pr, do not repeat it)

## Prioritization (most to least critical)

1. Bugs and logic issues
2. Security issues
3. Inconsistencies with HyperFleet architecture docs
4. PR does not meet JIRA ticket requirements
5. Internal inconsistencies and contradictions
6. Outdated or deprecated versions
7. Project patterns not followed
8. Issues found by the mechanical checklist passes (step 10) or intra-PR consistency (step 11) not covered above
9. Clarity and maintainability improvements

## Output format

### Initial summary

First, show a brief summary:

```
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** N (new, excluding already commented ones)

Showing recommendation 1 of N:
```

### Impact warnings (optional, only when impact analysis found files outside the PR)

If step 6 (impact analysis) found files that **should have been updated but are NOT part of the PR**, show them in a separate section **before** the recommendations. These are NOT numbered recommendations — they are informational warnings so the author is aware.

**GitHub comment:**

> ### Impact warnings
>
> The following files are **NOT in this PR** but may need updating due to changes in the diff:
>
> - **`docs/development.md`** (lines 31, 33, 40) — Still references `gcp.json` which was renamed to `nodepool-request.json` in this PR
>
> These are outside the PR scope and shown for awareness only.

If there are no impact warnings, skip this section entirely.

### When N = 0 (no new recommendations)

```
**PR:** [PR title]
**Files:** X file(s) changed
**Recommendations found:** 0

No additional recommendations! Existing comments already cover the relevant points.
```

### Current recommendation (when N > 0)

Show only ONE recommendation at a time:

```
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

### Doc <-> Code inconsistency variant

When the recommendation is a Doc <-> Code mismatch (from step 9), use this format instead — showing both files involved:

```
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

## Interactive behavior

- **"next"** or **"n"**: shows the next recommendation
- **"all"** or **"list"**: shows a summary table with all:

```
| # | File(s) | Line | Problem |
|---|---------|------|---------|
| 1 | path/file.ext | 42 | Brief description |
| 2 | doc.md <-> impl.go | 10, 55 | Doc <-> Code mismatch description |
| ... | ... | ... | ... |

> Type "1" to "N" to see details of a specific recommendation.
```

- **Number (e.g. "3")**: shows details of the specific recommendation
- **When done**: "Review complete! All N recommendations have been shown."

## Rules

- **SCOPE: diff only** — Only recommend problems on lines that were **added or modified** in the PR (lines with `+` in the diff). Pre-existing code that was not changed by the PR is **out of scope**, even if it has problems. Files that are NOT in the PR's file list are **never** valid targets for recommendations — even if a change in the diff makes them stale or broken. Impact analysis (step 6) may discover such files, but they must go in the **Impact warnings** section (see output format), never as numbered recommendations.
- DO NOT repeat problems already pointed out (by bots, reviewers, or the user in the conversation)
- Include concrete suggestions for fixes (code or text) when possible
- Adapt N to the actual number of recommendations (can be 0, 1, 5, 15, etc.)
- **Line numbers**: always use the line from the **new file** that corresponds to what GitHub shows in the right column of the diff in the web UI. **DO NOT manually calculate** from the `@@` headers of the diff — this is error-prone. Instead, fetch the file directly from the PR branch and find the exact line:
  ```bash
  # Get the PR branch
  gh pr view <PR> --json headRefName -q '.headRefName'
  # Fetch the file from the branch and find the exact line
  gh api "repos/{owner}/{repo}/contents/{path}?ref={branch}" -q '.content' | base64 -d | grep -n "code_snippet"
  ```
  The number returned by `grep -n` is what GitHub shows in the web UI.
