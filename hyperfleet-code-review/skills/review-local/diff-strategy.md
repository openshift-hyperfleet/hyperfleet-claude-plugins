# Diff Strategy

## Remote detection

Determine the correct remote in this order:

1. Run: git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
   If it exits with code 128 or any error, suppress the error output and move to step 2.
   Do not surface this error to the user — it is expected for branches without a tracking remote.
   If it succeeds, extract the remote name from the result (e.g. origin/main → origin).
   Use that remote.

2. If step 1 failed, run: git remote -v
   Look for a remote pointing to github.com/openshift-hyperfleet. Use that remote.

3. If no match, fall back to origin.

If the fetch fails (e.g. offline), tell the user and stop.

## Fetching and diffing

Fetch main from the resolved remote and diff all changes:

  git fetch REMOTE main
  git diff REMOTE/main

Also check for untracked files with: git ls-files --others --exclude-standard
If any exist, read them directly and include them in the review as new files.

Record for the summary:
- REMOTE
- Commit count: `git rev-list REMOTE/main..HEAD --count`
- Lines changed: `git diff REMOTE/main --shortstat`
- Scope: which change types are present (used as a sanity check in the summary):
    - Committed: commit count > 0
    - Staged:    `git diff --cached --name-only` is non-empty
    - Unstaged:  `git diff --name-only` is non-empty
  List only the types that are present, e.g. "committed + staged" or "unstaged only"

## Empty diff

If the diff is empty and no untracked files exist:

Print the summary box from output-format.md with Findings: 0, Warnings: 0, and this
note below the box:
  "No changes found against <remote>/main. Branch is clean."

Stop after printing.
