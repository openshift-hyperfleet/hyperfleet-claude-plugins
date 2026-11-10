---
description: Pulse check on large work items (5 SP and above) - the nudge queue leads work through twice a week
allowed-tools: Bash
argument-hint: [project-key]
---

# Sprint Pulse Check

Leads run a pulse check a couple of times per week during a sprint on the large items (5 SP and above), to find out whether the owner needs help or has open questions. The agreement behind it: work at 5 story points and above needs shared context, and a reviewer cannot reconstruct that context from a merged PR.

This command produces a short nudge queue. It is not a sprint status report: it does not compute progress, and it does not summarize the sprint. For that, use `/hyperfleet-jira:sprint-status`.

## Arguments
- `$1` (optional): Project key (e.g., HYPERFLEET). If not provided, uses HYPERFLEET as default.

## Instructions

1. **Locate the collector script.** It ships with this command in the plugin. No globs: an unmatched glob aborts the shell in zsh.
   ```bash
   PULSE=""
   for root in "${CLAUDE_PLUGIN_ROOT}" \
               "$HOME/.claude/plugins/marketplaces/hyperfleet-claude-plugins/hyperfleet-jira"; do
     [ -n "$root" ] || continue
     found=$(find "$root" -maxdepth 3 -name pulse_check.py -type f 2>/dev/null | head -1)
     [ -n "$found" ] && { PULSE="$found"; break; }
   done
   echo "$PULSE"
   ```
   If `$PULSE` is empty, stop and say so. The script is the command: do not reimplement the calculation inline.

2. **Run it.** Claude Code substitutes `$1` into this command as text, so never paste it into shell source: a value such as `$(id)` would run. Accept the argument only when it matches `^[A-Z][A-Z0-9_]{1,9}$`; otherwise stop and say it is not a Jira project key. When it matches, use that key in place of `HYPERFLEET` below.
   ```bash
   python3 "$PULSE" --project HYPERFLEET --format json
   ```
   Options: `--today YYYY-MM-DD` for a reproducible run, `--format markdown` for a ready-to-paste block, `--min-sp` and `--max-rows` to move the thresholds, `--link-style markdown|slack|bare` to match the destination, `--next-pulse YYYY-MM-DD` to print the next scheduled pulse (omit it when the lead has not scheduled one, and the output says "to be scheduled"), `--no-prs` to skip the pull request lookup.

   The script reads the active sprint, the open items at or above `--min-sp`, the movement signals, the status of every link target, and the pull requests Jira links to the items in `Review`. It returns the queue, the escalation buckets, the assignment gap and the concentration.

3. **Do not recompute by hand.** The script's `days_without_movement`, `open_blockers` and `assignment_gap` are the numbers of record. If a value looks wrong, fix the script.

4. **Sharpen the ask.** Each queue item carries a default `ask` derived from the ladder. Rewrite it only when you have concrete context the script cannot have - a reviewer the panel does not list, a blocker that just closed, a decision that stalled. Keep it to one line.

5. **Apply the courtesies the script cannot:**
   - never promote an item the script left out of the queue (below `--action-after` days)
   - when an item is `Review`, the ask names reviewers, not the owner. The script already names every reviewer Jira reports; rewrite it only when the panel reports none and the lead knows who was asked
   - when the item is blocked, the ask names the blocker, never the person holding the ticket

6. **Do not post comments.** This command is read-only. The lead posts the ask (or approves a draft), because a bot comment changes the very signal the next pulse check reads.

## Escalation Ladder

| Days without movement | Action |
|---|---|
| 0-4 | none; leave the owner alone |
| 5-9 | Slack nudge, and ask for a comment on the ticket with the open questions or the plan |
| 10+ | office hours slot; the engineer posts context, design note, or PR link on the ticket |
| 20+, or two pulses without answer | lead decides: re-assign, split the item, or drop it from the sprint |

Two rules that come from the retro and should shape the ask:

- **The evidence of a pulse check is a comment on the ticket,** not a Slack message. Slack does not reach the reviewer and dies at end of day, which is the exact failure the pulse check exists to prevent.
- **Nudge the reviewer when the item is in `Review`.** A large item parked in review is a review-capacity problem, not a progress problem of the owner.

And two rules that come from running the check:

- **Blocked time is not the owner's time.** If the item is blocked by another open ticket, the Ask points at the person who can move the blocker - its reviewers when it is in `Review`, its owner when it is still in progress - or at assigning it if it is unowned. Do not put the blocked delay on the person holding the item, and do not raise it to the 20-day rung.
- **Assignment resets the clock.** A ticket handed to someone last week has one week without movement, not the months it spent in Backlog before that. The script reads the assignee changes from the Jira changelog; without `JIRA_API_TOKEN` it falls back to status and comments only, so an item can look older than it is.

## Output Format

One screen. Slack-ready. Every ticket key is a link. No progress bar.

```text
Pulse check - Hyperfleet Sprint 19, 2026-11-03
Jira: https://<server>/browse/

Nudge queue (5 of 7 owned large items need action):

| Ticket | Title | Owner | SP | Status · age | Ask |
|--------|-------|-------|----|--------------|-----|
| [HYPERFLEET-1413](https://<server>/browse/HYPERFLEET-1413) | Verify N-1 to N operator upgrades converge the API operand | Tirth | 5 | In Progress · 20d | Propose a split with dates, or re-scope |
| [HYPERFLEET-1616](https://<server>/browse/HYPERFLEET-1616) | SPIKE: Extend Prow testing to support OLM installs classic and v1 | Mallory | 5 | Backlog · 60d (since 09-04) | Post the decision note this week or drop from the sprint |

No action: [HYPERFLEET-1671](https://<server>/browse/HYPERFLEET-1671) (4d, assigned 10-30), [HYPERFLEET-1751](https://<server>/browse/HYPERFLEET-1751) (1d)

Assignment gap: 17 items / 85 SP have no owner
- sizes present: 5 SP
- assign these first: [HYPERFLEET-XXXX](https://<server>/browse/HYPERFLEET-XXXX) (blocks 7), [HYPERFLEET-XXXX](https://<server>/browse/HYPERFLEET-XXXX) (blocks 4)

Concentration: Phuongnhat holds 3 of 7 owned items (21 of 41 SP)

Movement = the most recent of the exact last status change, the last human comment and the assignment to the current owner; a New to Backlog reclassification is not movement, and the `updated` field is ignored because bulk edits inflate it
Next pulse: 2026-11-05
```

Rules for the output:

- **Never wrap the report in a code fence for chat or TUI.** The fence in the template is illustrative: inside it the links and emphasis reach the reader as literal characters. Use the fence only when the destination is Slack, email, or a log file, and say which one you are formatting for.
- **Print the base URL once, under the title.** It documents where the links point; it is not a fallback for unlinked keys. The script emits it from the `server:` entry in `~/.config/.jira/.config.yml`; never hardcode it.
- **Every ticket key is a link**, in the table and in the prose lines below it (`No action`, `Escalation`, `assign these first`). `--format markdown` prints them already rendered (`text` is an alias for it); this command reads `--format json`, where the key stays bare and the payload carries `jira_base_url` and `link_style` instead, so render each key yourself: `[HYPERFLEET-XXXX](<base>HYPERFLEET-XXXX)` for chat or TUI, `<url|HYPERFLEET-XXXX>` for `--link-style slack`, the bare key for `--link-style bare`. Never mix two styles in one output. Do not re-render text that already arrives rendered - the `Ask` string is composed by the script and comes with its keys in the chosen style.
- **A pull request is a link too.** For an item in `Review` the script appends the pull requests whose **title** names the ticket: Jira links a pull request to every ticket its title mentions, so `architecture#255`, titled `HYPERFLEET-1636`, is never `HYPERFLEET-1669`'s. Numbers restart in every repository, so a pull request is identified by its URL: `hyperfleet-api#120` and `hyperfleet-infra#120` can both belong to the ticket. A ticket can own several; the `Ask` shows the two that fit and appends `+N`, a width limit rather than a ranking, and it never picks one or asks which is the duplicate. It rides in the `Ask`, already rendered in the chosen style, and is not a seventh column. **Name every requested reviewer, never one and never the author:** picking one would decide who reviews, and the author wrote the diff. The panel reports a state when it has one, so `(merged)` becomes `Move this ticket out of Review: PR [#181](url) (merged)`; a hand-attached link has none. With no link of its own the ask is `Attach this ticket's pull request, or move it back to In Progress` - but only when the lookup answered: a skipped (`--no-prs`), unavailable or failed read leaves the ask neutral, because an empty list then means "unread", not "none".
- **One table row per item, six columns, `Ask` last.** `Ticket | Title | Owner | SP | Status · age | Ask`. No second row, no empty cell: an `Ask` row under the data row squeezes the text into the first column, and Markdown has no `colspan` to fix it. `Ask` sits last because the last column is the one that grows, so a long ask wraps at the right edge instead of widening the table from the left.
- **Status and age share a column.** "Review · 12d" is one thought for the reader. Splitting it into two columns costs width and buys nothing.
- **Keep the title and the SP.** Without the title the ask loses its referent; without the SP an 8-point item gets the same nudge as a 5.
- The **Ask** names the next action, not the problem, and it starts with a verb: `Ask Tirth and Rafael to approve or reject [HYPERFLEET-1636](url) (Review 7d); assign [HYPERFLEET-1523](url)`, `Ask a reviewer to approve or reject`, `Start this week or drop from the sprint`, `Post a start date and the first step on the ticket`.
- **The verb comes from a closed set:** `ask` (approve/reject, status, start or drop), `assign`, `attach` (the ticket's pull request), `move` (a ticket out of `Review`), `post`, `start`, `propose` (a split), `confirm` (a date, or an unread ticket's status and owner). A closed set keeps the column scannable and countable, and it bounds the hand rewrite in step 4 to the specifics - who, which PR, which blocker - never to the choice of action.
- **Never restate the item's own age in the Ask.** It is in the `Status · age` cell beside it; repeating it costs width and produces "20+ days: 20+ days". A blocker's age does appear, because that clock is not in the table.
- **The verb follows the state, not the age alone:** blocked items name the blocker's move, `Review` asks a reviewer for a decision, `In Progress` asks for evidence on the ticket, and unstarted work asks for a date; a spike keeps that date ask until it reaches the 20-day rung, where it asks for the decision note instead of a start date.
- Items in good standing stay visible only in the single "No action" line, never as table rows.
- In the `Status · age` cell, `(assigned MM-DD)` marks a clock shortened by a reassignment and `(since MM-DD)` marks a Backlog item with no start. Never show both.
- A blocker's age is its own last workflow transition, not the blocked item's. A blocker in `Review` leads the ask and names all of its requested reviewers (`Ask Tirth and Rafael to approve or reject [HYPERFLEET-1636](url) (Review 7d)`); its owner is the author, so the owner is named only when Jira reports no pull request for it. When every pull request it owns is merged or declined there is nothing left to review, so the ask becomes the queue's move instead: `move [HYPERFLEET-1636](url) out of Review: PR [#181](url) (merged)`. An unowned blocker becomes `assign [HYPERFLEET-1523](url)`, because there is nobody to ask - but only when its state was read. A blocker whose read failed - no permission, a deleted issue, a dropped connection - becomes `confirm [HYPERFLEET-1825](url)'s status and owner`: `assign` would order work that may already have an owner, and the status `?` is the only thing known about it.
- **Say when the signal is partial.** The command reads JSON, so the script's own text warning never appears. If `changelog_signal.failed` is non-zero, add one line under the queue: `Signal: partial - N of M changelog reads failed; those items use the status category date`. Only when `failed` is zero and `changelog_signal.available` is false, add: `Signal: partial - no JIRA_API_TOKEN, so movement ignores exact status changes and assignments`. The two are exclusive, and the order matters: a failed read also sets `available` to false, so testing `available` first would blame the missing token for a network error. The same pair applies to `pr_signal`: a non-zero `failed` adds `Signal: partial - N of M pull request reads failed; those items carry no pull request link`, and an unavailable lookup with no failures adds the reason instead. A non-zero `fetch_signal.failed` adds `Signal: partial - N issue reads failed, so those items are missing from the queue and their links stay open`; the script's `render_text` prints all three in that order.
- State the movement definition in every output. Without it the numbers start arguments.
- Date the output, and print the next pulse date, so a stale copy is recognizable at a glance.

## Limits

Six things the numbers cannot tell you:

- **Bots are not movement.** Comments from app accounts are ignored, so a ticket whose only comments come from "Automation for Jira" or a GitHub sync shows the status-change clock. That is correct for "a human moved it", and it means a synced PR does not register: check the PR before nudging.
- **Reclassification is not movement.** A bulk `New -> Backlog` sweep changes status without work, so transitions where both sides are `New` or `Backlog` are ignored. A transition inside a category, such as `In Progress -> Review`, does count.
- **`Review` measures review decisions, not effort.** Review activity lives on GitHub, so days without movement on a `Review` item means "no reviewer decided". The ask points at reviewers, not at the owner: the owner wrote the diff.
- **A reviewer list comes from the panel, and the panel is incomplete.** Jira reports the reviewers the GitHub app collected, and it shows `User ` for an account it can no longer resolve - the script drops those. A pull request attached by hand carries no reviewers at all, so the ask falls back to `Ask a reviewer` instead of guessing a name.
- **The queue is sprint-scoped.** A large item outside the sprint never appears, however stalled it is; that is `/hyperfleet-jira:triage` territory.
- **No memory.** The script cannot tell "nudged twice already" from "first nudge": that lives in the ticket comments, and the 20-day rung is the proxy. If the team wants a real trail, the evidence rule above is what produces it.
