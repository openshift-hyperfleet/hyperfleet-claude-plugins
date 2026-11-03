"""Tests for the pulse check collector.

Run from the plugin directory:

    python3 -m unittest discover -s tests -v

The cases that matter are the ones where a plausible-looking implementation
produces a wrong answer: link orientation (a "blocks" link is not a blocker)
and the human-comment rule (an app comment is not movement).
"""

import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import jira_common as jc  # noqa: E402
import pulse_check as pc  # noqa: E402

TODAY = date(2026, 11, 3)


def doc(
    key="HYPERFLEET-100",
    *,
    sp=5,
    owner="A Person",
    status="Backlog",
    changed="2026-10-04",
    comments=(),
    links=(),
    summary="A large item",
):
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "issuetype": {"name": "Story"},
            "customfield_10028": sp,
            "assignee": {"displayName": owner} if owner else None,
            "status": {"name": status},
            "priority": {"name": "Normal"},
            "parent": {"key": "HYPERFLEET-1"},
            "labels": [],
            "created": "2026-09-01T10:00:00.000+0000",
            "statuscategorychangedate": f"{changed}T10:00:00.000+0000",
            "comment": {"comments": list(comments)},
            "issuelinks": list(links),
        },
    }


def comment(created, author="A Person", account_type="atlassian"):
    return {"created": f"{created}T09:00:00.000+0000", "author": {"displayName": author, "accountType": account_type}}


def blocks_link(target):
    return {
        "type": {"inward": "is blocked by", "outward": "blocks"},
        "outwardIssue": {"key": target},
    }


def blocked_by_link(target):
    return {
        "type": {"inward": "is blocked by", "outward": "blocks"},
        "inwardIssue": {"key": target},
    }


class LinkOrientationTest(unittest.TestCase):
    def test_outward_link_is_not_a_blocker(self):
        blocked_by, blocks = jc.link_targets(doc(links=[blocks_link("HYPERFLEET-200")]))
        self.assertEqual(blocked_by, [])
        self.assertEqual(blocks, ["HYPERFLEET-200"])

    def test_inward_link_is_a_blocker(self):
        blocked_by, blocks = jc.link_targets(doc(links=[blocked_by_link("HYPERFLEET-200")]))
        self.assertEqual(blocked_by, ["HYPERFLEET-200"])
        self.assertEqual(blocks, [])

    def test_both_directions_in_one_issue(self):
        blocked_by, blocks = jc.link_targets(
            doc(links=[blocked_by_link("HYPERFLEET-200"), blocks_link("HYPERFLEET-201")])
        )
        self.assertEqual(blocked_by, ["HYPERFLEET-200"])
        self.assertEqual(blocks, ["HYPERFLEET-201"])


class MovementTest(unittest.TestCase):
    def test_app_comments_are_not_movement(self):
        dates = jc.human_comment_dates(
            doc(comments=[comment("2026-11-02", "Automation for Jira", "app")])
        )
        self.assertEqual(dates, [])

    def test_human_comment_is_movement(self):
        dates = jc.human_comment_dates(doc(comments=[comment("2026-11-02")]))
        self.assertEqual(dates, [date(2026, 11, 2)])

    def test_movement_uses_the_most_recent_signal(self):
        item = pc.describe(
            "HYPERFLEET-100",
            doc(changed="2026-08-25", comments=[comment("2026-10-21")]),
            "customfield_10028",
            TODAY,
        )
        self.assertEqual(item["days_in_status"], 70)
        self.assertEqual(item["days_since_comment"], 13)
        self.assertEqual(item["days_without_movement"], 13)

    def test_no_comments_falls_back_to_status_change(self):
        item = pc.describe(
            "HYPERFLEET-100", doc(changed="2026-10-14"), "customfield_10028", TODAY
        )
        self.assertEqual(item["days_without_movement"], 20)
        self.assertIsNone(item["last_comment"])


class ChangelogSignalTest(unittest.TestCase):
    api = ("https://example.atlassian.net", "auth")

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return io.StringIO(json.dumps(self.payload))

        def __exit__(self, *exc):
            return False

    def item(self, **overrides):
        base = {
            "key": "HYPERFLEET-1671",
            "owner": "Phuongnhat Nguyen",
            "assignee_id": "acc-1",
            "status": "Backlog",
            "created": "2026-09-17",
            "days_in_status": 47,
            "days_since_comment": 13,
            "days_without_movement": 13,
        }
        base.update(overrides)
        return base

    def apply(self, status_entered=None, assigned=None):
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(jc, "changelog_dates", return_value=(status_entered, assigned)):
            return pc.apply_changelog_signals([self.item], TODAY, 1)

    def test_status_change_inside_a_category_resets_the_clock(self):
        item = self.item(days_in_status=15, days_without_movement=15)
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates", return_value=(date(2026, 10, 30), None)
             ):
            report = pc.apply_changelog_signals([item], TODAY, 1)
        self.assertEqual(item["days_in_status"], 4)
        self.assertEqual(item["days_without_movement"], 4)
        self.assertEqual(item["status_entered"], "2026-10-30")
        self.assertEqual(
            report,
            {
                "available": True,
                "failed": 0,
                "checked": 1,
                "status_dates": 1,
                "assignments": 0,
            },
        )

    def test_assignment_resets_the_clock(self):
        item = self.item()
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates", return_value=(None, date(2026, 10, 30))
             ):
            report = pc.apply_changelog_signals([item], TODAY, 1)
        self.assertEqual(item["days_without_movement"], 4)
        self.assertEqual(item["assigned"], "2026-10-30")
        self.assertEqual(item["days_since_assignment"], 4)
        self.assertEqual(report["assignments"], 1)

    def test_signals_never_raise_the_clock(self):
        item = self.item(days_in_status=2, days_since_comment=None, days_without_movement=2)
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates", return_value=(date(2026, 1, 1), date(2026, 1, 1))
             ):
            pc.apply_changelog_signals([item], TODAY, 1)
        self.assertEqual(item["days_without_movement"], 2)

    def test_missing_token_keeps_the_old_clock(self):
        item = self.item()
        with mock.patch.object(jc, "jira_api", return_value=None):
            report = pc.apply_changelog_signals([item], TODAY, 1)
        self.assertFalse(report["available"])
        self.assertEqual(item["days_without_movement"], 13)
        self.assertIsNone(item["assigned"])
        self.assertIsNone(item["status_entered"])

    def histories(self):
        return {
            "changelog": {
                "histories": [
                    {"created": "2026-09-01T10:00:00+0000",
                     "items": [{"field": "status", "to": "10013",
                                "fromString": "New", "toString": "Backlog"}]},
                    {"created": "2026-10-30T19:12:32+0000",
                     "items": [{"field": "status", "to": "3",
                                "fromString": "Backlog", "toString": "In Progress"}]},
                    {"created": "2026-10-31T10:00:00+0000",
                     "items": [{"field": "assignee", "to": "acc-1"},
                               {"field": "status", "to": "10145",
                                "fromString": "In Progress", "toString": "Review"}]},
                    {"created": "2026-11-02T09:00:00+0000",
                     "items": [{"field": "status", "to": "10013",
                                "fromString": "New", "toString": "Backlog"}]},
                ]
            }
        }

    def test_changelog_returns_the_latest_status_and_assignment(self):
        with mock.patch.object(
            jc, "open_changelog", return_value=self.Response(self.histories())
        ):
            self.assertEqual(
                jc.changelog_dates("HYPERFLEET-1", "acc-1", self.api),
                (date(2026, 10, 31), date(2026, 10, 31)),
            )

    def test_new_to_backlog_is_classification_not_movement(self):
        payload = {
            "changelog": {
                "histories": [
                    {"created": "2026-11-02T09:00:00+0000",
                     "items": [{"field": "status", "fromString": "New", "toString": "Backlog"}]}
                ]
            }
        }
        with mock.patch.object(
            jc, "open_changelog", return_value=self.Response(payload)
        ):
            self.assertEqual(
                jc.changelog_dates("HYPERFLEET-1", "acc-1", self.api), (None, None)
            )

    def test_created_in_status_has_no_transition_date(self):
        payload = {"changelog": {"histories": []}}
        with mock.patch.object(
            jc, "open_changelog", return_value=self.Response(payload)
        ):
            self.assertEqual(
                jc.changelog_dates("HYPERFLEET-1", "acc-1", self.api), (None, None)
            )

    def test_binding_only_when_assignment_is_strictly_shortest(self):
        self.assertTrue(
            pc.assignment_is_binding(
                {"days_since_assignment": 4, "days_in_status": 47, "days_since_comment": 13}
            )
        )
        self.assertFalse(
            pc.assignment_is_binding(
                {"days_since_assignment": 13, "days_in_status": 47, "days_since_comment": 13}
            )
        )
        self.assertFalse(
            pc.assignment_is_binding({"days_since_assignment": None, "days_in_status": 47})
        )


class ChangelogFailureTest(unittest.TestCase):
    api = ("https://example.atlassian.net", "auth")

    def item(self):
        return {
            "key": "HYPERFLEET-1671",
            "owner": "Phuongnhat Nguyen",
            "assignee_id": "acc-1",
            "days_in_status": 47,
            "days_since_comment": 13,
            "days_without_movement": 13,
        }

    def test_a_failed_read_is_counted_not_hidden(self):
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates",
                 side_effect=pc.ChangelogUnavailable("HYPERFLEET-1671: HTTPError"),
             ):
            report = pc.apply_changelog_signals([self.item()], TODAY, 1)
        self.assertFalse(report["available"])
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["checked"], 1)

    def test_a_failed_read_leaves_the_clock_alone(self):
        item = self.item()
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates", side_effect=pc.ChangelogUnavailable("boom")
             ):
            pc.apply_changelog_signals([item], TODAY, 1)
        self.assertEqual(item["days_without_movement"], 13)
        self.assertIsNone(item["status_entered"])

    def test_an_http_error_raises_instead_of_looking_empty(self):
        with mock.patch.object(
            jc,
            "open_changelog",
            side_effect=jc.urllib.error.URLError("401 Unauthorized"),
        ):
            with self.assertRaises(pc.ChangelogUnavailable):
                jc.changelog_dates("HYPERFLEET-1", "acc-1", self.api)


class ChangelogTransportTest(unittest.TestCase):
    api = ("https://example.atlassian.net", "auth")

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return io.StringIO(json.dumps(self.payload))

        def __exit__(self, *exc):
            return False

    def call(self, payload=None, error=None):
        if error is not None:
            patcher = mock.patch.object(jc, "open_changelog", side_effect=error)
        else:
            patcher = mock.patch.object(
                jc, "open_changelog", return_value=self.Response(payload)
            )
        with patcher:
            return jc.changelog_dates("HYPERFLEET-1", "acc-1", self.api)

    def test_a_truncated_response_is_counted(self):
        with self.assertRaises(pc.ChangelogUnavailable):
            self.call(error=jc.http.client.IncompleteRead(b""))

    def test_a_non_utf8_body_is_counted(self):
        error = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        with self.assertRaises(pc.ChangelogUnavailable):
            self.call(error=error)

    def test_a_capped_changelog_is_counted(self):
        with self.assertRaises(pc.ChangelogUnavailable):
            self.call(payload={"changelog": {"total": 150, "histories": []}})

    def test_a_complete_changelog_is_read(self):
        payload = {
            "changelog": {
                "total": 1,
                "histories": [
                    {
                        "created": "2026-10-30T10:00:00.000+0000",
                        "items": [
                            {
                                "field": "status",
                                "fromString": "In Progress",
                                "toString": "Review",
                            }
                        ],
                    }
                ],
            }
        }
        self.assertEqual(self.call(payload=payload)[0], date(2026, 10, 30))

    def test_a_redirect_is_refused(self):
        handler = jc.NoRedirect()
        with self.assertRaises(jc.urllib.error.HTTPError) as caught:
            handler.redirect_request(
                jc.urllib.request.Request("https://a.example"),
                None,
                302,
                "Found",
                {},
                "https://b.example",
            )
        caught.exception.close()


class RunJiraTest(unittest.TestCase):
    def test_a_timeout_is_a_pulse_error(self):
        with mock.patch.object(
            jc.subprocess,
            "run",
            side_effect=jc.subprocess.TimeoutExpired("jira", 120),
        ):
            with self.assertRaises(pc.PulseError):
                pc.run_jira(["issue", "list"], "jira")

    def test_a_missing_binary_is_a_pulse_error(self):
        with mock.patch.object(
            jc.subprocess, "run", side_effect=FileNotFoundError("jira")
        ):
            with self.assertRaises(pc.PulseError):
                pc.run_jira(["issue", "list"], "jira")


class JiraApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        (Path(self.tmp.name) / ".config" / ".jira").mkdir(parents=True)
        self.config = Path(self.tmp.name) / ".config" / ".jira" / ".config.yml"

    def api(self, server):
        self.config.write_text(f"server: {server}\nlogin: someone@example.com\n")
        with mock.patch.object(jc.Path, "home", return_value=Path(self.tmp.name)), \
             mock.patch.dict(jc.os.environ, {"JIRA_API_TOKEN": "token"}):
            return jc.jira_api()

    def test_https_is_kept(self):
        self.assertEqual(
            self.api("https://x.atlassian.net")[0], "https://x.atlassian.net"
        )

    def test_a_bare_host_gets_https(self):
        self.assertEqual(
            self.api("x.atlassian.net")[0], "https://x.atlassian.net"
        )

    def test_cleartext_http_is_refused_so_the_token_never_leaves(self):
        self.assertIsNone(self.api("http://x.atlassian.net"))


class ProjectArgumentTest(unittest.TestCase):
    def test_a_project_key_is_accepted(self):
        self.assertEqual(pc.project_key("HYPERFLEET"), "HYPERFLEET")

    def test_jql_is_not_a_project_key(self):
        with self.assertRaises(jc.argparse.ArgumentTypeError):
            pc.project_key("HF OR project = SECRET")


class AskTest(unittest.TestCase):
    def ask(self, status, days, blockers=None, summary="A large item"):
        item = {
            "summary": summary,
            "status": status,
            "days_without_movement": days,
            "open_blockers": blockers or [],
            "blocker_detail": [
                {"key": k, "status": "Review", "owner": "Someone"} for k in (blockers or [])
            ],
        }
        return pc.suggested_ask(item)

    def test_the_blocker_in_the_ask_is_a_link(self):
        ask = pc.suggested_ask(
            {
                "summary": "A large item",
                "status": "Backlog",
                "days_without_movement": 3,
                "open_blockers": ["HYPERFLEET-1636"],
                "blocker_detail": [
                    {"key": "HYPERFLEET-1636", "status": "Review", "owner": "Martin Liptak"}
                ],
            },
            lambda key: pc.ticket_ref(key, "https://example.atlassian.net/browse/", "markdown"),
        )
        self.assertIn(
            "approve or reject [HYPERFLEET-1636]"
            "(https://example.atlassian.net/browse/HYPERFLEET-1636)",
            ask,
        )

    def test_blocked_item_names_the_blocker_and_the_move(self):
        ask = self.ask("Backlog", 70, ["HYPERFLEET-1636"])
        self.assertIn("HYPERFLEET-1636", ask)
        self.assertIn("approve or reject", ask)

    def test_the_ask_starts_with_a_verb(self):
        for status in ("Backlog", "Review", "In Progress"):
            for days in (6, 12, 25):
                first = self.ask(status, days).split()[0].lower()
                self.assertIn(
                    first,
                    {"ask", "assign", "post", "start", "propose", "confirm"},
                    f"{status}/{days}d started with {first}",
                )

    def test_an_unowned_blocker_asks_for_an_owner(self):
        item = {
            "summary": "x",
            "status": "Backlog",
            "days_without_movement": 70,
            "open_blockers": ["HYPERFLEET-1523"],
            "blocker_detail": [{"key": "HYPERFLEET-1523", "status": "Backlog", "owner": None}],
        }
        self.assertTrue(pc.suggested_ask(item).lower().startswith("assign"))

    def test_long_blocker_list_is_truncated(self):
        ask = self.ask("Backlog", 70, ["HYPERFLEET-1", "HYPERFLEET-2", "HYPERFLEET-3"])
        self.assertIn("+1 more", ask)

    def test_review_blocker_leads_and_carries_its_age(self):
        item = {
            "status": "Backlog",
            "days_without_movement": 70,
            "open_blockers": ["HYPERFLEET-1532", "HYPERFLEET-1636"],
            "blocker_detail": [
                {"key": "HYPERFLEET-1532", "status": "Backlog", "days_in_status": 66},
                {"key": "HYPERFLEET-1636", "status": "Review", "days_in_status": 7,
                 "owner": "Martin Liptak"},
            ],
        }
        ask = pc.suggested_ask(item)
        self.assertLess(ask.index("HYPERFLEET-1636"), ask.index("HYPERFLEET-1532"))
        self.assertIn("Martin", ask)
        self.assertIn("Review 7d", ask)

    def test_review_asks_a_reviewer_for_a_decision(self):
        self.assertIn("approve or reject", self.ask("Review", 15).lower())

    def test_twenty_days_backlog_is_start_or_drop(self):
        ask = self.ask("Backlog", 25).lower()
        self.assertIn("start", ask)
        self.assertIn("drop", ask)

    def test_twenty_days_spike_is_a_decision_note(self):
        ask = self.ask("Backlog", 43, summary="[SPIKE] ingress/TLS").lower()
        self.assertIn("decision note", ask)
        self.assertNotIn("start", ask)

    def test_twenty_days_in_progress_is_not_start_or_drop(self):
        ask = self.ask("In Progress", 20).lower()
        self.assertIn("re-scope", ask)
        self.assertNotIn("drop", ask)

    def test_ten_days_asks_for_a_date_not_a_meeting(self):
        self.assertIn("start date", self.ask("Backlog", 12).lower())
        self.assertNotIn("office hours", self.ask("Backlog", 12).lower())


class CrossReferenceAskTest(unittest.TestCase):
    """Jira links a pull request to every ticket its title names, and only the title decides."""

    def item(self, pr=()):
        return {
            "summary": "Read tenant dimensions from wristband claims",
            "status": "Review",
            "days_without_movement": 4,
            "open_blockers": [],
            "blocker_detail": [],
            "ask": "Ask a reviewer to approve or reject",
            "pr": list(pr),
        }

    def test_an_owned_pull_request_rides_in_the_ask(self):
        ask = pc.decorate_ask(
            self.item(pr=[{"number": 257, "url": "https://github.com/o/r/pull/257"}]), "markdown"
        )
        self.assertIn("approve or reject PR [#257]", ask)

    def test_another_tickets_pull_request_never_reaches_the_ask(self):
        ask = pc.decorate_ask(self.item(), "markdown")
        self.assertNotIn("#255", ask)
        self.assertNotIn("1636", ask)
        self.assertNotIn("approve or reject PR", ask)

    def test_a_review_item_with_no_pull_request_asks_for_the_missing_artifact(self):
        self.assertEqual(
            pc.decorate_ask(self.item(), "markdown"),
            "Post this ticket's pull request, or move it back to In Progress",
        )


class RenderTest(unittest.TestCase):
    def data(self):
        return {
            "generated_for": "2026-11-03",
            "jira_base_url": "https://example.atlassian.net/browse/",
            "link_style": "markdown",
            "sprint": {"name": "Sprint 19"},
            "totals": {"owned": {"items": 1, "sp": 5}},
            "queue": [
                {
                    "key": "HYPERFLEET-1",
                    "summary": "A large item",
                    "owner": "A Person",
                    "sp": 5,
                    "status": "Backlog",
                    "days_without_movement": 60,
                    "created": "2026-09-04",
                    "days_in_status": 60,
                    "days_since_comment": None,
                    "assigned": None,
                    "days_since_assignment": None,
                    "ask": "Set a start date or drop",
                }
            ],
            "queue_needing_action": 1,
            "queue_overflow": 0,
            "no_action": [],
            "escalation_20d": [],
            "escalation_excluded_blocked": [],
            "assignment_gap": {"items": 0, "sp": 0, "sizes": [], "blocking_other_work": []},
            "concentration": [],
            "definition": "movement = the most recent signal",
            "next_pulse": None,
        }

    def test_no_action_line_carries_the_assignment_date(self):
        data = self.data()
        data["no_action"] = [
            {"key": "HYPERFLEET-1671", "owner": "P", "days_without_movement": 4,
             "days_in_status": 47, "days_since_comment": 13,
             "days_since_assignment": 4, "assigned": "2026-10-30"}
        ]
        self.assertIn(
            "No action: [HYPERFLEET-1671](https://example.atlassian.net/browse/HYPERFLEET-1671)"
            " (4d, assigned 10-30)",
            pc.render_text(data),
        )

    def test_no_action_line_hides_an_assignment_that_is_not_the_binding_signal(self):
        data = self.data()
        data["no_action"] = [
            {"key": "HYPERFLEET-1751", "owner": "P", "days_without_movement": 1,
             "days_in_status": 30, "days_since_comment": 1,
             "days_since_assignment": 4, "assigned": "2026-10-30"}
        ]
        self.assertIn(
            "No action: [HYPERFLEET-1751](https://example.atlassian.net/browse/HYPERFLEET-1751) (1d)",
            pc.render_text(data),
        )
        self.assertNotIn("assigned 10-30", pc.render_text(data))

    def test_one_table_row_per_item_with_the_ask_last(self):
        text = pc.render_text(self.data())
        self.assertIn("| Ticket | Title | Owner | SP | Status · age | Ask |", text)
        self.assertIn(
            "| [HYPERFLEET-1](https://example.atlassian.net/browse/HYPERFLEET-1) "
            "| A large item | A | 5 | Backlog · 60d (since 09-04) "
            "| Set a start date or drop |",
            text,
        )
        self.assertNotIn("> [", text)

    def test_a_pipe_in_the_summary_does_not_break_the_row(self):
        data = self.data()
        data["queue"][0]["summary"] = "Add | remove on the remote transport"
        row = [line for line in pc.render_text(data).splitlines() if "HYPERFLEET-1)" in line][0]
        self.assertEqual(row.count("|") - row.count("\\|"), 7)

    def test_prose_keys_are_links(self):
        data = self.data()
        data["escalation_20d"] = ["HYPERFLEET-2"]
        data["assignment_gap"] = {
            "items": 1,
            "sp": 5,
            "sizes": [5],
            "blocking_other_work": [{"key": "HYPERFLEET-3", "sp": 5, "blocks_open": 7}],
        }
        text = pc.render_text(data)
        self.assertIn(
            "Escalation 20+ days: [HYPERFLEET-2](https://example.atlassian.net/browse/HYPERFLEET-2)",
            text,
        )
        self.assertIn(
            "assign these first: [HYPERFLEET-3](https://example.atlassian.net/browse/HYPERFLEET-3)"
            " (blocks 7)",
            text,
        )

    def test_bare_style_leaves_every_key_plain(self):
        data = self.data()
        data["link_style"] = "bare"
        data["escalation_20d"] = ["HYPERFLEET-2"]
        text = pc.render_text(data)
        self.assertIn("Escalation 20+ days: HYPERFLEET-2", text)
        self.assertNotIn("](", text)

    def test_a_failed_pull_request_read_is_named(self):
        data = self.data()
        data["pr_signal"] = {"available": False, "failed": 1, "checked": 3, "found": 0}
        self.assertIn(
            "Signal: partial - 1 of 3 pull request reads failed",
            pc.render_text(data),
        )

    def test_a_failed_changelog_read_is_named_in_the_report(self):
        data = self.data()
        data["changelog_signal"] = {
            "available": False,
            "failed": 2,
            "checked": 7,
            "status_dates": 5,
            "assignments": 3,
        }
        self.assertIn(
            "Signal: partial - 2 of 7 changelog reads failed", pc.render_text(data)
        )

    def test_a_missing_token_is_named_in_the_report(self):
        data = self.data()
        data["changelog_signal"] = {"available": False, "failed": 0, "checked": 7}
        self.assertIn(
            "Signal: partial - no JIRA_API_TOKEN", pc.render_text(data)
        )

    def test_a_complete_signal_prints_no_partial_line(self):
        data = self.data()
        data["changelog_signal"] = {
            "available": True,
            "failed": 0,
            "checked": 7,
            "status_dates": 5,
            "assignments": 3,
        }
        self.assertNotIn("Signal: partial", pc.render_text(data))


class TicketRefTest(unittest.TestCase):
    base = "https://example.atlassian.net/browse/"

    def test_markdown_is_the_default_shape(self):
        self.assertEqual(
            pc.ticket_ref("HYPERFLEET-1", self.base, "markdown"),
            "[HYPERFLEET-1](https://example.atlassian.net/browse/HYPERFLEET-1)",
        )

    def test_slack_uses_angle_brackets(self):
        self.assertEqual(
            pc.ticket_ref("HYPERFLEET-1", self.base, "slack"),
            "<https://example.atlassian.net/browse/HYPERFLEET-1|HYPERFLEET-1>",
        )

    def test_bare_style_ignores_the_url(self):
        self.assertEqual(pc.ticket_ref("HYPERFLEET-1", self.base, "bare"), "HYPERFLEET-1")

    def test_no_base_url_falls_back_to_bare(self):
        self.assertEqual(pc.ticket_ref("HYPERFLEET-1", None, "markdown"), "HYPERFLEET-1")


class LargeItemQueryTest(unittest.TestCase):
    def test_done_is_filtered_by_category_not_by_status_name(self):
        with mock.patch.object(pc, "run_jira", return_value="HYPERFLEET-1\n") as fake:
            keys = pc.large_item_keys(
                "HYPERFLEET", "66537", 5, "Story Points", "jira"
            )
        jql = fake.call_args.args[0][fake.call_args.args[0].index("-q") + 1]
        self.assertEqual(keys, ["HYPERFLEET-1"])
        self.assertIn("statusCategory != Done", jql)
        self.assertNotIn("status != Closed", jql)

    def test_the_query_is_scoped_to_the_reported_sprint(self):
        with mock.patch.object(pc, "run_jira", return_value="") as fake:
            pc.large_item_keys("HYPERFLEET", "66537", 5, "Story Points", "jira")
        jql = fake.call_args.args[0][fake.call_args.args[0].index("-q") + 1]
        self.assertIn("sprint = 66537", jql)
        self.assertNotIn("openSprints()", jql)


class OpenLinksTest(unittest.TestCase):
    def test_a_done_category_closes_the_link(self):
        self.assertEqual(jc.open_links(["HYPERFLEET-2"], {"HYPERFLEET-2": "Done"}), [])

    def test_a_status_named_closed_but_still_in_progress_stays_open(self):
        self.assertEqual(
            jc.open_links(["HYPERFLEET-2"], {"HYPERFLEET-2": "In Progress"}),
            ["HYPERFLEET-2"],
        )

    def test_an_unread_target_counts_as_open(self):
        self.assertEqual(jc.open_links(["HYPERFLEET-2"], {}), ["HYPERFLEET-2"])


if __name__ == "__main__":
    unittest.main()
