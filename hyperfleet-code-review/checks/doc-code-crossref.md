# Doc/code cross-referencing and link validation

This check is **language-agnostic** and runs for every diff regardless of file types.

## Doc/code cross-referencing

Only run when at least one side (doc or code) is in the diff:

- If the diff adds/modifies a spec or design doc (e.g., test-design, ADR, runbook): read the
  corresponding implementation code and verify every step/claim in the doc is actually implemented
- If the diff adds/modifies implementation code: read the corresponding spec/design doc (if one
  exists in the repo) and verify the code matches what the doc describes
- Only flag mismatches where the **diff-side** introduced the inconsistency (a new doc step with
  no code, or new code that contradicts the doc)
- Common pairs: test-design docs <-> test files, API docs <-> handlers, deploy runbooks <-> deploy
  scripts

## Link and anchor validation

When any file in the diff contains a URL, link, or anchor reference (e.g., `runbook_url`, markdown
links, `$ref`), validate the reference resolves correctly:
- **Same-file anchors** (`#fragment` with no path): resolve against the file's updated content
  from the diff
- **Cross-file references** (pointing to another file): validate whether or not the target is
  part of the diff. For targets outside the diff, fetch the file from the base branch (usually
  `main`) to verify:

- For markdown heading anchors (`#section-name`): compute the GitHub-generated anchor using
  this algorithm in order:
  1. Strip markdown formatting: remove `**`, `*`, `_`, `` ` ``, `[text](url)` → `text`, and
     other inline markup tokens
  2. Lowercase the result (GitHub preserves Unicode — treat all Unicode letters as valid,
     not just ASCII)
  3. Strip characters that are not Unicode letters, numbers, spaces, or hyphens
  4. Replace spaces with hyphens
  5. Collapse consecutive hyphens into one (e.g. `test--multiple` → `test-multiple`)
  6. Strip leading and trailing hyphens (e.g. `-test-` → `test`)
  7. For duplicate headings, track a per-document slug counter: first occurrence uses the
     base slug, subsequent occurrences append `-1`, `-2`, etc.
  Example: `### Poll Stale (Dead Man's Switch)` → `#poll-stale-dead-mans-switch`, NOT `#poll-stale`.
  Verify the URL fragment against the base slug plus the appropriate duplicate suffix.
- For file path references: verify the target file exists at the referenced path
- For YAML/config references to doc sections: verify the referenced section heading exists and the
  generated anchor matches
