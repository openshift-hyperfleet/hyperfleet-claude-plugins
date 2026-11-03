#!/usr/bin/env python3
"""Shared jira-cli and Jira REST layer for the sprint commands.

`/sprint-status` and `/sprint-pulse-check` read the same objects: sprints, issues,
story points, links, comments and the changelog. Keeping two copies of that code
is how the two commands drifted apart in review - one filtered `status != Closed`
while the other used the status category, and the two disagree as soon as a
project names its done status something else (HYPERFLEET has no `Closed`).

So the Jira plumbing lives here once. A script imports what it needs, and a rule
such as "work is Done by category, never by status name" has exactly one
definition. `JiraError` is also shared: each script aliases it to its own name so
existing call sites and tests keep reading naturally.

Read-only. Nothing here writes to Jira.
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
from datetime import date, datetime
from pathlib import Path


class JiraError(Exception):
    """A jira-cli invocation or a Jira read failed."""


class ChangelogUnavailable(Exception):
    """A changelog read failed; it must not be read as "no entry"."""


# Jira groups statuses into three categories; the category is the stable answer,
# the status name is project-specific. HYPERFLEET has no `Done` or `Closed`
# status, so every "is this finished?" check must read the category.
DONE_CATEGORY = "Done"
CATEGORY_ORDER = {"To Do": 0, "In Progress": 1, DONE_CATEGORY: 2}

# This is the one JQL fragment for "still open". `status != Closed` matches
# nothing in HYPERFLEET and would silently include finished work.
OPEN_STATUS_JQL = f"statusCategory != {DONE_CATEGORY}"

# A move between these statuses is classification, not work. HYPERFLEET creates
# issues in `New`; a bulk New -> Backlog sweep must not reset the movement clock.
TRIVIAL_STATUSES = {"New", "Backlog"}


def status_category(doc: dict) -> str:
    """The status category of an issue document: To Do, In Progress or Done."""
    status = doc["fields"].get("status") or {}
    return ((status.get("statusCategory") or {}).get("name") or "").strip()


def status_name(doc: dict) -> str:
    return ((doc["fields"].get("status") or {}).get("name") or "").strip()


def is_done_doc(doc: dict) -> bool:
    return status_category(doc) == DONE_CATEGORY


def open_links(keys: list[str], category_of: dict[str, str]) -> list[str]:
    """Link targets that are still open work.

    A target with no known category counts as open: an unread link is not
    evidence that the blocker is gone.
    """
    return [key for key in keys if category_of.get(key) != DONE_CATEGORY]


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
        raise JiraError(f"jira {' '.join(args[:2])} could not run: {exc}") from exc
    if proc.returncode != 0:
        raise JiraError(
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

    An incomplete result raises instead of looking like a complete one.
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

    raise JiraError(
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
        raise JiraError(f"no active sprint found for project {project}")
    if len(rows) > 1:
        print(f"warning: {len(rows)} active sprints; using {rows[0]['name']}", file=sys.stderr)
    return rows[0]


def fetch_issue(key: str, project: str, binary: str) -> dict:
    try:
        return json.loads(
            run_jira(["issue", "view", key, "-p", project, "--raw"], binary)
        )
    except (JiraError, json.JSONDecodeError) as exc:
        raise JiraError(f"could not read {key}: {exc}") from exc


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


def describe(key: str, doc: dict, sp_field: str, today: date) -> dict:
    """The fields both reports need, read once.

    `status_changed` is the category change date, which is a fallback clock: it
    only moves between To Do / In Progress / Done. It is also the close date of a
    Done item, so the baseline uses it to tell work finished inside the previous
    sprint from work finished later while the sprint sat in the backlog.

    `sp` stays None when the field is empty: "no estimate" and "zero points" are
    different facts, and only the caller knows which one it can treat as zero.
    """
    fields = doc["fields"]
    status = fields.get("status") or {}
    category = ((status.get("statusCategory") or {}).get("name") or "").strip()
    status_changed = parse_date(fields["statuscategorychangedate"])
    comments = human_comment_dates(doc)
    last_comment = max(comments) if comments else None
    days_in_status = (today - status_changed).days
    days_since_comment = (today - last_comment).days if last_comment else None
    signals = [days_in_status]
    if days_since_comment is not None:
        signals.append(days_since_comment)
    blocked_by, blocks = link_targets(doc)
    points = fields.get(sp_field)

    return {
        "key": key,
        "summary": (fields.get("summary") or "").strip(),
        "type": (fields.get("issuetype") or {}).get("name", ""),
        "sp": points if isinstance(points, (int, float)) else None,
        "owner": ((fields.get("assignee") or {}).get("displayName") or "").strip(),
        "assignee_id": (fields.get("assignee") or {}).get("accountId") or None,
        "status": (status.get("name") or "").strip(),
        "category": category,
        "priority": (fields.get("priority") or {}).get("name", ""),
        "epic": (fields.get("parent") or {}).get("key"),
        "labels": fields.get("labels") or [],
        "created": (fields.get("created") or "")[:10],
        "status_changed": status_changed.isoformat(),
        "days_in_status": days_in_status,
        "days_since_comment": days_since_comment,
        "days_without_movement": min(signals),
        "last_comment": last_comment.isoformat() if last_comment else None,
        "blocked_by": blocked_by,
        "blocks": blocks,
        "is_done": category == DONE_CATEGORY,
    }


# --------------------------------------------------------------------------
# Linking and rendering
# --------------------------------------------------------------------------


def jira_base_url() -> str | None:
    """Read the server from the jira-cli config, so no report hardcodes it.

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


# --------------------------------------------------------------------------
# Changelog (Jira REST, the only place exact transitions live)
# --------------------------------------------------------------------------


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
    signal, inflating the stale list and the "needs a decision" count.
    """
    try:
        return changelog_dates(key, account_id, api), None
    except ChangelogUnavailable as exc:
        return (None, None), str(exc)


PR_URL = re.compile(r"/pull/(\d+)")


def pull_requests_from(payload: list, key: str) -> list[dict]:
    """The pull requests `key` owns, newest first.

    Two filters, because the panel is generous:

    - The URL must be a pull request. Jira stores a branch and a commit as remote
      links too, in the same shape, so only `/pull/<n>` counts.
    - The title decides ownership. Jira links a pull request to every ticket its
      title mentions, so a link on HYPERFLEET-1669 can be the pull request of
      HYPERFLEET-1636 - and then it is 1636's and never 1669's. A title that names
      another ticket, or names none at all, leaves this ticket with no pull
      request; printing it here would send the reviewer to someone else's diff and
      make two stalls look like one shared blocker.

    Duplicates are common (a PR appears once per branch event), so the number
    dedupes them. Order is newest first: within one repository the number grows,
    so the highest one is the latest attempt.
    """
    wanted = re.compile(rf"{re.escape(key)}(?!\d)", re.IGNORECASE)
    owned: dict[int, str] = {}
    for link in payload or []:
        if not isinstance(link, dict):
            continue
        obj = link.get("object") or {}
        url = (obj.get("url") or "").strip()
        match = PR_URL.search(url)
        if not match or not url.startswith("https://"):
            continue
        if wanted.search(obj.get("title") or ""):
            owned.setdefault(int(match.group(1)), url)
    return [{"number": number, "url": owned[number]} for number in sorted(owned, reverse=True)]



def read_pull_requests(key: str, api: tuple[str, str] | None) -> tuple[list[dict], str | None]:
    """(pull requests of `key`, error).

    The panel shows the link, not the state: an open and a merged pull request
    look the same here, so this says "there is something to review", never "it is
    still under review". Ownership comes from the title - a link the title
    attributes to another ticket is not returned, see `pull_requests_from`.
    """
    if not api:
        return [], "no JIRA_API_TOKEN or jira-cli login"
    server, auth = api
    request = urllib.request.Request(
        f"{server}/rest/api/3/issue/{key}/remotelink",
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
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
        return [], f"{key}: {type(exc).__name__}"
    return pull_requests_from(payload, key), None


def apply_pull_requests(items: list[dict], jobs: int) -> dict:
    """Attach `pr` to the items in review; other items get an empty list.

    `pr` is ownership - the title names the ticket. An item in Review with an empty
    list carries no pull request of its own, whatever Jira links on the panel.
    """
    for item in items:
        item["pr"] = []

    in_review = [item for item in items if item.get("status") == "Review"]
    if not in_review:
        return {"available": True, "failed": 0, "checked": 0, "found": 0}

    api = jira_api()
    if not api:
        return {
            "available": False,
            "failed": 0,
            "checked": len(in_review),
            "found": 0,
            "reason": "no JIRA_API_TOKEN or jira-cli login",
        }

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda item: read_pull_requests(item["key"], api), in_review))

    failed = found = 0
    for item, (prs, error) in zip(in_review, results):
        if error:
            failed += 1
        if prs:
            found += 1
            item["pr"] = prs

    return {
        "available": failed == 0,
        "failed": failed,
        "checked": len(in_review),
        "found": found,
    }


def pr_ref(pr: dict, style: str) -> str:
    """A pull request rendered for the destination, like `ticket_ref`."""
    number, url = pr["number"], pr["url"]
    if style == "bare":
        return f"#{number} ({url})"
    if style == "slack":
        return f"<{url}|#{number}>"
    return f"[#{number}]({url})"


def pr_refs(item: dict, style: str, limit: int = 2) -> str:
    """`PR #1, #2 +1` for an item, or "" when Jira links no pull request."""
    prs = item.get("pr") or []
    if not prs:
        return ""
    shown = ", ".join(pr_ref(pr, style) for pr in prs[:limit])
    more = f" +{len(prs) - limit}" if len(prs) > limit else ""
    return f"PR {shown}{more}"


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


PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")


def project_key(value: str) -> str:
    """A project key lands in JQL unquoted, so reject anything that is not one."""
    if not PROJECT_KEY.match(value):
        raise argparse.ArgumentTypeError(f"not a Jira project key: {value!r}")
    return value
