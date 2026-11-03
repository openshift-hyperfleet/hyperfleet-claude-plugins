"""Tests for the sprint status collector.

Run from the plugin directory:

    python3 -m unittest discover -s tests -v

The cases that matter are the ones where a plausible implementation returns a
comfortable number that is wrong: the 100-issue page cap (which silently drops
the tail of a sprint), the status names that match nothing in HYPERFLEET, and
the movement signal that counts automation comments as activity.
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

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

        with mock.patch.object(ss, "run_jira", side_effect=fake_run_jira):
            keys = ss.search_keys("project = HYPERFLEET", "HYPERFLEET", "jira")

        self.assertEqual(len(keys), 103)
        self.assertEqual(len(set(keys)), 103)
        self.assertIn("HYPERFLEET-98", keys)
        self.assertEqual(len(calls), 2)
        self.assertIn("key < HYPERFLEET-101", calls[1][calls[1].index("-q") + 1])

    def test_stops_when_a_batch_is_short(self):
        with mock.patch.object(
            ss, "run_jira", return_value="HYPERFLEET-3\nHYPERFLEET-2\n"
        ) as fake:
            keys = ss.search_keys("project = HYPERFLEET", "HYPERFLEET", "jira")
        self.assertEqual(keys, ["HYPERFLEET-3", "HYPERFLEET-2"])
        self.assertEqual(fake.call_count, 1)


class DescribeTest(unittest.TestCase):
    def test_status_category_is_read_not_status_name(self):
        described = ss.describe(doc(status="Closed", category="Done"), "customfield_10028", TODAY)
        self.assertTrue(described["is_done"])
        self.assertEqual(described["category"], "Done")

    def test_missing_story_points_are_none_not_zero(self):
        described = ss.describe(doc(sp=None), "customfield_10028", TODAY)
        self.assertIsNone(described["sp"])

    def test_automation_comments_are_not_movement(self):
        described = ss.describe(
            doc(changed="2026-10-04", comments=[comment("2026-11-02", "Automation", "app")]),
            "customfield_10028",
            TODAY,
        )
        self.assertEqual(described["days_without_movement"], 30)
        self.assertIsNone(described["last_comment"])

    def test_human_comment_resets_the_clock(self):
        described = ss.describe(
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
        blocked_by, blocks = ss.link_targets(doc(links=[link]))
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
        with mock.patch.object(ss, "jira_api", return_value=("https://x", "auth")), \
             mock.patch.object(
                 ss, "changelog_dates", return_value=(date(2026, 10, 30), None)
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_in_status"], 4)
        self.assertEqual(subject["days_without_movement"], 4)
        self.assertEqual(subject["status_entered"], "2026-10-30")

    def test_assignment_resets_the_clock(self):
        subject = self.item()
        with mock.patch.object(ss, "jira_api", return_value=("https://x", "auth")), \
             mock.patch.object(
                 ss, "changelog_dates", return_value=(None, date(2026, 10, 30))
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_without_movement"], 4)

    def test_new_to_backlog_is_not_movement(self):
        self.assertFalse(
            ss.status_change_counts({"fromString": "New", "toString": "Backlog"})
        )
        self.assertTrue(
            ss.status_change_counts({"fromString": "Backlog", "toString": "In Progress"})
        )
        self.assertTrue(
            ss.status_change_counts({"fromString": "In Progress", "toString": "Review"})
        )

    def test_missing_token_keeps_the_old_clock(self):
        subject = self.item()
        with mock.patch.object(ss, "jira_api", return_value=None):
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
        with mock.patch.object(ss, "jira_api", return_value=self.api), \
             mock.patch.object(
                 ss, "changelog_dates",
                 side_effect=ss.ChangelogUnavailable("HYPERFLEET-1671: HTTPError"),
             ):
            report = ss.apply_changelog_signals([self.item()], TODAY, 1)
        self.assertFalse(report["available"])
        self.assertEqual(report["failed"], 1)

    def test_a_failed_read_leaves_the_clock_alone(self):
        subject = self.item()
        with mock.patch.object(ss, "jira_api", return_value=self.api), \
             mock.patch.object(
                 ss, "changelog_dates", side_effect=ss.ChangelogUnavailable("boom")
             ):
            ss.apply_changelog_signals([subject], TODAY, 1)
        self.assertEqual(subject["days_without_movement"], 13)
        self.assertIsNone(subject["status_entered"])


class ProjectArgumentTest(unittest.TestCase):
    def test_a_project_key_is_accepted(self):
        self.assertEqual(ss.project_key("HYPERFLEET"), "HYPERFLEET")

    def test_jql_is_not_a_project_key(self):
        with self.assertRaises(ss.argparse.ArgumentTypeError):
            ss.project_key("HF OR project = SECRET")


if __name__ == "__main__":
    unittest.main()
