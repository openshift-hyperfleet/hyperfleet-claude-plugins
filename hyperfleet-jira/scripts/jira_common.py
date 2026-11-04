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
import urllib.parse
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


def fetch_all(
    keys: list[str],
    project: str,
    binary: str,
    jobs: int,
    failures: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Read every key, keeping the ones that answer.

    A key the caller cannot see - a link target outside their permission, a
    deleted issue, a repository the token lost access to - must not abort a report
    about the rest. The failed keys go to `failures` when the caller passes a dict,
    so the report can say it is partial; a caller that passes none gets a warning
    on stderr instead of a traceback.

    Callers must read a missing key as unknown, never as closed: `open_links`
    already counts an unread link as open, which keeps a blocker visible with a
    status of `?` instead of silently clearing it.
    """
    unique = sorted(set(keys), key=key_number)

    def fetch(key: str) -> dict | None:
        try:
            return fetch_issue(key, project, binary)
        except JiraError as exc:
            if failures is not None:
                failures[key] = str(exc)
            else:
                print(f"warning: {exc}", file=sys.stderr)
            return None

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        docs = list(pool.map(fetch, unique))
    return {doc["key"]: doc for doc in docs if doc is not None}


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
        # Jira's numeric id, which the development panel is keyed by.
        "issue_id": str(doc.get("id") or "") or None,
        "summary": (fields.get("summary") or "").strip(),
        "sp": points if isinstance(points, (int, float)) else None,
        "owner": ((fields.get("assignee") or {}).get("displayName") or "").strip(),
        "assignee_id": (fields.get("assignee") or {}).get("accountId") or None,
        "status": (status.get("name") or "").strip(),
        "category": category,
        "priority": (fields.get("priority") or {}).get("name", ""),
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


def key_in_title(key: str, title: str) -> bool:
    """Whether `title` names `key`, and not a longer key that starts with it."""
    return bool(re.search(rf"{re.escape(key)}(?!\d)", title or "", re.IGNORECASE))


def pull_requests_from(payload: list, key: str) -> list[dict]:
    """The pull requests `key` owns, from a remote-link payload.

    Two filters, because the payload is generous:

    - The URL must be a pull request. Jira stores a branch and a commit as remote
      links too, in the same shape, so only `/pull/<n>` counts.
    - The title decides ownership. Jira links a pull request to every ticket its
      title mentions, so a link on HYPERFLEET-1669 can be the pull request of
      HYPERFLEET-1636 - and then it is 1636's and never 1669's. A title that names
      another ticket, or names none at all, leaves this ticket with no pull
      request; printing it here would send the reviewer to someone else's diff and
      make two stalls look like one shared blocker.

    Remote links are the smaller half of the panel: the GitHub app reports through
    `dev-status`, which `development_pull_requests` reads. Both are merged, because
    some links exist only here.

    A pull request is identified by its URL, because numbers restart in every
    repository: `hyperfleet-api#120` and `hyperfleet-infra#120` can both belong to
    one ticket, and keeping only one of them would hide the other's reviewers.
    """
    owned: dict[str, int] = {}
    for link in payload or []:
        if not isinstance(link, dict):
            continue
        obj = link.get("object") or {}
        url = (obj.get("url") or "").strip()
        match = PR_URL.search(url)
        if not match or not url.startswith("https://"):
            continue
        if key_in_title(key, obj.get("title") or ""):
            # Keyed by URL, not by number: numbers restart in every repository,
            # so `hyperfleet-api#120` and `hyperfleet-infra#120` are two pull
            # requests and keeping one of them would hide the other's reviewers.
            owned.setdefault(url, int(match.group(1)))
    return [
        {"number": number, "url": url}
        for url, number in sorted(owned.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


def application_types(summary) -> list[str] | None:
    """The application ids the `dev-status` summary lists, or None when malformed.

    Each level is checked on its own: a response can be valid JSON and still be a
    list, a string or an object nested the wrong way, and `summary["summary"]` is
    not an object just because the body was.

    A branch that is simply absent means "no application reported a pull request",
    which is an empty list: Jira answers `{"summary": {}}` for an issue no app has
    touched, and calling that malformed would turn a knowable "no pull request"
    into an unknown one.
    """
    node = summary
    for part in ("summary", "pullrequest", "byInstanceType"):
        if node is None:
            return []
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    if node is None:
        return []
    if not isinstance(node, dict):
        return None
    return list(node)


def development_pull_requests(issue_id: str, api: tuple[str, str]) -> tuple[list[dict], str | None]:
    """(pull requests the development panel reports, error).

    The panel is served by `dev-status`, not by remote links: the GitHub app posts
    its own records there, and they are the ones carrying every repository. On
    Sprint 19 the remote links held nothing from `hyperfleet-api`, so ten API items
    looked like they had no pull request while theirs were open.

    `applicationType` is not a constant - it is the instance id the app reports
    (`oAuth-com.github.integration.production` here, `GitHub` elsewhere) - so the
    summary call supplies it instead of a guess. The same records carry `status`,
    which is the one thing remote links never have.
    """
    server, auth = api
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}

    def get(url: str):
        request = urllib.request.Request(url, headers=headers)
        with open_changelog(request) as response:
            return json.load(response)

    failures = (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        ValueError,
    )

    try:
        summary = get(f"{server}/rest/dev-status/1.0/issue/summary?issueId={issue_id}")
    except failures as exc:
        # The summary is the only source of application ids, so this failure really
        # does mean nothing was read.
        return [], type(exc).__name__

    types = application_types(summary)
    if types is None:
        # A malformed summary is a failed summary read: without the ids there is
        # nothing to ask for, and the caller reports a partial read.
        return [], "MalformedResponse"
    found: list[dict] = []
    error: str | None = None
    for app in types:
        try:
            detail = get(
                f"{server}/rest/dev-status/latest/issue/detail?issueId={issue_id}"
                f"&applicationType={urllib.parse.quote(app)}&dataType=pullrequest"
            )
        except failures as exc:
            # One application failing must not discard what the others reported,
            # and the caller still needs to know the list is partial.
            error = error or type(exc).__name__
            continue
        if not isinstance(detail, dict):
            # Valid JSON, wrong shape: a list or a string where the panel's object
            # belongs. That is a failed application read like any other, and
            # calling `.get` on it would abort the whole collector.
            error = error or "MalformedResponse"
            continue
        for group in detail.get("detail") or []:
            if not isinstance(group, dict):
                continue
            reported = group.get("pullRequests")
            if isinstance(reported, list):
                found.extend(pr for pr in reported if isinstance(pr, dict))

    prs = []
    for pr in found:
        url = (pr.get("url") or "").strip()
        match = PR_URL.search(url)
        if not match:
            continue
        prs.append(
            {
                "number": int(match.group(1)),
                "url": url,
                "title": pr.get("name") or "",
                "status": (pr.get("status") or "").upper() or None,
                "updated": pr.get("lastUpdate") or "",
                "reviewers": requested_reviewers(pr),
            }
        )
    return prs, error


def requested_reviewers(pr: dict) -> list[str]:
    """The people a pull request is waiting on, in the order Jira lists them.

    Three entries never belong in an ask:

    - the author, because nobody approves their own diff
    - `approved: true`, because that reviewer already decided
    - Jira's `User ` placeholder, which is what the panel shows for a GitHub
      account it can no longer resolve. On Sprint 19 most reviewers were this
      placeholder, so keeping it would fill the ask with a name nobody answers to.
    """
    author = ((pr.get("author") or {}).get("name") or "").strip()
    names: list[str] = []
    for reviewer in pr.get("reviewers") or []:
        name = ((reviewer or {}).get("name") or "").strip()
        if not name or name == "User" or name == author:
            continue
        if reviewer.get("approved"):
            continue
        if name not in names:
            names.append(name)
    return names


def read_pull_requests(
    key: str, issue_id: str | None, api: tuple[str, str] | None
) -> tuple[list[dict], str | None]:
    """(pull requests of `key`, error).

    The panel shows two kinds of record, and a ticket can have both: the GitHub app
    posts through `dev-status` (every repository, with a state), and a link the
    team attached by hand lives in `remotelink` (no state). Reading only the second
    is what hid every `hyperfleet-api` pull request on Sprint 19.

    Ownership comes from the title on both sides - see `pull_requests_from` - so a
    link titled for another ticket contributes a state to that ticket, not a pull
    request to this one. The state is why the two are merged instead of one being
    dropped: it says whether the diff a reviewer opens is still open.

    A failure in one source is returned with whatever the other source found. The
    error means "partial", not "empty": dropping the panel's list because the
    remote links failed - or the reverse - would hide pull requests Jira does report.
    """
    if not api:
        return [], "no JIRA_API_TOKEN or jira-cli login"
    server, auth = api
    request = urllib.request.Request(
        f"{server}/rest/api/3/issue/{key}/remotelink",
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
    )
    remote_error: str | None = None
    try:
        with open_changelog(request) as response:
            payload = json.load(response)
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        ValueError,
    ) as exc:
        # Keep going: the panel may still answer, and half the list is better
        # than none as long as the signal says the read was partial.
        payload = []
        remote_error = f"{key}: {type(exc).__name__}"

    owned = pull_requests_from(payload, key)
    states: dict[str, dict] = {}
    panel_error: str | None = None
    if issue_id:
        panel, error = development_pull_requests(issue_id, api)
        if error:
            # Same rule in the other direction: a panel failure must not drop the
            # remote-link pull requests already read. `panel` keeps whatever the
            # application types that did answer reported.
            panel_error = f"{key}: {error}"
        for pr in panel:
            if key_in_title(key, pr["title"]):
                owned.append({"number": pr["number"], "url": pr["url"]})
                states[pr["url"]] = pr

    unique: dict[str, dict] = {}
    for pr in owned:
        record = {"number": pr["number"], "url": pr["url"]}
        state = states.get(pr["url"])
        if state:
            record["status"] = state["status"]
            record["updated"] = state["updated"]
            record["reviewers"] = state["reviewers"]
        unique.setdefault(pr["url"], record)

    # Numbers restart in every repository, so they only break ties: a pull request
    # is newest by its own last update when Jira reports one.
    ordered = sorted(
        unique.values(),
        key=lambda pr: (pr.get("updated") or "", pr["number"]),
        reverse=True,
    )
    return ordered, remote_error or panel_error


def apply_pull_requests(items: list[dict], jobs: int) -> dict:
    """Attach `pr` to the items in review; other items get an empty list.

    `pr` is ownership - the title names the ticket. An item in Review with an empty
    list carries no pull request Jira knows about, which is not the same as no pull
    request: a repository without the GitHub app reports nothing here.

    `pr_unknown` marks the second case: the lookup for that item did not answer, so
    an empty `pr` says "unread", not "none". A partial read can do both - one source
    answered and the item keeps what it found while the flag records the failure -
    which is why the flag is per item and not only on the returned signal.

    The caller passes what it needs, not only the queue: a blocker in Review is
    someone else's pull request, and the ask that names its reviewers needs the
    same read. Extra descriptors are cheap - the lookup only touches Review items.
    """
    for item in items:
        item["pr"] = []
        item["pr_unknown"] = False

    in_review = [item for item in items if item.get("status") == "Review"]
    if not in_review:
        return {"available": True, "failed": 0, "checked": 0, "found": 0}

    api = jira_api()
    if not api:
        for item in in_review:
            item["pr_unknown"] = True
        return {
            "available": False,
            "failed": 0,
            "checked": len(in_review),
            "found": 0,
            "reason": "no JIRA_API_TOKEN or jira-cli login",
        }

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(
            pool.map(
                lambda item: read_pull_requests(item["key"], item.get("issue_id"), api),
                in_review,
            )
        )

    failed = found = 0
    for item, (prs, error) in zip(in_review, results):
        if error:
            failed += 1
            item["pr_unknown"] = True
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
    """A pull request rendered for the destination, like `ticket_ref`.

    The state rides along when Jira reports one, because it changes what the reader
    does next: `PR #181 (merged)` is a ticket waiting for its status, `PR #177` is
    one waiting for a reviewer. Remote links carry no state, so the suffix is
    absent there - not "open", just unknown.
    """
    number, url = pr["number"], pr["url"]
    if style == "bare":
        ref = f"#{number} ({url})"
    elif style == "slack":
        ref = f"<{url}|#{number}>"
    else:
        ref = f"[#{number}]({url})"
    state = (pr.get("status") or "").lower()
    return f"{ref} ({state})" if state and state != "open" else ref


def pr_refs(item: dict, style: str) -> str:
    """`PR #1, #2 +1` for an item, or "" when Jira reports no pull request.

    The two shown are a line-width cap, not a choice: every pull request in the
    list belongs to the ticket by its own title, and the count after `+` says how
    many are not shown. Nothing is dropped from ownership, only from the line.
    """
    prs = item.get("pr") or []
    if not prs:
        return ""
    shown = ", ".join(pr_ref(pr, style) for pr in prs[:2])
    more = f" +{len(prs) - 2}" if len(prs) > 2 else ""
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


def iso_date(value: str) -> str:
    """Validate a CLI date without changing it: `build` re-parses it with `parse_date`."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from exc
    return value


def positive_int(value: str) -> int:
    """A thread count of zero is a crash inside the pool, not a valid argument."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not an integer: {value!r}") from exc
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1: {value!r}")
    return number


# --------------------------------------------------------------------------
# CLI surface and signals shared by both collectors
# --------------------------------------------------------------------------


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """The flags both collectors accept, written once.

    Two `--help` texts that drift are two contracts: the reviewer reads one and
    the lead runs the other. The flags that mean the same thing in both scripts
    live here; the ones that only one command has stay in its `main`.
    """
    parser.add_argument("--project", default="HYPERFLEET", type=project_key)
    parser.add_argument("--jira", default="jira", help="jira-cli binary")
    parser.add_argument(
        "--sp-field", default="customfield_10028", help="custom field id holding story points"
    )
    parser.add_argument("--today", type=iso_date, help="YYYY-MM-DD, for reproducible runs")
    parser.add_argument(
        "--no-prs",
        action="store_true",
        help="skip the pull request lookup for items in review",
    )
    parser.add_argument("--jobs", type=positive_int, default=8)


def no_prs_signal() -> dict:
    """The `pr_signal` of a run that skipped the lookup.

    `skipped` is what keeps the renderer from blaming a missing token for a call
    the caller turned off.
    """
    return {"available": True, "failed": 0, "checked": 0, "found": 0, "skipped": True}


def warn_changelog_failure(signal: dict) -> None:
    """Say once, on stderr, that some movement clocks fell back."""
    if not signal.get("failed"):
        return
    print(
        f"warning: {signal['failed']} of {signal['checked']} changelog reads "
        "failed; those items fall back to the status category date",
        file=sys.stderr,
    )
