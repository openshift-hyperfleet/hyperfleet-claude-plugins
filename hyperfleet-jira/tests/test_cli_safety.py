"""Regression tests for executable selection and private CLI diagnostics."""

import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import jira_common as jc
import pulse_check as pc
import sprint_status as ss


SECRET = "private-token-and-issue-content"


class ExecutableTest(unittest.TestCase):
    """Both entry points reject executable overrides before any Jira call."""

    def test_collectors_reject_other_executables_before_running(self):
        """Neither shell commands nor absolute executable paths are accepted."""
        for collector in (pc, ss):
            for binary in ("sh", "/bin/sh", "/usr/local/bin/jira", "jira; id"):
                with self.subTest(collector=collector.__name__, binary=binary), \
                     mock.patch.object(sys, "argv", ["collector", "--jira", binary]), \
                     mock.patch.object(sys, "stderr", new_callable=io.StringIO), \
                     mock.patch.object(jc.subprocess, "run") as run, \
                     mock.patch.object(collector, "build") as build:
                    with self.assertRaises(SystemExit) as caught:
                        collector.main()
                    self.assertEqual(caught.exception.code, 2)
                    run.assert_not_called()
                    build.assert_not_called()

    def test_collectors_accept_the_fixed_executable(self):
        """The default and explicit jira option preserve the supported path."""
        for collector in (pc, ss):
            for flags in ([], ["--jira", "jira"]):
                with self.subTest(collector=collector.__name__, flags=flags), \
                     mock.patch.object(sys, "argv", ["collector", *flags]), \
                     mock.patch.object(sys, "stdout", new_callable=io.StringIO), \
                     mock.patch.object(collector, "build", return_value={}) as build:
                    self.assertEqual(collector.main(), 0)
                    self.assertEqual(build.call_args.args[0].jira, "jira")

    def test_direct_calls_also_reject_other_executables(self):
        """The shared runner cannot bypass the parser's restriction."""
        with mock.patch.object(jc.subprocess, "run") as run:
            with self.assertRaises(jc.JiraError):
                jc.run_jira(["issue", "list"], "/bin/sh")
            run.assert_not_called()


class DiagnosticsTest(unittest.TestCase):
    """Failures reveal only fixed identifiers, never captured CLI contents."""

    def test_nonzero_exit_does_not_expose_output_or_arguments(self):
        """Private command arguments, stdout and stderr stay out of errors."""
        proc = mock.Mock(returncode=1, stdout=SECRET, stderr=SECRET)
        with mock.patch.object(jc.subprocess, "run", return_value=proc):
            with self.assertRaises(jc.JiraError) as caught:
                jc.run_jira(["issue", "list", "-q", SECRET], "jira")
        self.assertEqual(str(caught.exception), "jira issue list failed (exit status 1)")

    def test_unknown_command_uses_a_fixed_identifier(self):
        """Even an unexpected argument list is not copied to the error."""
        with mock.patch.object(jc.subprocess, "run", return_value=mock.Mock(returncode=2)):
            with self.assertRaises(jc.JiraError) as caught:
                jc.run_jira([SECRET], "jira")
        self.assertEqual(str(caught.exception), "jira command failed (exit status 2)")

    def test_timeout_and_launch_errors_do_not_expose_exception_details(self):
        """Exception text and captured output are suppressed on process failures."""
        errors = (
            jc.subprocess.TimeoutExpired(SECRET, 120, output=SECRET, stderr=SECRET),
            FileNotFoundError(SECRET),
            PermissionError(SECRET),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__), \
                 mock.patch.object(jc.subprocess, "run", side_effect=error):
                with self.assertRaises(jc.JiraError) as caught:
                    jc.run_jira(["issue", "list"], "jira")
                self.assertNotIn(SECRET, str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_unreadable_issue_diagnostics_are_safe_in_both_failure_paths(self):
        """Neither the failure map nor fetch_all's warning contains CLI output."""
        for proc in (
            mock.Mock(returncode=1, stdout=SECRET, stderr=SECRET),
            mock.Mock(returncode=0, stdout=SECRET),
        ):
            with self.subTest(returncode=proc.returncode), \
                 mock.patch.object(jc.subprocess, "run", return_value=proc), \
                 mock.patch.object(sys, "stderr", new_callable=io.StringIO) as stderr:
                failures = {}
                self.assertEqual(jc.fetch_all(["HYPERFLEET-1"], "HYPERFLEET", "jira", 1, failures), {})
                self.assertNotIn(SECRET, str(failures))
                self.assertIn("HYPERFLEET-1", failures)
                self.assertEqual(jc.fetch_all(["HYPERFLEET-1"], "HYPERFLEET", "jira", 1), {})
                self.assertIn("warning:", stderr.getvalue())
                self.assertNotIn(SECRET, stderr.getvalue())

    def test_both_entry_points_print_only_sanitized_cli_errors(self):
        """A real build failure cannot copy private CLI output to the console."""
        proc = mock.Mock(returncode=1, stdout=SECRET, stderr=SECRET)
        for collector in (pc, ss):
            with self.subTest(collector=collector.__name__), \
                 mock.patch.object(sys, "argv", ["collector"]), \
                 mock.patch.object(sys, "stderr", new_callable=io.StringIO) as stderr, \
                 mock.patch.object(sys, "stdout", new_callable=io.StringIO) as stdout, \
                 mock.patch.object(jc.subprocess, "run", return_value=proc):
                self.assertEqual(collector.main(), 1)
                self.assertEqual(stderr.getvalue(), "error: jira sprint list failed (exit status 1)\n")
                self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
