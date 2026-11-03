"""Tests for the sprint status collector.

Run from the plugin directory:

    python3 -m unittest discover -s tests -v

The cases that matter are the ones where a plausible implementation returns a
comfortable number that is wrong: the 100-issue page cap (which silently drops
the tail of a sprint), the status names that match nothing in HYPERFLEET, and
the movement signal that counts automation comments as activity.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import jira_common as jc  # noqa: E402
import sprint_status as ss  # noqa: E402

TODAY = date(2026, 11, 3)


def doc(
    key="HYPERFLEET-100",
    *,
    sp=5,
    owner="A Person",
    status="Backlog",
    category="To Do",
    priority="Normal",
    changed="2026-10-04",
    comments=(),
    links=(),
    summary="An item",
):
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "issuetype": {"name": "Story"},
            "customfield_10028": sp,
            "assignee": {"displayName": owner} if owner else None,
            "status": {"name": status, "statusCategory": {"name": category}},
            "priority": {"name": priority},
            "parent": {"key": "HYPERFLEET-1"},
            "created": "2026-09-01T10:00:00.000+0000",
            "statuscategorychangedate": f"{changed}T10:00:00.000+0000",
            "comment": {"comments": list(comments)},
            "issuelinks": list(links),
        },
    }


def comment(created, author="A Person", account_type="atlassian"):
    return {
        "created": f"{created}T09:00:00.000+0000",
        "author": {"displayName": author, "accountType": account_type},
    }


def item(key, *, sp=5, owner="A Person", status="Backlog", category="To Do", days=0):
    return {
        "key": key,
        "summary": "An item",
        "sp": sp,
        "owner": owner,
        "status": status,
        "category": category,
        "is_done": category == "Done",
        "days_without_movement": days,
    }


class PaginationTest(unittest.TestCase):
    """`jira issue list --paginate` ignores the offset and caps at 100."""

    def test_reads_past_the_first_hundred_issues(self):
        calls = []

        def fake_run_jira(args, binary):
            calls.append(args)
            jql = args[args.index("-q") + 1]
            if "key <" in jql:
                return "\n".join(f"HYPERFLEET-{n}" for n in range(100, 97, -1)) + "\n"
            return "\n".join(f"HYPERFLEET-{n}" for n in range(200, 100, -1)) + "\n"

        with mock.patch.object(jc, "run_jira", side_effect=fake_run_jira):
            keys = ss.search_keys("project = HYPERFLEET", "HYPERFLEET", "jira")

        self.assertEqual(len(keys), 103)
        self.assertEqual(len(set(keys)), 103)
        self.assertIn("HYPERFLEET-98", keys)
        self.assertEqual(len(calls), 2)
        self.assertIn("key < HYPERFLEET-101", calls[1][calls[1].index("-q") + 1])

    def test_stops_when_a_batch_is_short(self):
        with mock.patch.object(
            jc, "run_jira", return_value="HYPERFLEET-3\nHYPERFLEET-2\n"
        ) as fake:
            keys = ss.search_keys("project = HYPERFLEET", "HYPERFLEET", "jira")
        self.assertEqual(keys, ["HYPERFLEET-3", "HYPERFLEET-2"])
        self.assertEqual(fake.call_count, 1)


class DescribeTest(unittest.TestCase):
    def test_status_category_is_read_not_status_name(self):
        described = ss.describe("HYPERFLEET-100", doc(status="Closed", category="Done"), "customfield_10028", TODAY)
        self.assertTrue(described["is_done"])
        self.assertEqual(described["category"], "Done")

    def test_missing_story_points_are_none_not_zero(self):
        described = ss.describe("HYPERFLEET-100", doc(sp=None), "customfield_10028", TODAY)
        self.assertIsNone(described["sp"])

    def test_automation_comments_are_not_movement(self):
        described = ss.describe(
            "HYPERFLEET-100",
            doc(changed="2026-10-04", comments=[comment("2026-11-02", "Automation", "app")]),
            "customfield_10028",
            TODAY,
        )
        self.assertEqual(described["days_without_movement"], 30)
        self.assertIsNone(described["last_comment"])

    def test_human_comment_resets_the_clock(self):
        described = ss.describe(
            "HYPERFLEET-100",
            doc(changed="2026-10-04", comments=[comment("2026-11-01")]),
            "customfield_10028",
            TODAY,
        )
        self.assertEqual(described["days_without_movement"], 2)

    def test_block_link_is_not_a_blocker(self):
        link = {
            "type": {"inward": "is blocked by", "outward": "blocks"},
            "outwardIssue": {"key": "HYPERFLEET-200"},
        }
        blocked_by, blocks = jc.link_targets(doc(links=[link]))
        self.assertEqual(blocked_by, [])
        self.assertEqual(blocks, ["HYPERFLEET-200"])


class ChangelogSignalTest(unittest.TestCase):
    def item(self, **overrides):
        base = {
            "key": "HYPERFLEET-1671",
            "owner": "Phuongnhat Nguyen",
            "assignee_id": "acc-1",
            "days_in_status": 47,
            "days_since_comment": 13,
            "days_without_movement": 13,
        }
        base.update(overrides)
        return base

    def test_status_change_inside_a_category_resets_the_clock(self):
        subject = self.item(days_in_status=15, days_without_movement=15)
        with mock.patch.object(jc, "jira_api", return_value=("https://x", "auth")), \
             mock.patch.object(
                 jc, "changelog_dates", return_value=(date(2026, 10, 30), None)
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_in_status"], 4)
        self.assertEqual(subject["days_without_movement"], 4)
        self.assertEqual(subject["status_entered"], "2026-10-30")

    def test_assignment_resets_the_clock(self):
        subject = self.item()
        with mock.patch.object(jc, "jira_api", return_value=("https://x", "auth")), \
             mock.patch.object(
                 jc, "changelog_dates", return_value=(None, date(2026, 10, 30))
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_without_movement"], 4)

    def test_new_to_backlog_is_not_movement(self):
        self.assertFalse(
            jc.status_change_counts({"fromString": "New", "toString": "Backlog"})
        )
        self.assertTrue(
            jc.status_change_counts({"fromString": "Backlog", "toString": "In Progress"})
        )
        self.assertTrue(
            jc.status_change_counts({"fromString": "In Progress", "toString": "Review"})
        )

    def test_missing_token_keeps_the_old_clock(self):
        subject = self.item()
        with mock.patch.object(jc, "jira_api", return_value=None):
            report = ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertFalse(report["available"])
        self.assertEqual(subject["days_without_movement"], 13)


class SummariseTest(unittest.TestCase):
    def test_progress_is_reported_by_points_and_by_count(self):
        items = [
            item("A", sp=5, category="Done", status="Closed"),
            item("B", sp=5, category="To Do"),
            item("C", sp=10, category="To Do"),
        ]
        summary = ss.summarise(items)
        self.assertEqual(summary["sp"], 20)
        self.assertEqual(summary["percent_by_sp"], 25.0)
        self.assertEqual(summary["percent_by_items"], 33.3)

    def test_unestimated_items_count_as_zero_points_but_as_an_item(self):
        summary = ss.summarise([item("A", sp=None), item("B", sp=5, category="Done")])
        self.assertEqual(summary["sp"], 5)
        self.assertEqual(summary["items"], 2)
        self.assertEqual(summary["percent_by_sp"], 100.0)

    def test_statuses_are_ordered_by_category(self):
        summary = ss.summarise(
            [
                item("A", status="Closed", category="Done"),
                item("B", status="Backlog", category="To Do"),
                item("C", status="Review", category="In Progress"),
            ]
        )
        self.assertEqual(
            [bucket["status"] for bucket in summary["by_status"]],
            ["Backlog", "Review", "Closed"],
        )


class WorkloadTest(unittest.TestCase):
    def test_unassigned_is_a_row_not_a_crash(self):
        rows = ss.workload(
            [item("A", owner=""), item("B", owner="B Person")], ["Backlog", "Closed"]
        )
        self.assertEqual(rows[0]["owner"], "B Person")
        self.assertEqual(rows[-1]["owner"], "Unassigned")
        self.assertEqual(rows[-1]["items"], 1)


class CarryOverTest(unittest.TestCase):
    def test_done_items_are_never_candidates(self):
        carry = ss.carry_over(
            [item("A", owner="", category="Done", status="Closed")], stale_days=5
        )
        self.assertEqual(carry["items"], 0)

    def test_unassigned_sorts_before_stale(self):
        carry = ss.carry_over(
            [
                item("A", status="In Progress", category="In Progress", days=40),
                item("B", owner="", days=0),
            ],
            stale_days=5,
        )
        self.assertEqual([c["key"] for c in carry["candidates"]], ["B", "A"])

    def test_reasons_are_counted(self):
        carry = ss.carry_over(
            [
                item("A", owner="", sp=None),
                item("B", days=10, status="Review", category="In Progress"),
            ],
            stale_days=5,
        )
        self.assertEqual(carry["by_reason"], {"unassigned": 1, "stale": 1, "unestimated": 1})

    def test_backlog_is_not_stale(self):
        carry = ss.carry_over([item("A", days=90)], stale_days=5)
        self.assertEqual(carry["by_reason"]["stale"], 0)


class CapacityTest(unittest.TestCase):
    sprint = {"start": "2026-11-02", "end": "2026-11-22"}

    def test_days_are_counted_the_way_a_person_counts_them(self):
        calendar = ss.sprint_calendar(date(2026, 11, 2), date(2026, 11, 22), TODAY)
        self.assertEqual(calendar["days_total"], 21)
        self.assertEqual(calendar["days_elapsed"], 1)
        self.assertEqual(calendar["days_remaining"], 20)

    def test_projects_from_the_previous_pace(self):
        projection = ss.capacity(
            remaining_sp=120,
            sprint=self.sprint,
            baseline={"delivered_sp": 100, "days": 10},
            today=TODAY,
        )
        self.assertTrue(projection["available"])
        self.assertEqual(projection["days_remaining"], 20)
        self.assertEqual(projection["expected_sp"], 200.0)
        self.assertEqual(projection["over_capacity_sp"], 0.0)
        self.assertEqual(projection["headroom_sp"], 80.0)

    def test_over_capacity_is_reported_when_scope_exceeds_pace(self):
        projection = ss.capacity(
            remaining_sp=300,
            sprint=self.sprint,
            baseline={"delivered_sp": 100, "days": 10},
            today=TODAY,
        )
        self.assertEqual(projection["over_capacity_sp"], 100.0)
        self.assertEqual(projection["headroom_sp"], 0.0)

    def test_without_a_baseline_it_says_so_instead_of_guessing(self):
        projection = ss.capacity(120, self.sprint, None, TODAY)
        self.assertFalse(projection["available"])
        self.assertIn("baseline", projection["reason"])


class BarTest(unittest.TestCase):
    def test_width_never_moves(self):
        widths = {len(ss.bar(percent)) for percent in (0, 3, 50, 99, 100)}
        self.assertEqual(len(widths), 1)

    def test_full_bar_is_all_equals(self):
        self.assertNotIn(">", ss.bar(100))


class TicketRefTest(unittest.TestCase):
    base = "https://example.atlassian.net/browse/"

    def test_markdown_is_the_default_shape(self):
        self.assertEqual(
            ss.ticket_ref("HYPERFLEET-1", self.base, "markdown"),
            "[HYPERFLEET-1](https://example.atlassian.net/browse/HYPERFLEET-1)",
        )

    def test_slack_uses_angle_brackets(self):
        self.assertEqual(
            ss.ticket_ref("HYPERFLEET-1", self.base, "slack"),
            "<https://example.atlassian.net/browse/HYPERFLEET-1|HYPERFLEET-1>",
        )

    def test_bare_style_ignores_the_url(self):
        self.assertEqual(ss.ticket_ref("HYPERFLEET-1", self.base, "bare"), "HYPERFLEET-1")

    def test_no_base_url_falls_back_to_bare(self):
        self.assertEqual(ss.ticket_ref("HYPERFLEET-1", None, "markdown"), "HYPERFLEET-1")


class PullRequestTest(unittest.TestCase):
    """The development panel lists branches, commits and other tickets' pull requests."""

    pr = {"number": 104, "url": "https://github.com/o/r/pull/104"}

    def payload(self, key="HYPERFLEET-104"):
        return [
            {"object": {"url": "https://github.com/o/r/pull/104",
                        "title": f"{key} - fix: a thing"}},
            {"object": {"url": "https://github.com/o/r/pull/104",
                        "title": f"{key} - fix: a thing"}},
            {"object": {"url": "https://github.com/o/r/tree/pr-links", "title": key}},
            {"object": {"url": "https://github.com/o/r/commit/abc123", "title": key}},
            {"object": {"url": "https://github.com/o/r/pull/99", "title": f"{key} - fix: older"}},
            {"object": {"url": "http://github.com/o/r/pull/7", "title": f"{key} - fix: cleartext"}},
        ]

    def test_only_pull_request_urls_count_and_a_duplicate_is_listed_once(self):
        owned, other = jc.pull_requests_from(self.payload(), "HYPERFLEET-104")
        self.assertEqual([pr["number"] for pr in owned], [104, 99])
        self.assertEqual(other, [])

    def test_a_pull_request_titled_for_another_ticket_is_a_cross_reference(self):
        payload = [
            {
                "object": {
                    "url": "https://github.com/o/r/pull/255",
                    "title": "HYPERFLEET-1636 - docs: sync the wristband contract",
                }
            }
        ]
        owned, other = jc.pull_requests_from(payload, "HYPERFLEET-1669")
        self.assertEqual(owned, [])
        self.assertEqual(
            other,
            [{"number": 255, "url": "https://github.com/o/r/pull/255", "titled": "HYPERFLEET-1636"}],
        )

    def test_a_pull_request_that_names_both_tickets_belongs_to_both(self):
        payload = [
            {
                "object": {
                    "url": "https://github.com/o/r/pull/255",
                    "title": "HYPERFLEET-1636 + HYPERFLEET-1669 - docs: the contract",
                }
            }
        ]
        owned, other = jc.pull_requests_from(payload, "HYPERFLEET-1669")
        self.assertEqual([pr["number"] for pr in owned], [255])
        self.assertEqual(other, [])

    def test_a_title_without_any_ticket_key_is_shown_without_a_claim(self):
        payload = [
            {"object": {"url": "https://github.com/o/r/pull/5", "title": "fix: a thing"}}
        ]
        owned, other = jc.pull_requests_from(payload, "HYPERFLEET-104")
        self.assertEqual(owned, [])
        self.assertEqual([pr["titled"] for pr in other], [None])

    def test_a_longer_key_does_not_match_the_shorter_one(self):
        payload = [
            {
                "object": {
                    "url": "https://github.com/o/r/pull/6",
                    "title": "HYPERFLEET-16360 - fix: a thing",
                }
            }
        ]
        owned, other = jc.pull_requests_from(payload, "HYPERFLEET-1636")
        self.assertEqual(owned, [])
        self.assertEqual([pr["titled"] for pr in other], ["HYPERFLEET-16360"])

    def test_the_newest_pull_request_comes_first(self):
        owned, _ = jc.pull_requests_from(
            [
                {"object": {"url": "https://github.com/o/r/pull/9",
                            "title": "HYPERFLEET-104 - a"}},
                {"object": {"url": "https://github.com/o/r/pull/120",
                            "title": "HYPERFLEET-104 - b"}},
                {"object": {"url": "https://github.com/o/r/pull/11",
                            "title": "HYPERFLEET-104 - c"}},
            ],
            "HYPERFLEET-104",
        )
        self.assertEqual([pr["number"] for pr in owned], [120, 11, 9])

    def test_markdown_links_the_number_not_the_url(self):
        self.assertEqual(
            jc.pr_ref(self.pr, "markdown"),
            "[#104](https://github.com/o/r/pull/104)",
        )

    def test_slack_wraps_the_url_with_the_number_as_text(self):
        self.assertEqual(
            jc.pr_ref(self.pr, "slack"),
            "<https://github.com/o/r/pull/104|#104>",
        )

    def test_bare_style_keeps_the_url_the_reader_would_lose(self):
        self.assertIn("https://github.com/o/r/pull/104", jc.pr_ref(self.pr, "bare"))

    def test_pr_refs_caps_the_list_and_counts_the_rest(self):
        item = {
            "pr": [
                {"number": number, "url": f"https://github.com/o/r/pull/{number}"}
                for number in (3, 2, 1)
            ]
        }
        self.assertTrue(jc.pr_refs(item, "markdown").endswith("+1"))

    def test_an_item_without_a_pull_request_renders_nothing(self):
        self.assertEqual(jc.pr_refs({"pr": []}, "markdown"), "")

    def test_a_cross_reference_names_the_ticket_its_title_names(self):
        item = {
            "pr": [],
            "pr_other": [
                {"number": 255, "url": "https://github.com/o/r/pull/255",
                 "titled": "HYPERFLEET-1636"}
            ],
        }
        rendered = jc.other_pr_refs(item, "markdown")
        self.assertIn("[#255](https://github.com/o/r/pull/255)", rendered)
        self.assertIn("titled HYPERFLEET-1636", rendered)

    def test_a_cross_reference_without_a_key_says_so(self):
        item = {
            "pr": [],
            "pr_other": [
                {"number": 5, "url": "https://github.com/o/r/pull/5", "titled": None}
            ],
        }
        self.assertIn("no ticket key in the title", jc.other_pr_refs(item, "markdown"))

    def test_only_review_items_are_looked_up(self):
        items = [
            {"key": "HYPERFLEET-1", "status": "Review"},
            {"key": "HYPERFLEET-2", "status": "Backlog"},
        ]
        with mock.patch.object(jc, "jira_api", return_value=None):
            signal = jc.apply_pull_requests(items, 2)
        self.assertEqual(signal["checked"], 1)
        self.assertFalse(signal["available"])
        self.assertEqual(items[1]["pr"], [])


class PreviousSprintTest(unittest.TestCase):
    rows = [
        {"id": "1", "name": "Sprint 17", "start": "2026-09-01", "end": "2026-09-21", "state": "closed"},
        {"id": "2", "name": "Sprint 18", "start": "2026-09-22", "end": "2026-10-12", "state": "closed"},
        {"id": "3", "name": "Sprint 19", "start": "2026-11-02", "end": "2026-11-22", "state": "closed"},
    ]

    def find(self, before=None):
        with mock.patch.object(ss, "sprint_rows", return_value=self.rows):
            return ss.previous_sprint("HYPERFLEET", "jira", before)

    def test_without_a_target_the_latest_closed_sprint_wins(self):
        self.assertEqual(self.find()["id"], "3")

    def test_a_later_closed_sprint_is_not_a_baseline(self):
        found = self.find(before="2026-11-02")
        self.assertEqual(found["id"], "2")

    def test_no_earlier_sprint_returns_none(self):
        self.assertIsNone(self.find(before="2026-09-01"))

    def test_a_row_with_no_end_date_is_not_a_baseline(self):
        rows = [{"id": "9", "name": "Broken", "start": "", "end": "", "state": "closed"}]
        with mock.patch.object(ss, "sprint_rows", return_value=rows):
            self.assertIsNone(ss.previous_sprint("HYPERFLEET", "jira", "2026-11-02"))


class RenderSignalTest(unittest.TestCase):
    def data(self):
        return {
            "sprint": {"name": "Sprint 19", "start": "2026-11-02", "end": "2026-11-22"},
            "totals": {
                "by_status": [{"status": "Backlog", "category": "To Do", "items": 1, "sp": 5}],
                "items": 1,
                "sp": 5,
                "percent_by_sp": 0,
                "percent_by_items": 0,
                "done": {"items": 0, "sp": 0},
            },
            "blockers": {
                "blocked": [],
                "blocked_items": 0,
                "blocked_sp": 0,
                "high_priority": [],
                "priority_checked": "Major",
                "priorities_seen": ["Normal"],
            },
            "at_risk": {
                "stale": [],
                "stale_items": 0,
                "stale_days": 5,
                "missing_sp_items": 0,
                "unassigned_items": 0,
                "unassigned_sp": 0,
            },
            "carry_over": {
                "items": 0,
                "sp": 0,
                "by_reason": {"unassigned": 0, "stale": 0, "unestimated": 0},
            },
            "capacity": {"available": False, "reason": "no baseline"},
            "workload": [],
            "workload_statuses": [],
            "notes": {
                "movement_basis": "movement basis",
                "progress_basis": "progress basis",
                "baseline_basis": "baseline basis",
            },
            "changelog_signal": {"available": True, "failed": 0, "checked": 1},
        }

    def test_method_names_all_three_bases(self):
        text = ss.render_text(self.data())
        for basis in ("movement basis", "progress basis", "baseline basis"):
            self.assertIn(basis, text)

    def test_a_review_item_carries_its_pull_request(self):
        data = self.data()
        data["jira_base_url"] = "https://example.atlassian.net/browse/"
        data["link_style"] = "markdown"
        data["at_risk"]["stale"] = [
            {
                "key": "HYPERFLEET-9",
                "summary": "An item",
                "owner": "A Person",
                "status": "Review",
                "days_without_movement": 7,
                "pr": [{"number": 104, "url": "https://github.com/o/r/pull/104"}],
            }
        ]
        data["at_risk"]["stale_items"] = 1
        self.assertIn(
            "(7d) - PR [#104](https://github.com/o/r/pull/104)", ss.render_text(data)
        )

    def test_a_failed_pull_request_read_is_named(self):
        data = self.data()
        data["pr_signal"] = {"available": False, "failed": 2, "checked": 5, "found": 1}
        self.assertIn(
            "signal: partial - 2 of 5 pull request reads failed", ss.render_text(data)
        )

    def test_a_failed_changelog_read_is_named_in_the_report(self):
        data = self.data()
        data["changelog_signal"] = {"available": False, "failed": 2, "checked": 7}
        self.assertIn("signal: partial - 2 of 7 changelog reads failed", ss.render_text(data))

    def test_a_missing_token_is_named_in_the_report(self):
        data = self.data()
        data["changelog_signal"] = {"available": False, "failed": 0, "checked": 7}
        self.assertIn("signal: partial - no JIRA_API_TOKEN", ss.render_text(data))

    def test_a_complete_signal_prints_no_partial_line(self):
        self.assertNotIn("signal: partial", ss.render_text(self.data()))


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
                 side_effect=ss.ChangelogUnavailable("HYPERFLEET-1671: HTTPError"),
             ):
            report = ss.apply_changelog_signals([self.item()], TODAY, 1)
        self.assertFalse(report["available"])
        self.assertEqual(report["failed"], 1)

    def test_a_failed_read_leaves_the_clock_alone(self):
        subject = self.item()
        with mock.patch.object(jc, "jira_api", return_value=self.api), \
             mock.patch.object(
                 jc, "changelog_dates", side_effect=ss.ChangelogUnavailable("boom")
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_without_movement"], 13)
        self.assertIsNone(subject["status_entered"])


class JiraApiGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        (Path(self.tmp.name) / ".config" / ".jira").mkdir(parents=True)
        self.config = Path(self.tmp.name) / ".config" / ".jira" / ".config.yml"

    def api(self, server):
        self.config.write_text(f"server: {server}\nlogin: someone@example.com\n")
        with mock.patch.object(jc.Path, "home", return_value=Path(self.tmp.name)), \
             mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "token"}):
            return jc.jira_api()

    def test_https_is_kept(self):
        self.assertEqual(
            self.api("https://x.atlassian.net")[0], "https://x.atlassian.net"
        )

    def test_a_bare_host_gets_https(self):
        self.assertEqual(self.api("x.atlassian.net")[0], "https://x.atlassian.net")

    def test_cleartext_http_is_refused(self):
        self.assertIsNone(self.api("http://x.atlassian.net"))


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

    def test_a_network_error_is_counted(self):
        with self.assertRaises(ss.ChangelogUnavailable):
            self.call(error=jc.urllib.error.URLError("401 Unauthorized"))

    def test_a_truncated_response_is_counted(self):
        with self.assertRaises(ss.ChangelogUnavailable):
            self.call(error=jc.http.client.IncompleteRead(b""))

    def test_a_non_utf8_body_is_counted(self):
        error = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        with self.assertRaises(ss.ChangelogUnavailable):
            self.call(error=error)

    def test_a_capped_changelog_is_counted(self):
        with self.assertRaises(ss.ChangelogUnavailable):
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


class ProjectArgumentTest(unittest.TestCase):
    def test_a_project_key_is_accepted(self):
        self.assertEqual(ss.project_key("HYPERFLEET"), "HYPERFLEET")

    def test_jql_is_not_a_project_key(self):
        with self.assertRaises(jc.argparse.ArgumentTypeError):
            ss.project_key("HF OR project = SECRET")


class BaselineTest(unittest.TestCase):
    """The baseline measures the previous sprint at its own end date."""

    sprint = {
        "id": "66536",
        "name": "Hyperfleet Sprint 18",
        "start": "2026-10-12",
        "end": "2026-10-25",
    }

    def run_baseline(self, docs):
        with mock.patch.object(ss, "search_keys", return_value=[d["key"] for d in docs]), \
             mock.patch.object(ss, "fetch_all", return_value={d["key"]: d for d in docs}):
            return ss.baseline_for(
                self.sprint,
                "HYPERFLEET",
                "customfield_10028",
                "jira",
                1,
                TODAY,
            )

    def test_counts_only_work_closed_by_the_sprint_end(self):
        baseline = self.run_baseline(
            [
                doc("HYPERFLEET-1", sp=3, status="Done", category="Done", changed="2026-10-20"),
                doc("HYPERFLEET-2", sp=5, status="Closed", category="Done", changed="2026-11-02"),
                doc("HYPERFLEET-3", sp=2, status="In Progress", category="In Progress", changed="2026-10-20"),
            ]
        )
        self.assertEqual(baseline["committed_sp"], 10)
        self.assertEqual(baseline["delivered_sp"], 3)
        self.assertEqual(baseline["percent"], 30.0)
        self.assertEqual(baseline["end"], "2026-10-25")

    def test_work_closed_on_the_last_day_still_counts(self):
        baseline = self.run_baseline(
            [doc("HYPERFLEET-1", sp=5, status="Closed", category="Done", changed="2026-10-25")]
        )
        self.assertEqual(baseline["delivered_sp"], 5)

    def test_an_open_item_is_never_delivered(self):
        baseline = self.run_baseline(
            [doc("HYPERFLEET-1", sp=5, status="In Progress", category="In Progress", changed="2026-10-20")]
        )
        self.assertEqual(baseline["delivered_sp"], 0)
        self.assertEqual(baseline["percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
