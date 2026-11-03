#!/usr/bin/env python3
"""Pulse check data collector for the HyperFleet sprint pulse check.

Reads the open large work items (>= --min-sp story points) of the active sprint,
computes how long each has been without movement, resolves open blockers, and
prints the nudge queue as JSON (default) or as a ready-to-paste text block.

Movement is the most recent of:
  - the exact last status change, from the Jira changelog; a New -> Backlog
    reclassification is ignored, while In Progress -> Review counts
  - the last human comment (authors whose accountType is not "app")
  - the assignment to the current owner, from the same changelog

The status and assignment signals need `JIRA_API_TOKEN`; without it the script
falls back to `statusCategoryChangedDate` plus comments and says the signal is
partial. The `updated` field is deliberately ignored: bulk edits make untouched
tickets look active (on Sprint 19, 18 tickets shared one `updated` timestamp).

Read-only. The script never writes to Jira.

Usage:
    python3 pulse_check.py                          # JSON, current sprint, today
    python3 pulse_check.py --format text            # ready-to-paste block
    python3 pulse_check.py --today 2026-11-03       # reproducible run
    python3 pulse_check.py --project HYPERFLEET --min-sp 5 --max-rows 7
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

# The Jira layer is shared with sprint_status.py: one definition of "work is Done
# by category", one pager, one changelog reader. See jira_common.py.
from jira_common import (
    OPEN_STATUS_JQL,
    ChangelogUnavailable,
    JiraError,
    active_sprint,
    apply_changelog_signals,
    apply_pull_requests,
    describe,
    fetch_all,
    jira_base_url,
    open_links,
    parse_date,
    pr_refs,
    project_key,
    run_jira,
    status_category,
    status_name,
    ticket_ref,
)

# One error type, two names: the caller sees the script it invoked, not the module
# that raised. The alias also keeps existing tests reading naturally.
PulseError = JiraError


def prose(text: str) -> str:
    return " ".join(str(text or "").split())


def cell(text: str) -> str:
    """One table cell: no pipes, no newlines, whatever the text contains."""
    return prose(text).replace("|", "\\|")


def large_item_keys(
    project: str, sprint_id: str, min_sp: int, sp_field_name: str, binary: str
) -> list[str]:
    jql = (
        f'project = {project} AND sprint = {sprint_id} '
        f'AND "{sp_field_name}" >= {min_sp} AND {OPEN_STATUS_JQL}'
    )
    out = run_jira(
        ["issue", "list", "-q", jql, "-p", project, "--plain", "--no-headers", "--columns", "KEY"],
        binary,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def assignment_is_binding(item: dict) -> bool:
    """True when the assignment date is what keeps the clock short.

    A tie with the status change is not a reason to mention the assignment: the
    status already explains it.
    """
    days = item.get("days_since_assignment")
    if days is None:
        return False
    others = [item["days_in_status"]]
    if item.get("days_since_comment") is not None:
        others.append(item["days_since_comment"])
    return days < min(others)


def is_spike(item: dict) -> bool:
    """A spike reads its evidence into a document, not into a PR."""
    return item.get("summary", "").lstrip().upper().startswith(("SPIKE", "[SPIKE]"))


def suggested_ask(item: dict, ref=None) -> str:
    """One imperative per item: verb first, then who and what artifact.

    The verb comes from a fixed set - ask to approve/reject, assign, unblock,
    post, start, propose a split - so the column can be scanned and counted.
    The item's own age lives in the `Status . age` cell, so the text never
    repeats it; a blocker"s age does appear, because that clock is not in the
    table and it is what makes the blocker urgent or not.

    `ref` renders a key for the destination, so a blocker named in the ask is a
    link like every other key in the report. It defaults to the bare key, which
    keeps the ask readable in a test and in a log.
    """
    ref = ref or (lambda key: key)
    if item["open_blockers"]:
        # A blocker in Review is the one an ask can move today, so it leads.
        detail = sorted(
            item["blocker_detail"],
            key=lambda d: (d["status"] != "Review", d["key"]),
        )
        clauses = []
        for d in detail:
            days = d.get("days_in_status")
            when = f" {days}d" if days is not None else ""
            if d["status"] == "Review" and d.get("owner"):
                clauses.append(
                    f"ask {d['owner'].split()[0]} to approve or reject {ref(d['key'])} "
                    f"(Review{when})"
                )
            elif not d.get("owner"):
                clauses.append(f"assign {ref(d['key'])}")
            elif d["status"] == "In Progress":
                clauses.append(
                    f"ask {d['owner'].split()[0]} for the status of {ref(d['key'])}"
                )
            else:
                clauses.append(
                    f"ask {d['owner'].split()[0]} to start or drop {ref(d['key'])}"
                )
        shown = "; ".join(clauses[:2])
        more = f" (+{len(clauses) - 2} more)" if len(clauses) > 2 else ""
        return shown[0].upper() + shown[1:] + more
    if item["status"] == "Review":
        return "Ask a reviewer to approve or reject"
    if item["status"] == "In Progress":
        if item["days_without_movement"] >= 20:
            return "Propose a split with dates, or re-scope"
        if item["days_without_movement"] >= 10:
            return "Post the blocker or the PR link on the ticket"
        return "Post the open questions on the ticket"
    if item["days_without_movement"] >= 20:
        if is_spike(item):
            return "Post the decision note this week or drop from the sprint"
        return "Start this week or drop from the sprint"
    if item["days_without_movement"] >= 10:
        return "Post a start date and the first step on the ticket"
    return "Confirm a start date on the ticket"


def build(args) -> dict:
    today = parse_date(args.today) if args.today else datetime.now(timezone.utc).date()
    sprint = active_sprint(args.project, args.jira)
    keys = large_item_keys(
        args.project, sprint["id"], args.min_sp, args.sp_field_name, args.jira
    )
    docs = fetch_all(keys, args.project, args.jira, args.jobs)

    items = []
    for key, doc in docs.items():
        item = describe(key, doc, args.sp_field, today)
        # The report sums points, so "no estimate" is zero here; describe keeps
        # None so the sprint report can tell the two apart.
        item["sp"] = item["sp"] or 0
        items.append(item)

    # Resolve the status of every link target so "blocked" and "blocks" mean open work only.
    targets = {k for item in items for k in item["blocked_by"] + item["blocks"]} - set(docs)
    extra = fetch_all(sorted(targets), args.project, args.jira, args.jobs) if targets else {}
    status_of = {k: status_name(d) for k, d in {**docs, **extra}.items()}
    category_of = {k: status_category(d) for k, d in {**docs, **extra}.items()}
    owner_of = {
        k: (((d["fields"].get("assignee") or {}).get("displayName")) or "").strip()
        for k, d in {**docs, **extra}.items()
    }

    # Descriptors for the targets as well, so a blocker's ask can carry its own age.
    target_items = [describe(k, d, args.sp_field, today) for k, d in extra.items()]
    by_key = {entry["key"]: entry for entry in items + target_items}

    # Exact status transitions and owner changes reset the movement clock. Must run
    # before the asks are derived.
    signals = apply_changelog_signals(items + target_items, today, args.jobs)
    if signals.get("failed"):
        print(
            f"warning: {signals['failed']} of {signals['checked']} changelog reads "
            "failed; those items fall back to the status category date",
            file=sys.stderr,
        )

    base_url = jira_base_url()

    def ref(key: str) -> str:
        return ticket_ref(key, base_url, args.link_style)

    pr_signal = (
        apply_pull_requests(items, args.jobs)
        if not args.no_prs
        else {"available": True, "failed": 0, "checked": 0, "found": 0, "skipped": True}
    )

    for item in items:
        item["open_blockers"] = open_links(item["blocked_by"], category_of)
        item["blocked"] = bool(item["open_blockers"])
        item["blocker_detail"] = [
            {
                "key": k,
                "status": status_of.get(k, "?"),
                "owner": owner_of.get(k) or None,
                "days_in_status": by_key[k]["days_in_status"] if k in by_key else None,
            }
            for k in item["open_blockers"]
        ]
        item["blocks_open"] = open_links(item["blocks"], category_of)
        item["ask"] = suggested_ask(item, ref)
        prs = pr_refs(item, args.link_style)
        if prs:
            # The pull request is where a reviewer acts, so it rides in the ask
            # rather than in a seventh column. The generic review ask names no
            # ticket, so the PR becomes its object instead of a suffix.
            if item["ask"].startswith("Ask a reviewer"):
                item["ask"] = f"{item['ask']} {prs}"
            else:
                item["ask"] = f"{item['ask']} - {prs}"

    owned = [i for i in items if i["owner"]]
    unowned = [i for i in items if not i["owner"]]
    for item in owned:
        item["needs_action"] = item["days_without_movement"] >= args.action_after

    needing = sorted(
        [i for i in owned if i["needs_action"]], key=lambda i: -i["days_without_movement"]
    )
    queue = needing[: args.max_rows]

    escalation = [i["key"] for i in needing if i["days_without_movement"] >= 20 and not i["blocked"]]
    excluded = [i["key"] for i in needing if i["days_without_movement"] >= 20 and i["blocked"]]

    gating = sorted(
        [i for i in unowned if i["blocks_open"]], key=lambda i: -len(i["blocks_open"])
    )

    owners: dict[str, dict] = {}
    for item in owned:
        bucket = owners.setdefault(item["owner"], {"owner": item["owner"], "items": 0, "sp": 0})
        bucket["items"] += 1
        bucket["sp"] += item["sp"]

    return {
        "generated_for": today.isoformat(),
        "project": args.project,
        "jira_base_url": base_url,
        "link_style": args.link_style,
        "sprint": sprint,
        "definition": (
            "Movement = the most recent of the exact last status change, the last human "
            "comment and the assignment to the current owner; a New to Backlog "
            "reclassification is not movement, and the `updated` field is ignored "
            "because bulk edits inflate it"
        ),
        "changelog_signal": signals,
        "pr_signal": pr_signal,
        "totals": {
            "items": len(items),
            "sp": sum(i["sp"] for i in items),
            "owned": {"items": len(owned), "sp": sum(i["sp"] for i in owned)},
            "unowned": {"items": len(unowned), "sp": sum(i["sp"] for i in unowned)},
        },
        "queue": queue,
        "queue_needing_action": len(needing),
        "queue_overflow": max(0, len(needing) - len(queue)),
        "no_action": [
            {
                "key": i["key"],
                "owner": i["owner"],
                "days_without_movement": i["days_without_movement"],
                "days_in_status": i["days_in_status"],
                "days_since_comment": i.get("days_since_comment"),
                "days_since_assignment": i.get("days_since_assignment"),
                "assigned": i.get("assigned"),
            }
            for i in sorted(owned, key=lambda i: i["days_without_movement"])
            if not i["needs_action"]
        ],
        "escalation_20d": escalation,
        "escalation_excluded_blocked": excluded,
        "assignment_gap": {
            "items": len(unowned),
            "sp": sum(i["sp"] for i in unowned),
            "sizes": sorted({i["sp"] for i in unowned}),
            "blocking_other_work": [
                {"key": i["key"], "sp": i["sp"], "blocks_open": len(i["blocks_open"])} for i in gating
            ],
            "keys": [i["key"] for i in sorted(unowned, key=lambda i: -i["days_without_movement"])],
        },
        "concentration": sorted(owners.values(), key=lambda o: (-o["sp"], -o["items"])),
        "next_pulse": args.next_pulse,
    }


def render_text(data: dict) -> str:
    sprint = data["sprint"]
    totals = data["totals"]
    lines = [f"Pulse check - {sprint['name']}, {data['generated_for']}"]
    if data.get("jira_base_url"):
        lines.append(f"Jira: {data['jira_base_url']}")
    lines.append("")

    queue = data["queue"]
    base_url = data.get("jira_base_url")
    style = data.get("link_style", "markdown")

    def ref(key: str) -> str:
        return ticket_ref(key, base_url, style)

    lines.append(
        f"Nudge queue ({len(queue)} of {totals['owned']['items']} owned large items need action):"
    )
    if queue:
        lines.append("")
        lines.append("| Ticket | Title | Owner | SP | Status · age | Ask |")
        lines.append("|--------|-------|-------|----|--------------|-----|")
        for item in queue:
            when = f"{item['days_without_movement']}d"
            if assignment_is_binding(item):
                when += f" (assigned {item['assigned'][5:]})"
            elif item["status"] == "Backlog":
                when += f" (since {item['created'][5:]})"
            lines.append(
                f"| {ticket_ref(item['key'], base_url, style)} | {cell(item['summary'])} | "
                f"{item['owner'].split()[0]} | {int(item['sp'])} | "
                f"{item['status']} · {when} | {cell(item['ask'])} |"
            )
    else:
        lines.append("nothing needs action this pulse")
    if data["queue_overflow"]:
        lines.append(f"+{data['queue_overflow']} more items need action")

    if data["no_action"]:
        entries = []
        for i in data["no_action"]:
            entry = f"{ref(i['key'])} ({i['days_without_movement']}d"
            if assignment_is_binding(i) and i.get("assigned"):
                entry += f", assigned {i['assigned'][5:]}"
            entries.append(f"{entry})")
        lines.append(f"\nNo action: {', '.join(entries)}")

    if data["escalation_20d"]:
        keys = ", ".join(ref(key) for key in data["escalation_20d"])
        lines.append(f"\nEscalation 20+ days: {keys}"
                     " — lead decides: start, split, re-scope or drop")
    if data["escalation_excluded_blocked"]:
        keys = ", ".join(ref(key) for key in data["escalation_excluded_blocked"])
        lines.append(f"(excluded as blocked: {keys})")

    gap = data["assignment_gap"]
    if gap["items"]:
        sizes = ", ".join(f"{int(s)} SP" for s in gap["sizes"]) or "n/a"
        lines.append(f"\nAssignment gap: {gap['items']} items / {int(gap['sp'])} SP have no owner")
        lines.append(f"- sizes present: {sizes}")
        if gap["blocking_other_work"]:
            top = ", ".join(
                f"{ref(o['key'])} (blocks {o['blocks_open']})"
                for o in gap["blocking_other_work"][:4]
            )
            lines.append(f"- assign these first: {top}")

    if data["concentration"]:
        top = data["concentration"][0]
        if top["items"] > 1:
            lines.append(
                f"\nConcentration: {top['owner']} holds {top['items']} of "
                f"{totals['owned']['items']} owned items ({int(top['sp'])} of "
                f"{int(totals['owned']['sp'])} SP)"
            )

    lines.append("")
    signal = data.get("changelog_signal") or {}
    if signal.get("failed"):
        lines.append(
            f"Signal: partial - {signal['failed']} of {signal['checked']} changelog "
            "reads failed, so those items use the status category date"
        )
    elif signal.get("available") is False:
        lines.append(
            "Signal: partial - no JIRA_API_TOKEN, so movement ignores exact status "
            "changes and assignments"
        )
    prs = data.get("pr_signal") or {}
    if prs.get("failed"):
        lines.append(
            f"Signal: partial - {prs['failed']} of {prs['checked']} pull request reads "
            "failed, so those items carry no pull request link"
        )
    elif prs.get("available") is False and not prs.get("skipped"):
        lines.append(
            "Signal: partial - pull request links unavailable "
            f"({prs.get('reason') or 'no JIRA_API_TOKEN'})"
        )
    lines.append(data["definition"])
    lines.append(f"Next pulse: {data['next_pulse'] or 'to be scheduled'}")
    return "\n".join(lines)


def field_name(value: str) -> str:
    """A field name sits inside quotes in JQL; keep quotes and escapes out."""
    if '"' in value or "\\" in value:
        raise argparse.ArgumentTypeError(f"not a Jira field name: {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect the sprint pulse check data.")
    parser.add_argument("--project", default="HYPERFLEET", type=project_key)
    parser.add_argument("--jira", default="jira", help="jira-cli binary")
    parser.add_argument("--min-sp", type=int, default=5)
    parser.add_argument("--max-rows", type=int, default=7)
    parser.add_argument("--action-after", type=int, default=5, help="days without movement that trigger an ask")
    parser.add_argument("--sp-field", default="customfield_10028", help="custom field id holding story points")
    parser.add_argument("--sp-field-name", default="Story Points", type=field_name, help="JQL name of the story points field")
    parser.add_argument("--today", help="YYYY-MM-DD, for reproducible runs")
    parser.add_argument(
        "--no-prs",
        action="store_true",
        help="skip the pull request lookup for items in review",
    )
    parser.add_argument("--next-pulse", help="YYYY-MM-DD printed in the text output")
    parser.add_argument(
        "--link-style",
        choices=["markdown", "slack", "bare"],
        default="markdown",
        help="how ticket keys are rendered in the table",
    )
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    try:
        data = build(args)
    except PulseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(render_text(data) if args.format == "text" else json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
