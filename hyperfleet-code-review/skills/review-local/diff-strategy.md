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

Fetch main from the resolved remote, then diff based on the SCOPE argument:

- `all` (default):
    git fetch REMOTE main
    git diff REMOTE/main
    Also check for untracked files: git ls-files --others --exclude-standard
    Include any untracked files as new files in the review.

- `committed`:
    git fetch REMOTE main
    git diff REMOTE/main HEAD    (committed changes only — staged and unstaged excluded)
    Only include files from: git diff --name-only REMOTE/main HEAD

- `uncommitted`:
    git diff HEAD        (staged + unstaged changes against last commit)
    Do NOT fetch or diff against REMOTE/main.

Record for the summary:
- REMOTE (not applicable for uncommitted scope)
- SCOPE (the resolved argument: all, committed, or uncommitted)
- Lines changed:
    - `all`:         git diff REMOTE/main --shortstat
    - `committed`:   git diff REMOTE/main HEAD --shortstat
    - `uncommitted`: git diff HEAD --shortstat

## Empty diff

If the diff is empty and no untracked files exist:

Print the summary box from output-format.md with Findings: 0, Warnings: 0, and this
note below the box:
  For `all` or `committed`: "No changes found against <remote>/main. Branch is clean."
  For `uncommitted`: "No uncommitted changes found. Working tree is clean."

Stop after printing.
