#!/usr/bin/env python3
"""Sprint status data collector for the HyperFleet sprint status report.

Reads the active sprint, every issue in it, and the previous sprint's baseline,
then prints one JSON document (default) or a ready-to-paste text report.

The script exists because the numbers this report needs cannot be obtained from
`jira issue list`:

  - story points live in a custom field (`customfield_10028`), which
    `jira issue list` does not return; only `jira issue view --raw` has it
  - `--paginate` ignores its `<from>` offset and caps at 100, so a sprint with
    more than 100 issues truncates silently; this script pages by key range
  - HYPERFLEET has no `Done` / `To Do` statuses, so `status = Done` matches
    nothing; status categories are used instead
  - the status and assignee changelogs are not exposed by jira-cli, so the exact
    status transition and assignment signal read the REST API with
    `JIRA_API_TOKEN`; without it, movement falls back to the status category date
    and human comments

Read-only. The script never writes to Jira.

Usage:
    python3 sprint_status.py                        # JSON, current sprint, today
    python3 sprint_status.py --format markdown      # ready-to-paste report
    python3 sprint_status.py --today 2026-11-03     # reproducible run
    python3 sprint_status.py --project HYPERFLEET --stale-days 5

The Markdown report contains tables. Present it as Markdown: wrapping it in a
code fence turns the tables into literal pipes. Use `--format json` when a
caller needs the numbers without the layout.
"""

from __future__ import annotations

import argparse
import base64
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


class SprintError(Exception):
    pass


class ChangelogUnavailable(Exception):
    """A changelog read failed; it must not be read as "no entry"."""


CATEGORY_ORDER = {"To Do": 0, "In Progress": 1, "Done": 2}

# A move between these statuses is classification, not work. HYPERFLEET creates
# issues in `New`; a bulk New -> Backlog sweep must not reset the movement clock.
TRIVIAL_STATUSES = {"New", "Backlog"}


def status_change_counts(change: dict) -> bool:
    """True when a status transition is workflow movement, not classification."""
    from_status = (change.get("fromString") or "").strip()
    to_status = (change.get("toString") or "").strip()
    return not (from_status in TRIVIAL_STATUSES and to_status in TRIVIAL_STATUSES)


# --------------------------------------------------------------------------
# jira-cli plumbing
# --------------------------------------------------------------------------


def run_jira(args: list[str], binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=120
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise SprintError(f"jira {' '.join(args[:2])} could not run: {exc}") from exc
    if proc.returncode != 0:
        raise SprintError(
            f"jira {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:300]}"
        )
    return proc.stdout


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def key_number(key: str) -> int:
    _, _, number = key.rpartition("-")
    return int(number)


def jql_project(project: str) -> str:
    return f"project = {project}"


def search_keys(jql: str, project: str, binary: str, limit: int = 100) -> list[str]:
    """List every key matching `jql`, past the 100-issue page cap.

    `jira issue list --paginate <from>:<limit>` ignores `<from>`: every page
    returns the same first N issues. It also rejects a limit above 100. So the
    only way to walk a larger result is to move the search window with JQL
    itself, using the lowest key of each batch as the next boundary.

    Returns the keys in the order the CLI emitted them, plus a `truncated` flag
    is not needed: an incomplete result raises instead of lying.
    """
    keys: list[str] = []
    seen: set[str] = set()
    boundary: str | None = None

    for _ in range(200):
        query = jql if boundary is None else f"({jql}) AND key < {boundary}"
        out = run_jira(
            [
                "issue", "list", "-q", query, "-p", project,
                "--plain", "--no-headers", "--columns", "KEY",
                "--order-by", "key", "--paginate", f"0:{limit}",
            ],
            binary,
        )
        batch = [line.strip() for line in out.splitlines() if line.strip()]
        fresh = [key for key in batch if key not in seen]
        if not fresh:
            return keys
        keys.extend(fresh)
        seen.update(fresh)
        if len(batch) < limit:
            return keys
        boundary = min(batch, key=key_number)

    raise SprintError(
        f"gave up paging after 200 batches ({len(keys)} keys); narrow the JQL"
    )


def sprint_rows(project: str, state: str, binary: str) -> list[dict]:
    out = run_jira(
        [
            "sprint", "list", "-p", project, "--state", state,
            "--plain", "--no-truncate",
            "--columns", "ID,NAME,START,END,STATE",
        ],
        binary,
    )
    lines = [line for line in out.strip().splitlines() if line.strip()]
    rows = []
    for line in lines[1:]:
        sid, name, start, end, sprint_state = (line.split("\t") + [""] * 5)[:5]
        rows.append(
            {
                "id": sid.strip(),
                "name": name.strip(),
                "start": start.strip()[:10],
                "end": end.strip()[:10],
                "state": sprint_state.strip(),
            }
        )
    return rows


def active_sprint(project: str, binary: str) -> dict:
    rows = sprint_rows(project, "active", binary)
    if not rows:
        raise SprintError(f"no active sprint found for project {project}")
    if len(rows) > 1:
        print(f"warning: {len(rows)} active sprints; using {rows[0]['name']}", file=sys.stderr)
    return rows[0]


def previous_sprint(
    project: str, binary: str, before: str | None = None
) -> dict | None:
    """The sprint the target sprint is compared against.

    `--sprint` can name a closed sprint, and then the latest closed sprint may be
    the target itself or a later one; only sprints that ended before the target
    started are baselines.
    """
    rows = sprint_rows(project, "closed", binary)
    if before:
        rows = [row for row in rows if row["end"] and row["end"] < before]
    if not rows:
        return None
    return max(rows, key=lambda row: row["end"])


def fetch_issue(key: str, project: str, binary: str) -> dict:
    try:
        return json.loads(
            run_jira(["issue", "view", key, "-p", project, "--raw"], binary)
        )
    except (SprintError, json.JSONDecodeError) as exc:
        raise SprintError(f"could not read {key}: {exc}") from exc


def fetch_all(keys: list[str], project: str, binary: str, jobs: int) -> dict[str, dict]:
    unique = sorted(set(keys), key=key_number)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        docs = list(pool.map(lambda key: fetch_issue(key, project, binary), unique))
    return {doc["key"]: doc for doc in docs}


# --------------------------------------------------------------------------
# Issue shape
# --------------------------------------------------------------------------


def link_targets(doc: dict) -> tuple[list[str], list[str]]:
    """Return (blocked_by, blocks) keys from the issue links.

    Jira labels every Blocks link with inward="is blocked by" and
    outward="blocks", so the type label alone cannot tell you the direction.
    What decides is which side of the link carries the other issue.
    """
    blocked_by, blocks = [], []
    for link in doc["fields"].get("issuelinks") or []:
        kind = link.get("type") or {}
        inward, outward = link.get("inwardIssue"), link.get("outwardIssue")
        if (
            inward
            and inward.get("key")
            and (kind.get("inward") or "").strip().lower() == "is blocked by"
        ):
            blocked_by.append(inward["key"])
        elif (
            outward
            and outward.get("key")
            and (kind.get("outward") or "").strip().lower() == "blocks"
        ):
            blocks.append(outward["key"])
    return blocked_by, blocks


def human_comment_dates(doc: dict) -> list[date]:
    """Comment dates written by people, not integrations.

    Jira automation comments (`author.accountType == "app"`) are not movement:
    a ticket whose only recent comment came from "Automation for Jira" was not
    touched by anyone.
    """
    dates = []
    for comment in (doc["fields"].get("comment") or {}).get("comments") or []:
        author = comment.get("author") or {}
        if author.get("accountType") == "app":
            continue
        created = comment.get("created")
        if created:
            dates.append(parse_date(created))
    return dates


def sprint_of(doc: dict, sprint_id: str) -> dict | None:
    for sprint in doc["fields"].get("customfield_10020") or []:
        if str(sprint.get("id")) == str(sprint_id):
            return sprint
    return None


def describe(doc: dict, sp_field: str, today: date) -> dict:
    fields = doc["fields"]
    status = fields.get("status") or {}
    category = (status.get("statusCategory") or {}).get("name", "")
    status_changed = parse_date(fields["statuscategorychangedate"])
    comments = human_comment_dates(doc)
    last_comment = max(comments) if comments else None
    signals = [(today - status_changed).days]
    if last_comment:
        signals.append((today - last_comment).days)
    blocked_by, blocks = link_targets(doc)
    points = fields.get(sp_field)

    return {
        "key": doc["key"],
        "summary": (fields.get("summary") or "").strip(),
        "type": (fields.get("issuetype") or {}).get("name", ""),
        "sp": points if isinstance(points, (int, float)) else None,
        "owner": ((fields.get("assignee") or {}).get("displayName") or "").strip(),
        "assignee_id": (fields.get("assignee") or {}).get("accountId") or None,
        "status": status.get("name", ""),
        "category": category,
        "priority": (fields.get("priority") or {}).get("name", ""),
        "epic": (fields.get("parent") or {}).get("key"),
        "created": (fields.get("created") or "")[:10],
        "days_in_status": (today - status_changed).days,
        "days_since_comment": (today - last_comment).days if last_comment else None,
        "days_without_movement": min(signals),
        "last_comment": last_comment.isoformat() if last_comment else None,
        "blocked_by": blocked_by,
        "blocks": blocks,
        "is_done": category == "Done",
    }


def resolve_blockers(
    items: list[dict], docs: dict[str, dict], project: str, binary: str, jobs: int
) -> None:
    """Annotate each item with the blockers that are still open.

    A blocker only counts while it is not Done: a closed blocker no longer
    explains why the item sits still.
    """
    known = set(docs)
    targets = {key for item in items for key in item["blocked_by"]} - known
    extra = fetch_all(sorted(targets), project, binary, jobs) if targets else {}

    status_of = {
        key: {
            "status": (doc["fields"].get("status") or {}).get("name", ""),
            "category": (
                ((doc["fields"].get("status") or {}).get("statusCategory") or {}).get("name", "")
            ),
            "owner": ((doc["fields"].get("assignee") or {}).get("displayName") or "").strip(),
        }
        for key, doc in {**docs, **extra}.items()
    }

    for item in items:
        item["blocker_detail"] = [
            {"key": key, **status_of.get(key, {"status": "?", "category": "?", "owner": ""})}
            for key in item["blocked_by"]
        ]
        item["open_blockers"] = [
            detail["key"]
            for detail in item["blocker_detail"]
            if detail["category"] != "Done"
        ]
        item["blocked"] = bool(item["open_blockers"])


# --------------------------------------------------------------------------
# Aggregates
# --------------------------------------------------------------------------


def summarise(items: list[dict]) -> dict:
    sp_total = sum(item["sp"] or 0 for item in items)
    done = [item for item in items if item["is_done"]]

    by_status: dict[str, dict] = {}
    for item in items:
        bucket = by_status.setdefault(
            item["status"], {"status": item["status"], "category": item["category"], "items": 0, "sp": 0}
        )
        bucket["items"] += 1
        bucket["sp"] += item["sp"] or 0

    ordered_status = sorted(
        by_status.values(),
        key=lambda bucket: (CATEGORY_ORDER.get(bucket["category"], 9), bucket["status"]),
    )

    by_category: dict[str, dict] = {}
    for item in items:
        bucket = by_category.setdefault(
            item["category"], {"category": item["category"], "items": 0, "sp": 0}
        )
        bucket["items"] += 1
        bucket["sp"] += item["sp"] or 0

    done_sp = sum(item["sp"] or 0 for item in done)
    return {
        "items": len(items),
        "sp": sp_total,
        "done": {"items": len(done), "sp": done_sp},
        "remaining": {
            "items": len(items) - len(done),
            "sp": sp_total - done_sp,
        },
        "by_status": ordered_status,
        "by_category": sorted(
            by_category.values(),
            key=lambda bucket: CATEGORY_ORDER.get(bucket["category"], 9),
        ),
        "percent_by_sp": round(100 * done_sp / sp_total, 1) if sp_total else 0.0,
        "percent_by_items": round(100 * len(done) / len(items), 1) if items else 0.0,
    }


def workload(items: list[dict], statuses: list[str]) -> list[dict]:
    people: dict[str, dict] = {}
    for item in items:
        owner = item["owner"] or "Unassigned"
        bucket = people.setdefault(
            owner, {"owner": owner, "items": 0, "sp": 0, "by_status": {status: 0 for status in statuses}}
        )
        bucket["items"] += 1
        bucket["sp"] += item["sp"] or 0
        bucket["by_status"][item["status"]] = bucket["by_status"].get(item["status"], 0) + 1
    return sorted(
        people.values(),
        key=lambda person: (person["owner"] == "Unassigned", person["owner"].lower()),
    )


def carry_over(items: list[dict], stale_days: int) -> dict:
    """Items likely to spill, named rather than guessed.

    The rule is deliberately mechanical: an item is a carry-over candidate if it
    is not Done and nobody owns it, it has not moved in `stale_days`, or it has
    no estimate. Those are the three things the team can still fix today.
    """
    candidates = []
    for item in items:
        if item["is_done"]:
            continue
        reasons = []
        if not item["owner"]:
            reasons.append("unassigned")
        if item["days_without_movement"] >= stale_days and item["category"] != "To Do":
            reasons.append(f"{item['days_without_movement']}d without movement")
        if item["sp"] is None or item["sp"] == 0:
            reasons.append("no estimate")
        if reasons:
            candidates.append({**item, "reasons": reasons})

    # Unassigned first: it is the only reason on this list the lead can clear
    # today. Then the longest-stalled, then the largest.
    candidates.sort(
        key=lambda item: (
            0 if not item["owner"] else 1,
            -item["days_without_movement"],
            -(item["sp"] or 0),
        )
    )

    by_reason = {"unassigned": 0, "stale": 0, "unestimated": 0}
    for item in candidates:
        if not item["owner"]:
            by_reason["unassigned"] += 1
        if item["days_without_movement"] >= stale_days and item["category"] != "To Do":
            by_reason["stale"] += 1
        if item["sp"] is None or item["sp"] == 0:
            by_reason["unestimated"] += 1

    return {
        "items": len(candidates),
        "sp": sum(item["sp"] or 0 for item in candidates),
        "by_reason": by_reason,
        "candidates": candidates,
    }


def sprint_calendar(start: date, end: date, today: date) -> dict:
    """Calendar days, counted the way a person counts them.

    A sprint that starts on the 2nd and ends on the 22nd is 21 days, not 20: the
    end day counts. Subtracting the dates without the `+ 1` makes every report
    one day short, which reads as a bug even when the arithmetic is consistent.
    """
    total = max(1, (end - start).days + 1)
    elapsed = min(total, max(0, (today - start).days))
    return {
        "days_total": total,
        "days_elapsed": elapsed,
        "days_remaining": max(0, total - elapsed),
        "percent_elapsed": round(100 * elapsed / total, 1),
    }


def capacity(
    remaining_sp: float, sprint: dict, baseline: dict | None, today: date
) -> dict:
    """Compare what is left with what the previous sprint says the team delivers.

    This is a projection, not a promise: it assumes the last sprint's pace holds
    and that the sprints are comparable. It reports the headroom as well as the
    overage, because "0 SP over capacity" in a sprint that committed half of what
    the team delivered last time is not good news - it is an under-committed plan.
    """
    try:
        start = parse_date(sprint["start"])
        end = parse_date(sprint["end"])
    except (KeyError, ValueError):
        return {"available": False, "reason": "sprint dates unavailable"}

    calendar = sprint_calendar(start, end, today)
    days_remaining = calendar["days_remaining"]

    if not baseline or not baseline.get("delivered_sp") or not baseline.get("days"):
        return {
            "available": False,
            "reason": "no delivered baseline from the previous sprint",
            "days_remaining": days_remaining,
            "sprint_days": calendar["days_total"],
            "percent_elapsed": calendar["percent_elapsed"],
        }

    expected = round(baseline["delivered_sp"] * days_remaining / baseline["days"], 1)
    return {
        "available": True,
        "days_remaining": days_remaining,
        "sprint_days": calendar["days_total"],
        "percent_elapsed": calendar["percent_elapsed"],
        "baseline_sp": baseline["delivered_sp"],
        "baseline_days": baseline["days"],
        "expected_sp": expected,
        "remaining_sp": remaining_sp,
        "over_capacity_sp": round(max(0.0, remaining_sp - expected), 1),
        "headroom_sp": round(max(0.0, expected - remaining_sp), 1),
    }


def baseline_for(
    sprint: dict | None, project: str, sp_field: str, binary: str, jobs: int, today: date
) -> dict | None:
    """Previous sprint totals.

    `committed` is the SP currently sitting in that sprint, not the SP committed
    on day one: Jira keeps no record of scope added or removed mid-sprint, so the
    number is an upper bound. The report says so instead of implying precision
    it does not have.
    """
    if not sprint:
        return None
    jql = f'{jql_project(project)} AND sprint = {sprint["id"]}'
    keys = search_keys(jql, project, binary)
    if not keys:
        return None
    docs = fetch_all(keys, project, binary, jobs)
    items = [describe(doc, sp_field, today) for doc in docs.values()]
    committed = sum(item["sp"] or 0 for item in items)
    delivered = sum(item["sp"] or 0 for item in items if item["is_done"])
    try:
        days = (parse_date(sprint["end"]) - parse_date(sprint["start"])).days + 1
    except (KeyError, ValueError):
        days = None
    return {
        "sprint": sprint["name"],
        "id": sprint["id"],
        "items": len(items),
        "committed_sp": committed,
        "delivered_sp": delivered,
        "percent": round(100 * delivered / committed, 1) if committed else 0.0,
        "days": days,
    }


def jira_base_url() -> str | None:
    """Read the server from the jira-cli config, so the report never hardcodes it."""
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


def jira_api() -> tuple[str, str] | None:
    """(server, basic-auth header) for Jira's REST API, or None.

    The changelog is the only place Jira records the exact status transition and
    the owner change, and jira-cli exposes neither. The token is the same
    `JIRA_API_TOKEN` the CLI uses; without it both signals are unavailable and the
    report falls back to `statusCategoryChangedDate`.
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
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise ChangelogUnavailable(f"{key}: {type(exc).__name__}") from exc

    status_dates: list[date] = []
    assignment_dates: list[date] = []
    for entry in (payload.get("changelog") or {}).get("histories") or []:
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
    signal, inflating the stale list and the "needs a decision" count.
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


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def build(args) -> dict:
    today = parse_date(args.today) if args.today else datetime.now(timezone.utc).date()

    if args.sprint:
        sprint = next(
            (row for row in sprint_rows(args.project, "active,closed", args.jira) if row["id"] == args.sprint),
            None,
        )
        if sprint is None:
            raise SprintError(f"sprint {args.sprint} not found in project {args.project}")
    else:
        sprint = active_sprint(args.project, args.jira)

    jql = f'{jql_project(args.project)} AND sprint = {sprint["id"]}'
    keys = search_keys(jql, args.project, args.jira)
    docs = fetch_all(keys, args.project, args.jira, args.jobs)
    items = [describe(doc, args.sp_field, today) for doc in docs.values()]

    goal = None
    for doc in docs.values():
        sprint_field = sprint_of(doc, sprint["id"])
        if sprint_field and sprint_field.get("goal"):
            goal = sprint_field["goal"]
            break

    resolve_blockers(items, docs, args.project, args.jira, args.jobs)
    signals = apply_changelog_signals(
        [item for item in items if not item["is_done"]], today, args.jobs
    )
    if signals.get("failed"):
        print(
            f"warning: {signals['failed']} of {signals['checked']} changelog reads "
            "failed; those items fall back to the status category date",
            file=sys.stderr,
        )

    totals = summarise(items)
    open_items = [item for item in items if not item["is_done"]]
    open_statuses = [
        bucket["status"] for bucket in totals["by_status"] if bucket["category"] != "Done"
    ]
    people = workload(open_items, open_statuses)

    blocked = sorted(
        [item for item in open_items if item["blocked"]],
        key=lambda item: (-len(item["open_blockers"]), item["key"]),
    )
    high_priority = sorted(
        [item for item in open_items if item["priority"] == args.blocker_priority],
        key=lambda item: (item["category"] != "To Do", item["key"]),
    )
    priorities_seen = sorted({item["priority"] for item in items if item["priority"]})

    stale = sorted(
        [
            item
            for item in open_items
            if item["category"] != "To Do" and item["days_without_movement"] >= args.stale_days
        ],
        key=lambda item: -item["days_without_movement"],
    )
    missing_sp = [item for item in open_items if item["sp"] is None or item["sp"] == 0]
    unassigned = [item for item in open_items if not item["owner"]]

    baseline = baseline_for(
        previous_sprint(args.project, args.jira, sprint.get("start") or None)
        if not args.no_baseline
        else None,
        args.project,
        args.sp_field,
        args.jira,
        args.jobs,
        today,
    )

    risk = carry_over(items, args.stale_days)
    projection = capacity(totals["remaining"]["sp"], sprint, baseline, today)

    start = parse_date(sprint["start"]) if sprint.get("start") else None
    end = parse_date(sprint["end"]) if sprint.get("end") else None
    calendar = (
        sprint_calendar(start, end, today) if start and end else {}
    )

    scope = {"committed_sp": totals["sp"], "baseline_delivered_sp": None, "delta_percent": None}
    if baseline and baseline.get("delivered_sp"):
        scope["baseline_delivered_sp"] = baseline["delivered_sp"]
        scope["delta_percent"] = round(
            100 * (totals["sp"] - baseline["delivered_sp"]) / baseline["delivered_sp"], 1
        )

    return {
        "generated_for": today.isoformat(),
        "project": args.project,
        "jira_base_url": jira_base_url(),
        "link_style": args.link_style,
        "sprint": {
            **sprint,
            "goal": goal,
            "days_total": calendar.get("days_total"),
            "days_elapsed": calendar.get("days_elapsed"),
            "days_remaining": calendar.get("days_remaining"),
            "percent_elapsed": calendar.get("percent_elapsed"),
            "overdue": bool(end and today > end),
        },
        "totals": totals,
        "scope": scope,
        "workload": people,
        "workload_statuses": open_statuses,
        "blockers": {
            "blocked": blocked,
            "blocked_items": len(blocked),
            "blocked_sp": sum(item["sp"] or 0 for item in blocked),
            "high_priority": high_priority,
            "priority_checked": args.blocker_priority,
            "priorities_seen": priorities_seen,
        },
        "at_risk": {
            "stale": stale,
            "stale_items": len(stale),
            "stale_days": args.stale_days,
            "missing_sp": missing_sp,
            "missing_sp_items": len(missing_sp),
            "unassigned": unassigned,
            "unassigned_items": len(unassigned),
            "unassigned_sp": sum(item["sp"] or 0 for item in unassigned),
        },
        "carry_over": risk,
        "baseline": baseline,
        "capacity": projection,
        "changelog_signal": signals,
        "notes": {
            "progress_basis": "percent_by_sp is closed story points over total story points",
            "movement_basis": (
                "days_without_movement is the most recent of the exact last status change "
                "(from the changelog), the last human comment and the assignment to the "
                "current owner; the `updated` field is ignored because bulk edits inflate it"
            ),
            "baseline_basis": (
                "committed_sp counts the story points currently in the previous sprint, "
                "not the scope committed on day one; Jira does not keep that history"
            ),
        },
    }


def bar(percent: float, width: int = 14) -> str:
    """Fixed-width progress bar; the whole point is that the width never moves."""
    filled = min(width, int(round(max(0.0, percent) / 100 * width)))
    if filled >= width:
        return "[" + "=" * width + "]"
    return "[" + "=" * filled + ">" + " " * (width - filled - 1) + "]"


def render_text(data: dict) -> str:
    sprint = data["sprint"]
    totals = data["totals"]
    base_url = data.get("jira_base_url")
    style = data.get("link_style", "markdown")

    def ref(key: str) -> str:
        return ticket_ref(key, base_url, style)

    lines: list[str] = []

    lines.append(f"Sprint: {sprint['name']}")
    lines.append(f"Goal: {sprint.get('goal') or 'not set'}")
    duration = f"{sprint.get('start') or '?'} - {sprint.get('end') or '?'}"
    if sprint.get("days_total") is not None:
        duration += f" ({sprint['days_total']} days)"
    lines.append(f"Duration: {duration}")
    if sprint.get("overdue"):
        lines.append("Days Remaining: 0 - sprint end date has passed")
    elif sprint.get("days_remaining") is not None:
        lines.append(f"Days Remaining: {sprint['days_remaining']} days")

    baseline = data.get("baseline")
    if baseline:
        lines.append(
            f"Previous sprint baseline: {baseline['committed_sp']:g} SP committed / "
            f"{baseline['delivered_sp']:g} SP delivered ({baseline['percent']:g}%) "
            f"across {baseline['items']} items ({baseline['sprint']})"
        )
    else:
        lines.append("Previous sprint baseline: unavailable")
    scope = data.get("scope") or {}
    if scope.get("baseline_delivered_sp"):
        lines.append(
            f"Scope: {scope['committed_sp']:g} SP committed vs "
            f"{scope['baseline_delivered_sp']:g} SP delivered in the previous sprint "
            f"({scope['delta_percent']:+g}%)"
        )
    if data.get("jira_base_url"):
        lines.append(f"Jira: {data['jira_base_url']}")

    lines.append("")
    lines.append("Progress by status:")
    lines.append("| Status | Category | Count | Story Points |")
    lines.append("|--------|----------|-------|--------------|")
    for bucket in totals["by_status"]:
        lines.append(
            f"| {bucket['status']} | {bucket['category']} | {bucket['items']} | {bucket['sp']:g} |"
        )
    lines.append(
        f"| **Total** |  | **{totals['items']}** | **{totals['sp']:g}** |"
    )
    lines.append(
        f"Progress: {bar(totals['percent_by_sp'])} {totals['percent_by_sp']:g}% by SP "
        f"({totals['done']['sp']:g} of {totals['sp']:g}) | "
        f"{totals['percent_by_items']:g}% by count "
        f"({totals['done']['items']} of {totals['items']})"
    )

    lines.append("")
    lines.append("Risk assessment:")

    blockers = data["blockers"]
    if blockers["blocked"]:
        lines.append(
            f"Blocked by open work ({blockers['blocked_items']} items / "
            f"{blockers['blocked_sp']:g} SP):"
        )
        for item in blockers["blocked"][:10]:
            detail = ", ".join(
                f"{d['key']} ({d['status']})" for d in item["blocker_detail"]
                if d["category"] != "Done"
            )
            owner = item["owner"] or "UNASSIGNED"
            lines.append(
                f"- {ref(item['key'])}: {item['summary']} - {owner} - {item['status']} - "
                f"blocked by {detail}"
            )
        if blockers["blocked_items"] > 10:
            lines.append(f"+{blockers['blocked_items'] - 10} more blocked items")
    else:
        lines.append("Blocked by open work: none")

    if blockers["high_priority"]:
        lines.append(
            f"Highest-priority open items ({blockers['priority_checked']}): "
            f"{len(blockers['high_priority'])}"
        )
        for item in blockers["high_priority"][:5]:
            owner = item["owner"] or "UNASSIGNED"
            lines.append(
                f"- {ref(item['key'])}: {item['summary']} - {owner} - {item['status']} "
                f"({item['days_without_movement']}d without movement)"
            )
    else:
        seen = ", ".join(blockers["priorities_seen"]) or "none recorded"
        lines.append(
            f"Highest-priority open items ({blockers['priority_checked']}): none "
            f"- priorities present in this sprint: {seen}"
        )

    at_risk = data["at_risk"]
    lines.append(
        f"Stale in progress/review (>= {at_risk['stale_days']}d without movement): "
        f"{at_risk['stale_items']}"
    )
    for item in at_risk["stale"][:5]:
        owner = item["owner"] or "UNASSIGNED"
        lines.append(
            f"- {ref(item['key'])}: {item['summary']} - {owner} - {item['status']} "
            f"({item['days_without_movement']}d)"
        )
    if at_risk["stale_items"] > 5:
        lines.append(f"+{at_risk['stale_items'] - 5} more stale items")
    lines.append(f"Unestimated open items: {at_risk['missing_sp_items']}")
    lines.append(
        f"Unassigned open items: {at_risk['unassigned_items']} / "
        f"{at_risk['unassigned_sp']:g} SP"
    )

    lines.append("")
    carry = data["carry_over"]
    reasons = carry["by_reason"]
    lines.append(
        f"Needs a decision: {carry['items']} items / {carry['sp']:g} SP "
        f"({reasons['unassigned']} unassigned, {reasons['stale']} stale, "
        f"{reasons['unestimated']} unestimated; a ticket can be listed twice)"
    )

    projection = data["capacity"]
    if projection.get("available"):
        if projection["over_capacity_sp"]:
            verdict = f"{projection['over_capacity_sp']:g} SP over capacity"
        else:
            verdict = (
                f"{projection['headroom_sp']:g} SP of headroom - the committed scope "
                "is below the previous sprint's pace"
            )
        lines.append(
            f"Capacity: {projection['remaining_sp']:g} SP remaining; at the previous "
            f"sprint's pace the team delivers {projection['expected_sp']:g} SP in the "
            f"{projection['days_remaining']} days left ({verdict})"
        )
    else:
        lines.append(f"Capacity: not projected ({projection.get('reason')})")

    lines.append("")
    lines.append("Team workload (open items):")
    statuses = data.get("workload_statuses") or []
    headers = ["Team Member"] + statuses + ["Open SP"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("-" * (len(header) + 2) for header in headers) + "|")
    for person in data["workload"]:
        cells = " | ".join(str(person["by_status"].get(status, 0)) for status in statuses)
        lines.append(f"| {person['owner']} | {cells} | {person['sp']:g} |")

    lines.append("")
    lines.append("Method:")
    lines.append(f"- {data['notes']['movement_basis']}")
    lines.append(f"- {data['notes']['progress_basis']}")
    lines.append(f"- {data['notes']['baseline_basis']}")
    signal = data.get("changelog_signal") or {}
    if signal.get("failed"):
        lines.append(
            f"- signal: partial - {signal['failed']} of {signal['checked']} changelog "
            "reads failed, so those items use the status category date"
        )
    elif signal.get("available") is False:
        lines.append(
            "- signal: partial - no JIRA_API_TOKEN, so movement ignores exact status "
            "changes and assignments"
        )
    return "\n".join(lines)


PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")


def project_key(value: str) -> str:
    """A project key lands in JQL unquoted, so reject anything that is not one."""
    if not PROJECT_KEY.match(value):
        raise argparse.ArgumentTypeError(f"not a Jira project key: {value!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect the sprint status data.")
    parser.add_argument("--project", default="HYPERFLEET", type=project_key)
    parser.add_argument("--jira", default="jira", help="jira-cli binary")
    parser.add_argument("--sprint", help="sprint id; defaults to the active sprint")
    parser.add_argument("--sp-field", default="customfield_10028", help="custom field id holding story points")
    parser.add_argument("--blocker-priority", default="Major", help="priority name that counts as top priority")
    parser.add_argument("--stale-days", type=int, default=5, help="days without movement that count as stale")
    parser.add_argument("--today", help="YYYY-MM-DD, for reproducible runs")
    parser.add_argument("--no-baseline", action="store_true", help="skip the previous sprint lookup")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument(
        "--link-style",
        choices=["markdown", "slack", "bare"],
        default="markdown",
        help="how ticket keys are rendered in lists",
    )
    parser.add_argument("--format", choices=["json", "text", "markdown"], default="json")
    args = parser.parse_args()

    try:
        data = build(args)
    except SprintError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        render_text(data)
        if args.format in ("text", "markdown")
        else json.dumps(data, indent=2, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
