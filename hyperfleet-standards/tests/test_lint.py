"""Regression tests for the Markdown baseline exception and lint entry points."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="plugins-lint-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "hack", self.root / "hack")
        for name in ("Makefile", ".markdownlint-cli2.cjs", ".yamllint"):
            shutil.copy(ROOT / name, self.root / name)
        (self.root / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
        self.baseline = self.root / ".markdownlint-baseline.json"
        self.baseline.write_text('{"version":1,"files":{}}\n')
        self.doc = self.root / "doc.md"
        self.doc.write_text("# Example\n")

    def run_command(self, *args):
        return subprocess.run(args, cwd=self.root, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def markdown(self, *args):
        return self.run_command("bash", "hack/markdownlint.sh", *args)

    def legacy(self):
        self.doc.write_text("# Example\n\n```\ncode\n```\n")
        result = self.markdown("--write-baseline")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_clean_lint_and_help(self):
        result = self.run_command("make", "lint")
        self.assertEqual(result.returncode, 0, result.stdout)
        (self.root / "broken.yaml").write_text("key: [broken\n")
        result = self.run_command("make", "help")
        self.assertEqual(result.returncode, 0, result.stdout)
        for target in ("help", "test", "lint"):
            self.assertIn(target, result.stdout)
        self.assertNotIn("Running", result.stdout)

    def test_new_markdown_failure_does_not_rewrite_baseline(self):
        before = self.baseline.read_bytes()
        (self.root / "new $(touch INJECTED).md").write_text("# Example\n\n```\ncode\n```\n")
        result = self.run_command("make", "lint")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("MD040", result.stdout)
        self.assertEqual(self.baseline.read_bytes(), before)
        self.assertFalse((self.root / "INJECTED").exists())

    def test_existing_violation_and_moved_line_are_accepted(self):
        self.legacy()
        self.doc.write_text(self.doc.read_text().replace("# Example\n", "# Example\n\nIntro.\n"))
        result = self.markdown()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("1 existing violations, 0 new violations", result.stdout)

    def test_changed_violation_is_not_accepted(self):
        self.legacy()
        self.doc.write_text(self.doc.read_text().replace("```", "~~~"))
        self.assertNotEqual(self.markdown().returncode, 0)

    def test_extra_occurrence_is_not_accepted(self):
        self.legacy()
        self.doc.write_text(self.doc.read_text() + "\n```\nmore\n```\n")
        self.assertNotEqual(self.markdown().returncode, 0)

    def test_waiver_does_not_transfer_to_new_file(self):
        self.legacy()
        shutil.copy(self.doc, self.root / "new.md")
        self.assertNotEqual(self.markdown().returncode, 0)

    def test_missing_and_malformed_baseline_fail(self):
        for content in (None, "{broken", '{"version":1,"files":{"doc.md":[]}}'):
            with self.subTest(content=content):
                if content is None:
                    self.baseline.unlink()
                else:
                    self.baseline.write_text(content)
                self.assertNotEqual(self.markdown().returncode, 0)

    def test_yaml_failure_is_not_baselined(self):
        self.legacy()
        (self.root / "broken.yaml").write_text("key: [broken\n")
        result = self.run_command("make", "lint")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("syntax error", result.stdout)

    def test_cli_failure_and_missing_output_fail_even_when_writing_baseline(self):
        (self.root / "node_modules").unlink()
        binary = self.root / "node_modules/.bin/markdownlint-cli2"
        binary.parent.mkdir(parents=True)
        before = self.baseline.read_bytes()
        for code, output in ((0, ""), (1, ""), (2, ""), (127, ""),
                             (2, 'echo "[]" > "$MARKDOWNLINT_RESULTS"\n')):
            with self.subTest(code=code, output=output):
                binary.write_text(f"#!/bin/sh\n{output}exit {code}\n")
                binary.chmod(0o755)
                self.assertNotEqual(self.markdown("--write-baseline").returncode, 0)
                self.assertEqual(self.baseline.read_bytes(), before)

    def test_inconsistent_cli_status_fails(self):
        results = self.root / "results.json"
        results.write_text("[]")
        result = self.run_command(os.environ.get("PYTHON", "python3"),
                                  "hack/markdownlint-baseline.py", str(results), "1")
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_cli_config_is_not_baselined(self):
        (self.root / ".markdownlint-cli2.cjs").write_text("throw new Error('broken config');\n")
        before = self.baseline.read_bytes()
        self.assertNotEqual(self.markdown("--write-baseline").returncode, 0)
        self.assertEqual(self.baseline.read_bytes(), before)

    def test_test_discovery_failure_propagation_and_empty_suite(self):
        result = self.run_command("make", "test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No test suites found", result.stdout)
        runner = self.root / "plugin with spaces/tests/run-tests.sh"
        runner.parent.mkdir(parents=True)
        runner.write_text("exit 3\n")
        result = self.run_command("make", "test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Running plugin with spaces/tests/run-tests.sh", result.stdout)


if __name__ == "__main__":
    unittest.main()
