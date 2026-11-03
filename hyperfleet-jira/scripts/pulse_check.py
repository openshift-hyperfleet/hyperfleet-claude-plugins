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
import base64
import http.client
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path


class PulseError(Exception):
    pass


class ChangelogUnavailable(Exception):
    """A changelog read failed; it must not be read as "no entry"."""


# A move between these statuses is classification, not work. HYPERFLEET creates
# issues in `New`; a bulk New -> Backlog sweep must not reset the movement clock.
TRIVIAL_STATUSES = {"New", "Backlog"}


def status_change_counts(change: dict) -> bool:
    """True when a status transition is workflow movement, not classification."""
    from_status = (change.get("fromString") or "").strip()
    to_status = (change.get("toString") or "").strip()
    return not (from_status in TRIVIAL_STATUSES and to_status in TRIVIAL_STATUSES)


def run_jira(args: list[str], binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=120
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise PulseError(f"jira {' '.join(args[:2])} could not run: {exc}") from exc
    if proc.returncode != 0:
        raise PulseError(
            f"jira {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:300]}"
        )
    return proc.stdout


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def jira_base_url() -> str | None:
    """Read the server from the jira-cli config, so the report never hardcodes it.

    Bare keys are only resolvable if the reader knows the server; one line here
    saves every table from carrying a link per row.
    """
    config = Path.home() / ".config" / ".jira" / ".config.yml"
    try:
        text = config.read_text()
    except OSError:
        return None
    match = re.search(r"^server:\s*(\S+)", text, re.MULTILINE)
    if not match:
        return None
    server = match.group(1).rstrip("/")
    if "://" not in server:
        server = f"https://{server}"
    if not server.startswith("https://"):
        return None
    return f"{server}/browse/"


def ticket_ref(key: str, base_url: str | None, style: str) -> str:
    """Render a ticket key for the destination.

    The same report is pasted into the TUI, Slack and log files, and only one of
    the three understands `[text](url)`. Keep the syntax switchable instead of
    guessing at render time.
    """
    if not base_url or style == "bare":
        return key
    url = f"{base_url}{key}"
    if style == "slack":
        return f"<{url}|{key}>"
    return f"[{key}]({url})"


def prose(text: str) -> str:
    return " ".join(str(text or "").split())


def cell(text: str) -> str:
    """One table cell: no pipes, no newlines, whatever the text contains."""
    return prose(text).replace("|", "\\|")


def jira_api() -> tuple[str, str] | None:
    """(server, basic-auth header) for Jira's REST API, or None.

    The changelog is the only place Jira records the exact status transition and
    the owner change, and jira-cli exposes neither. The token is the same
    `JIRA_API_TOKEN` the CLI uses; without it both signals are unavailable and the
    scripts fall back to `statusCategoryChangedDate`.
    """
    token = os.environ.get("JIRA_API_TOKEN")
    if not token:
        return None
    config = Path.home() / ".config" / ".jira" / ".config.yml"
    try:
        text = config.read_text()
    except OSError:
        return None
    server = re.search(r"^server:\s*(\S+)", text, re.MULTILINE)
    login = re.search(r"^login:\s*(\S+)", text, re.MULTILINE)
    if not server or not login:
        return None
    base = server.group(1).rstrip("/")
    if "://" not in base:
        base = f"https://{base}"
    if not base.startswith("https://"):
        # The Basic auth header carries the API token; never send it in cleartext.
        return None
    auth = base64.b64encode(f"{login.group(1)}:{token}".encode()).decode()
    return base, auth


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: urllib copies the Authorization header to the target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


def open_changelog(request: urllib.request.Request):
    """GET that never follows a redirect, so the token stays on the Jira host."""
    return urllib.request.build_opener(NoRedirect).open(request, timeout=15)


def changelog_dates(
    key: str, account_id: str | None, api: tuple[str, str] | None
) -> tuple[date | None, date | None]:
    """(last status change, date the current assignee took the issue).

    Both come from the same changelog payload, so the report pays one request per
    issue. `statusCategoryChangedDate` is a fallback, not the truth: it ignores
    moves inside a category, such as In Progress -> Review.

    Either value is None when the changelog has no such entry (the issue was
    created in its current status or already assigned). A failed request raises
    `ChangelogUnavailable` instead: "the API said no" and "the API did not
    answer" must not collapse into the same value, because the caller falls back
    to a different clock for the second one.
    """
    if not api:
        return None, None
    server, auth = api
    url = f"{server}/rest/api/3/issue/{key}?expand=changelog&fields=status,assignee"
    request = urllib.request.Request(
        url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"}
    )
    try:
        with open_changelog(request) as response:
            payload = json.load(response)
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        ValueError,
    ) as exc:
        # HTTPError is a URLError and JSONDecodeError/UnicodeDecodeError are
        # ValueErrors: every transport or decode failure is one counted failure.
        raise ChangelogUnavailable(f"{key}: {type(exc).__name__}") from exc

    changelog = payload.get("changelog") or {}
    histories = changelog.get("histories") or []
    try:
        total = int(changelog.get("total") or 0)
    except (TypeError, ValueError):
        total = 0
    if total > len(histories):
        # The inline changelog is capped; a truncated read can miss the exact
        # transition, so it must be counted instead of looking like "no entry".
        raise ChangelogUnavailable(
            f"{key}: changelog truncated ({len(histories)} of {total} entries)"
        )

    status_dates: list[date] = []
    assignment_dates: list[date] = []
    for entry in histories:
        changed_status = changed_assignee = False
        for change in entry.get("items") or []:
            if change.get("field") == "status":
                if status_change_counts(change):
                    changed_status = True
            elif (
                account_id
                and change.get("field") == "assignee"
                and change.get("to") == account_id
            ):
                changed_assignee = True
        if changed_status:
            status_dates.append(parse_date(entry["created"]))
        if changed_assignee:
            assignment_dates.append(parse_date(entry["created"]))

    status_entered = max(status_dates) if status_dates else None
    assigned = max(assignment_dates) if assignment_dates else None
    return status_entered, assigned


def read_changelog(
    key: str, account_id: str | None, api: tuple[str, str] | None
) -> tuple[tuple[date | None, date | None], str | None]:
    """(dates, error). A failed read is counted, not read as "no entry".

    Collapsing both into (None, None) lets an expired token walk every item back
    to the status category clock while the report still calls it the exact
    signal, and the 20-day rung then fires on items that moved last week.
    """
    try:
        return changelog_dates(key, account_id, api), None
    except ChangelogUnavailable as exc:
        return (None, None), str(exc)


def apply_changelog_signals(items: list[dict], today: date, jobs: int) -> dict:
    """Reset the movement clock on an exact status change or a new owner.

    `statusCategoryChangedDate` only moves between To Do / In Progress / Done, so
    an item that entered Review yesterday can still look stale by the category
    date. The changelog has the exact transition.

    Assignment matters for the same reason blocked time does: time before the
    current owner had the ticket is not the current owner's time. Both signals can
    only lower the clock; neither can raise it.
    """
    for item in items:
        item["status_entered"] = None
        item["assigned"] = None
        item["days_since_assignment"] = None

    api = jira_api()
    if not api:
        return {
            "available": False,
            "failed": 0,
            "checked": len(items),
            "reason": "JIRA_API_TOKEN or jira-cli login not configured",
        }
    if not items:
        return {
            "available": True,
            "failed": 0,
            "checked": 0,
            "status_dates": 0,
            "assignments": 0,
        }

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(
            pool.map(
                lambda item: read_changelog(item["key"], item.get("assignee_id"), api),
                items,
            )
        )

    status_found = assignment_found = failed = 0
    for item, ((status_entered, assigned), error) in zip(items, results):
        if error:
            failed += 1
        if status_entered:
            status_found += 1
            item["status_entered"] = status_entered.isoformat()
            item["days_in_status"] = min(
                item["days_in_status"], (today - status_entered).days
            )
        if assigned:
            assignment_found += 1
            item["assigned"] = assigned.isoformat()
            item["days_since_assignment"] = (today - assigned).days

        signals = [item["days_in_status"]]
        if item["days_since_comment"] is not None:
            signals.append(item["days_since_comment"])
        if item["days_since_assignment"] is not None:
            signals.append(item["days_since_assignment"])
        item["days_without_movement"] = min(signals)

    return {
        "available": failed == 0,
        "failed": failed,
        "checked": len(items),
        "status_dates": status_found,
        "assignments": assignment_found,
    }


def active_sprint(project: str, binary: str) -> dict:
    out = run_jira(
        [
            "sprint", "list", "-p", project, "--state", "active",
            "--plain", "--no-truncate",
            "--columns", "ID,NAME,START,END,STATE",
        ],
        binary,
    )
    rows = [line.split("\t") for line in out.strip().splitlines()]
    if len(rows) < 2:
        raise PulseError(f"no active sprint found for project {project}")
    if len(rows) > 2:
        print(f"warning: {len(rows) - 1} active sprints; using {rows[1][1]}", file=sys.stderr)
    sid, name, start, end, state = (rows[1] + [""] * 5)[:5]
    return {"id": sid, "name": name, "start": start[:10], "end": end[:10], "state": state}


def large_item_keys(project: str, min_sp: int, sp_field_name: str, binary: str) -> list[str]:
    jql = (
        f'project = {project} AND sprint in openSprints() '
        f'AND "{sp_field_name}" >= {min_sp} AND status != Closed'
    )
    out = run_jira(
        ["issue", "list", "-q", jql, "-p", project, "--plain", "--no-headers", "--columns", "KEY"],
        binary,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def fetch_issue(key: str, project: str, binary: str) -> dict:
    try:
        return json.loads(run_jira(["issue", "view", key, "-p", project, "--raw"], binary))
    except (PulseError, json.JSONDecodeError) as exc:
        raise PulseError(f"could not read {key}: {exc}") from exc


def fetch_all(keys: list[str], project: str, binary: str, jobs: int) -> dict[str, dict]:
    unique = sorted(set(keys))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        docs = list(pool.map(lambda k: fetch_issue(k, project, binary), unique))
    return {doc["key"]: doc for doc in docs}


def link_targets(doc: dict) -> tuple[list[str], list[str]]:
    """Return (blocked_by, blocks) keys from the issue links.

    Orientation matters: Jira labels every Blocks link with inward="is blocked by"
    and outward="blocks", so the type label alone cannot tell you the direction.
    What decides is which side of the link carries the other issue.
    """
    blocked_by, blocks = [], []
    for link in doc["fields"].get("issuelinks") or []:
        kind = link.get("type") or {}
        inward, outward = link.get("inwardIssue"), link.get("outwardIssue")
        if inward and inward.get("key") and (kind.get("inward") or "").strip().lower() == "is blocked by":
            blocked_by.append(inward["key"])
        elif outward and outward.get("key") and (kind.get("outward") or "").strip().lower() == "blocks":
            blocks.append(outward["key"])
    return blocked_by, blocks


def human_comment_dates(doc: dict) -> list[date]:
    dates = []
    for comment in (doc["fields"].get("comment") or {}).get("comments") or []:
        author = comment.get("author") or {}
        if author.get("accountType") == "app":
            continue
        created = comment.get("created")
        if created:
            dates.append(parse_date(created))
    return dates


def describe(key: str, doc: dict, sp_field: str, today: date) -> dict:
    fields = doc["fields"]
    status_changed = parse_date(fields["statuscategorychangedate"])
    comments = human_comment_dates(doc)
    last_comment = max(comments) if comments else None
    days_in_status = (today - status_changed).days
    days_since_comment = (today - last_comment).days if last_comment else None
    signals = [days_in_status] + ([days_since_comment] if days_since_comment is not None else [])
    blocked_by, blocks = link_targets(doc)
    return {
        "key": key,
        "summary": fields.get("summary", ""),
        "type": (fields.get("issuetype") or {}).get("name", ""),
        "sp": fields.get(sp_field) or 0,
        "owner": ((fields.get("assignee") or {}).get("displayName") or "").strip(),
        "assignee_id": (fields.get("assignee") or {}).get("accountId") or None,
        "status": (fields.get("status") or {}).get("name", ""),
        "priority": (fields.get("priority") or {}).get("name", ""),
        "epic": (fields.get("parent") or {}).get("key"),
        "labels": fields.get("labels") or [],
        "created": (fields.get("created") or "")[:10],
        "days_without_movement": min(signals),
        "days_in_status": days_in_status,
        "days_since_comment": days_since_comment,
        "last_comment": last_comment.isoformat() if last_comment else None,
        "blocked_by": blocked_by,
        "blocks": blocks,
    }


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


def suggested_ask(item: dict) -> str:
    """One imperative per item: verb first, then who and what artifact.

    The verb comes from a fixed set - ask to approve/reject, assign, unblock,
    post, start, propose a split - so the column can be scanned and counted.
    The item's own age lives in the `Status . age` cell, so the text never
    repeats it; a blocker"s age does appear, because that clock is not in the
    table and it is what makes the blocker urgent or not.
    """
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
                    f"ask {d['owner'].split()[0]} to approve or reject {d['key']} "
                    f"(Review{when})"
                )
            elif not d.get("owner"):
                clauses.append(f"assign {d['key']}")
            elif d["status"] == "In Progress":
                clauses.append(f"ask {d['owner'].split()[0]} for the status of {d['key']}")
            else:
                clauses.append(f"ask {d['owner'].split()[0]} to start or drop {d['key']}")
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
    keys = large_item_keys(args.project, args.min_sp, args.sp_field_name, args.jira)
    docs = fetch_all(keys, args.project, args.jira, args.jobs)

    items = [describe(k, d, args.sp_field, today) for k, d in docs.items()]

    # Resolve the status of every link target so "blocked" and "blocks" mean open work only.
    targets = {k for item in items for k in item["blocked_by"] + item["blocks"]} - set(docs)
    extra = fetch_all(sorted(targets), args.project, args.jira, args.jobs) if targets else {}
    status_of = {k: (d["fields"].get("status") or {}).get("name", "") for k, d in docs.items()}
    status_of.update({k: (d["fields"].get("status") or {}).get("name", "") for k, d in extra.items()})
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

    for item in items:
        item["open_blockers"] = [k for k in item["blocked_by"] if status_of.get(k) != "Closed"]
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
        item["blocks_open"] = [k for k in item["blocks"] if status_of.get(k) != "Closed"]
        item["ask"] = suggested_ask(item)

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
        "jira_base_url": jira_base_url(),
        "link_style": args.link_style,
        "sprint": sprint,
        "definition": (
            "Movement = the most recent of the exact last status change, the last human "
            "comment and the assignment to the current owner; a New to Backlog "
            "reclassification is not movement, and the `updated` field is ignored "
            "because bulk edits inflate it"
        ),
        "changelog_signal": signals,
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
            entry = f"{i['key']} ({i['days_without_movement']}d"
            if assignment_is_binding(i) and i.get("assigned"):
                entry += f", assigned {i['assigned'][5:]}"
            entries.append(f"{entry})")
        lines.append(f"\nNo action: {', '.join(entries)}")

    if data["escalation_20d"]:
        lines.append(f"\nEscalation 20+ days: {', '.join(data['escalation_20d'])}"
                     " — lead decides: start, split, re-scope or drop")
    if data["escalation_excluded_blocked"]:
        lines.append(f"(excluded as blocked: {', '.join(data['escalation_excluded_blocked'])})")

    gap = data["assignment_gap"]
    if gap["items"]:
        sizes = ", ".join(f"{int(s)} SP" for s in gap["sizes"]) or "n/a"
        lines.append(f"\nAssignment gap: {gap['items']} items / {int(gap['sp'])} SP have no owner")
        lines.append(f"- sizes present: {sizes}")
        if gap["blocking_other_work"]:
            top = ", ".join(
                f"{o['key']} (blocks {o['blocks_open']})" for o in gap["blocking_other_work"][:4]
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
    lines.append(data["definition"])
    lines.append(f"Next pulse: {data['next_pulse'] or 'to be scheduled'}")
    return "\n".join(lines)


PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")


def project_key(value: str) -> str:
    """A project key lands in JQL unquoted, so reject anything that is not one."""
    if not PROJECT_KEY.match(value):
        raise argparse.ArgumentTypeError(f"not a Jira project key: {value!r}")
    return value


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
