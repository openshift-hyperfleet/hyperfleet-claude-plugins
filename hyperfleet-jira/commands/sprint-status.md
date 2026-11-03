---
description: Sprint health overview for team leads - progress, blockers, and risks
allowed-tools: Bash
argument-hint: [project-key]
---

# Sprint Status (Team Lead View)

Comprehensive sprint health report for team leads and scrum masters.

## Arguments
- `$1` (optional): Project key (e.g., HYPERFLEET). If not provided, uses HYPERFLEET as default.

## Instructions

1. **Locate the collector script.** It ships with this command in the plugin. No globs: an unmatched glob aborts the shell in zsh.
   ```bash
   SPRINT=""
   for root in "${CLAUDE_PLUGIN_ROOT}" \
               "$HOME/.claude/plugins/marketplaces/hyperfleet-claude-plugins/hyperfleet-jira"; do
     [ -n "$root" ] || continue
     found=$(find "$root" -maxdepth 3 -name sprint_status.py -type f 2>/dev/null | head -1)
     [ -n "$found" ] && { SPRINT="$found"; break; }
   done
   echo "$SPRINT"
   ```
   If `$SPRINT` is empty, stop and say so. The script is the command: do not fall back to hand-written JQL.

2. **Run it.** Claude Code substitutes `$1` into this command as text, so never paste it into shell source: a value such as `$(id)` would run. Accept the argument only when it matches `^[A-Z][A-Z0-9_]{1,9}$`; otherwise stop and say it is not a Jira project key. When it matches, use that key in place of `HYPERFLEET` below.
   ```bash
   python3 "$SPRINT" --project HYPERFLEET --format markdown
   ```
   Options: `--today YYYY-MM-DD` for a reproducible run, `--sprint <id>` to report on a sprint other than the active one, `--stale-days` to move the staleness threshold, `--blocker-priority` to change which priority counts as top, `--link-style markdown|slack|bare` to match the destination, `--no-baseline` to skip the previous sprint lookup, `--no-prs` to skip the pull request lookup.

   The script reads the sprint metadata and goal, every issue in the sprint, the story points, the movement signals, the open blockers, the previous sprint's baseline, and a capacity projection. The baseline's delivered points are measured at the previous sprint's end date, so work closed later is not credited to it. Every item in `Review` also carries the pull requests Jira links to it, because that is where the reader's next click goes. It returns the report in one document.

3. **Do not recompute by hand, and do not re-query Jira.** These four queries look right and return wrong answers:
   - `status = Done`, `status = 'To Do'`, `priority = Highest`, `priority = High` match nothing in HYPERFLEET, which uses `Backlog` / `In Progress` / `Review` / `Closed` and `Major` / `Normal`. Use status categories, which the script does.
   - `jira issue list` omits custom fields, so it cannot produce story points. Only `jira issue view --raw` has them.
   - `jira issue list --paginate <from>:<limit>` ignores `<from>` and caps at 100, so a sprint above 100 issues truncates silently. The script pages by key range instead.
   - `updated` is polluted by bulk edits: on Sprint 19, 18 tickets shared one timestamp. Movement is the most recent of the exact last status change, the last human comment and the assignment to the current owner. A `New -> Backlog` reclassification is not movement; `In Progress -> Review` is.

4. **Reproduce the script's output.** Present its sections as given: Sprint Overview, Progress by status, Risk assessment, Carry-over, Capacity, Team workload. Keep the numbers verbatim, including the ones that look wrong; if a number is wrong, fix the script, not the text.

   Four definitions matter when you read it:
   - **Progress** is shown twice, by story points and by item count. The bar and the headline percentage use story points. Say which one you are quoting.
   - **Movement** is the most recent of the exact last status change, the last human comment and the assignment to the current owner. The status and assignment parts need `JIRA_API_TOKEN`; without it the report falls back to `statusCategoryChangedDate` and comments only, so an item can look older than it is. A failed or unavailable changelog read adds a `signal: partial` line to the Method section; keep that line in the report.
   - **Capacity** is a projection from the previous sprint's pace, not a commitment. At the start of a sprint it is mostly noise; from mid-sprint on it is the number to argue with.
   - **Pull requests** appear only on items in `Review`, read from the links the team attached in Jira. Only a pull request whose title names the ticket counts: Jira links the same pull request to every ticket it mentions, so the link alone is not ownership, and a "stale in review" item can point at someone else's diff. A failed read adds its own `signal: partial` line; keep it. A listed pull request may already be merged - the link says "there is something to review", not "it is still pending".

5. **Add Recommendations.** The script cannot write these: they need a decision.
   - Each recommendation names who decides. A follow-up with no name is not a follow-up.
   - Name the person who can say yes alone: the requested reviewer on the pull request, the assignee for a status that was never updated. When the decision belongs to a group, write the role and not its members - `decided by: Tech leads`, never a list of names. A list goes stale with the next reorganisation, and a partial list reads as the whole group. The role resolves through `OWNERS_ALIASES` in this repository; do not invent one.
   - `Owner` in the report body means the Jira assignee; `decided by` means the person accountable for the recommendation. They are different roles and the report must not reuse the word `owner` for both: a recommendation about unassigned tickets has a decider, not an owner.
   - Do not add a due date. The report has no basis for one: it does not know the reviewer's calendar, the size of the released work or the lead time of the repository. A date invented here reads as a commitment and is met by nobody, and it competes with the sprint end date, which is the only deadline the report actually knows.
   - Order by what unblocks the most work: an unassigned item that blocks seven others outranks an unassigned item that blocks none.
   - When the `Blocked by open work` list is long, recommend clearing the blockers rather than chasing the blocked items. The blocked owners cannot move.
   - Never recommend "add more people" without naming the item and the person.
   - For large work items (5 SP and above), point the lead to `/sprint-pulse-check` instead of expanding this report.

6. **Keep the report in English.** The chat reply that accompanies it follows the user's language.

## Ticket References

Every ticket key in the report is a link, and the same key is linked every time it appears.

- Print the base URL once, in Sprint Overview. The script emits it as `Jira: <server>/browse/`, read from the `server:` entry in `~/.config/.jira/.config.yml`. It documents where the links point; it is not a fallback for unlinked keys.
- Link the item's own key at the start of its Blockers, Highest-priority, Stale or Carry-Over line, and link every blocker key inside that line too. A blocked item is actionable only through its blockers, so a bare blocker key is a dead end on the line where the reader decides.
- The report's tables carry no ticket keys. If a table ever lists tickets, link the key there too.
- A key repeated across sections is linked in each of them: the reader arrives at a section, not at the document.

Match the syntax to the destination, because only one of the three renders all of them:

| Destination | Syntax | How |
|---|---|---|
| Chat / TUI | `[HYPERFLEET-XXXX](url)` | default; the script emits this |
| Slack | `<url\|HYPERFLEET-XXXX>` | run the script with `--link-style slack` |
| Plain log / paste | `HYPERFLEET-XXXX` | run the script with `--link-style bare` |

Links are the default, not a decoration. When the destination cannot render them, say so in the reply and switch the whole report to `--link-style bare`; never strip the links from part of the report.

An item in `Review` also carries its pull requests at the end of the line, as `- PR [#177](url)`. Jira's development panel is the source, so the link is whatever the team already attached to the ticket: a branch or a commit is not shown, because it is not what the reviewer opens.

The pull request's **title** decides ownership, not the link. Jira links a pull request to every ticket its title mentions, so a link whose title names another ticket is a cross-reference: reporting it as this ticket's pull request sends the reviewer to the wrong diff, and it makes two stalls look like one shared blocker. Hiding it is just as wrong, because the ticket visibly carries a link and `no pull request linked` would be false - so the line carries it with the key its title names, as `- PR [#255](url) (titled [HYPERFLEET-1636](url))`. The reader sees the shared work and knows why it is not counted. A title with no ticket key at all gets the same treatment, as `(no ticket key in the title)`.

State the link, not a question about it. The report never read the pull request, so it cannot say whether that diff covers this ticket; a recommendation that asks someone to go and confirm it turns title hygiene into sprint work. Name the two moves instead - the pull request of this ticket, or closing it as delivered by the linked one - and let the person with the context pick.

The panel carries the link and not the state, so a pull request listed here may already be merged - the link says "there is something to review", never "it is still pending". When the lookup fails, the Method section says so in its own `signal: partial` line instead of silently dropping the link.

## Output Format

The script's `--format markdown` output **is** the report: present it as Markdown, then add Recommendations.

**Never wrap the whole report in a code fence.** A fenced block disables Markdown, so the tables reach the reader as rows of `|` characters. The fences in the shapes below are illustrative; do not copy them into the reply. Use a fenced `text` block only when the destination cannot render tables (Slack, email, a plain log file), and say which destination you are formatting for.

The sections below describe the report's shape so you can check that nothing is missing, not a template to retype.

### Sprint Overview
```text
Sprint: [Sprint Name]
Goal: [Sprint Goal]
Duration: [Start Date] - [End Date] (N days)
Days Remaining: X days
Previous sprint baseline: X SP committed / X SP delivered by [End Date] (X%) across N items
Scope: X SP committed vs X SP delivered in the previous sprint (+/-X%)
Jira: https://<server>/browse/
```

### Progress Summary
```text
| Status | Category | Count | Story Points |
|--------|----------|-------|--------------|
| [real status name] | [To Do / In Progress / Done] | X | X |
| **Total** |  | **X** | **X** |

Progress: [=====>      ] X% by SP (X of X) | X% by count (X of X)
```

### Risk Assessment

#### Blocked by open work
- KEY: [Summary] - [Owner or UNASSIGNED] - [Status] - blocked by [KEY](url) (Status), [KEY](url) (Status)

#### Highest-priority open items
- KEY: [Summary] - [Owner or UNASSIGNED] - [Status] - [X days without movement]

#### Stale in progress/review
- KEY: [Summary] - [Owner or UNASSIGNED] - [Status] - [X days without movement] - PR [#N](url)

#### Missing data
- Unestimated open items: X
- Unassigned open items: X / X SP

### Carry-Over and Capacity
```text
Needs a decision: X items / X SP (X unassigned, X stale, X unestimated; a ticket can be counted in multiple reasons)
Capacity: X SP remaining; at the previous sprint's pace the team delivers X SP
in the X days left (X SP over capacity, or X SP of headroom)
```

Headroom is a finding, not a compliment: it means the sprint committed less than
the team delivers. Report it with the same weight as an overage.

### Team Workload
Open items only: closed work is already in the Progress Summary, and mixing the
two makes the Unassigned row disagree with the Missing data section.

| Team Member | [Status] | [Status] | ... | Open SP |
|-------------|----------|----------|-----|---------|
| [Name] | X | X | ... | X |
| Unassigned | X | X | ... | X |

### Recommendations
- [Action] - decided by: [Name, or role when the group decides]
- [Action] - decided by: [Name, or role when the group decides]
