# Output Format

## Scope rule

Only report numbered findings for problems on lines that were added or modified in the diff
(lines with + in the diff). Do not flag pre-existing findings in unchanged code.

## No narrative commentary

Output ONLY the structured blocks defined in this file:

1. Review setup
2. Numbered findings (grouped by category)
3. Warnings
4. Summary box

Do NOT output anything else — no introductory sentences, no closing paragraphs, no
explanations of why code is correct, no summaries of what the diff does, no architecture
analysis narratives, no positive observations, no conclusions. Any text outside the four
blocks above must be removed before responding.

## Review setup

Print this block first — before running any checks. Combine tool availability, scope,
lines changed, and check results into one unified block.

```
Review setup
  ✓  gh CLI available
  ✓  <remote>/main reachable
  ✓  Scope    all  (+523 / -35)
  ✓  Standards loaded (8 files)
  ❌  CodeRabbit — not installed
  ❌  Standards — fetch failed (run gh auth login)
```

Rules:

The Review setup block has exactly these lines — no more, no less:

| Line | When to print |
|------|---------------|
| `✓  gh CLI available` | Always |
| `✓  <remote>/main reachable` | Always |
| `✓  Scope    <types>  (<+N> / <-N>)` | Once diff is computed |
| `✓  Standards loaded (N files)` | When fetch succeeds |
| `❌  Standards — fetch failed (run gh auth login)` | When fetch fails |
| `❌  CodeRabbit — not installed` | When CodeRabbit is not installed |
| `❌  CodeRabbit — rate limited` | When CodeRabbit is rate limited |

DO NOT add ✓ lines for individual check results (Security, Architecture, Code hygiene, etc.).
Check results belong in the summary box Tools section and in the findings/warnings sections.
Omit any line not in the table above.

## Numbered findings

If there are no findings, omit this section entirely — do not print any category headers
or finding blocks.

Otherwise, list all findings grouped by category, ordered by category priority (see
config/categories.md). Within each category, sort blocking before nit.

Severity levels (**Blocking** = must fix, **nit** = non-blocking suggestion).
See config/categories.md for default severity by category and override rules.
For CodeRabbit-sourced findings, preserve CodeRabbit's own severity instead of applying
category defaults: Critical/Major/Minor → Blocking, Trivial/Info → nit.

```
─── Bug (1) ─────────────────────────────────────────

── Finding 1/N ── Bug | Standards | Blocking | path/to/file.go:42 ──────────────

─── Security (2) ────────────────────────────────────

── Finding 2/N ── Security | CodeRabbit | Blocking | path/to/file.go:88 ─────────
── Finding 3/N ── Security | Standards | nit | path/to/file.go:101 ─────────
```

Source labels:

- `Standards` — found by standards or mechanical checks only
- `CodeRabbit` — found by CodeRabbit only
- `CodeRabbit + Standards` — found by both; counts as CodeRabbit in the summary

Before rendering, validate every finding has all four header fields populated (Category,
Source, Severity, Location). If any field is missing, infer it and append `(inferred)` to the
inferred value so it is visible to the user:

- Missing category → infer from the check name (e.g. security agent → `Security (inferred)`); if the check name does not map to a known category, default to `Pattern (inferred)`
- Missing source → use `Standards (inferred)`
- Missing severity → use the category default above with `(inferred)`
- Missing location → use the file/line from the finding object, or `unknown (inferred)`
Never render a finding with a blank or missing header field.

For each finding, show ALL four parts in order — never omit any part, never output the
prompt block without the header and body above it:

1. **Header line** (required — always first)
   `── Finding N/N ── Category | Source | Severity | path/to/file:line ──`
2. Current code with a few lines of context, always in a fenced code block (even for
   markdown or text files — show the raw content, not rendered output)
3. **Problem:** clear description of the issue
4. **Fix:** before/after diff block with - and + lines
   - Prefer replacing over deleting — every `-` line should have a corresponding `+` line
     unless the deletion itself is the fix (e.g. removing dead code, a security risk, or a
     redundant check).
   - Preserve behavior unless the finding is a bug or security issue where changing behavior
     is the point. When behavior changes, note why in the fix description.
   - The fixed code must be syntactically valid (or compile for compiled languages).
5. **Prompt for AI tooling** (required label — always print `**Prompt for AI tooling:**` on its own line before the `~~~` fence) — a concise block the user can copy directly into an AI tool.
   - If the finding source is `CodeRabbit` or `CodeRabbit + Standards`: preserve CodeRabbit's
     original suggestion block exactly as provided in its output. Do not rewrite it.
   - Otherwise: generate the prompt using the template below. Use `@file` syntax so the AI
     loads the file automatically. Map category to a label:
     Bug/Security → `Critical comment`,
     Architecture/Inconsistency/Deprecated → `Inline comment`,
     Standards/Pattern → `Inline comment`,
     Improvement → `Nitpick comment`.

~~~
Verify this finding against the current code and only fix if needed.
Note: line numbers are from the review snapshot — verify location before applying.

<Label> comment:
In `@path/to/file.go`:
- Line N: <one clear instruction describing the problem and the fix, referencing the
  relevant HyperFleet standard where applicable>
~~~

Only flag findings backed by the loaded standards or checks.

## Counting rule

Count each finding exactly once for the summary totals:

- All findings count toward the Findings total regardless of source label.
- The CodeRabbit Tools line shows how many findings CodeRabbit contributed
  (labels `CodeRabbit` and `CodeRabbit + Standards` both count here).

Count each WARN line exactly once toward the Warnings total:

- Commit format violations count as 1 warning (not 1 per commit).
- Each pre-existing issue is 1 warning.
- Each impact analysis hit is 1 warning.

## Warnings

Print this section after numbered findings and before the summary box. Only print this
section if there is at least one warning — omit it entirely (including the header) if
there are no warnings.

```
─── Warnings ────────────────────────────────────────
```

List every warning once, with inline detail immediately below it. Each warning gets at most two lines: the
WARN line, then one line of context. No per-item breakdowns, no explanations, no extra lines.

```
WARN  commit-standard.md — 2 commits not following format (SHA: 6417377, 059b299)
      Expected format: HYPERFLEET-XXX - <type>: <subject>

WARN  internal/foo.go:88 — pre-existing: error return ignored
      Not introduced by this diff — flagged for awareness only.

WARN  internal/bar.go — may need updating: calls Reconcile() whose signature changed
      Callers found at: internal/bar.go:42, internal/baz.go:17
```

If the WARN line is self-explanatory, omit the second line entirely.

## Summary box

Print the summary box after the warnings section. This is the final output — stop
immediately after the closing box line.

```
┌──────────────────────────────────────────────────┐
│  Review Summary                                  │
│                                                  │
│  Repo     <repo-name>                            │
│  Branch   <current-branch>                       │
│  Against  <remote>/main                          │
│                                                  │
│  Results                                         │
│  ──────────────────────────────────────────────  │
│  Findings  N                                     │
│  Warnings  N                                     │
│                                                  │
│  Tools                                           │
│  ──────────────────────────────────────────────  │
│  CodeRabbit     <one of: N findings |            │
│                  rate limited | not installed>   │
│  Architecture   <one of: N findings |            │
│                  skipped | failed>               │
└──────────────────────────────────────────────────┘
```

HARD STOP — the summary box is the final output. Do not add anything after the closing
└─ line. No analysis summaries, no positive observations, no conclusions, no next steps.
The response ends immediately after the summary box.
