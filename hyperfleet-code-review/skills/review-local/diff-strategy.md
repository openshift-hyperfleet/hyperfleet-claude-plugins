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

If SCOPE is not `uncommitted`, fetch main from the resolved remote:

    git fetch REMOTE main

Skip the fetch entirely for `uncommitted` scope — no remote contact is needed.

### Main branch guard (skip for `uncommitted` scope)

Before diffing, check if the current branch is main:

    CURRENT=$(git branch --show-current)

If CURRENT is `main` or `master`, stop the review immediately and print:

    ❌  Cannot review main. Check out a feature branch and try again.

Do not proceed with the review.

### Branch staleness check (skip for `uncommitted` scope)

Before diffing, check how far behind the branch is:

    BEHIND=$(git rev-list --count HEAD..REMOTE/main)

If BEHIND > 0, print the following warning and continue with the review:

    ⚠️  Branch is N commits behind REMOTE/main — rebase before merging.

### Diff by scope

- `all` (default):
    MERGE_BASE=$(git merge-base REMOTE/main HEAD)
    git diff "$MERGE_BASE"
    Also check for untracked files: git ls-files --others --exclude-standard
    Include any untracked files as new files in the review.

- `committed`:
    git diff REMOTE/main...HEAD    (committed changes only — staged and unstaged excluded)
    Only include files from: git diff --name-only REMOTE/main...HEAD

- `uncommitted`:
    git diff HEAD        (staged + unstaged changes against last commit)
    Do NOT fetch or diff against REMOTE/main.

## Lines changed

Record lines changed for the Review setup block:

    - `all`:         git diff "$MERGE_BASE" --shortstat
    - `committed`:   git diff REMOTE/main...HEAD --shortstat
    - `uncommitted`: git diff HEAD --shortstat

## Empty diff

If the diff is empty and no untracked files exist:

Print the summary box from output-format.md with Findings: 0, Warnings: 0, and this
note below the box:
  For `all` or `committed`: "No changes found against <remote>/main. Branch is clean."
  For `uncommitted`: "No uncommitted changes found. Working tree is clean."

Stop after printing.
