from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY = Path(__file__).parents[2]
os.environ.setdefault("GITHUB_ACTION_PATH", str(REPOSITORY))
SPEC = importlib.util.spec_from_file_location(
    "ci_rescue_action_entrypoint", REPOSITORY / "action" / "entrypoint.py"
)
assert SPEC and SPEC.loader
entrypoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entrypoint)


class ActionEntrypointTests(unittest.TestCase):
    def test_workflow_command_data_is_escaped(self) -> None:
        self.assertEqual(
            entrypoint._workflow_command_value("bad%value\r\nnext"),
            "bad%25value%0D%0Anext",
        )

    def test_repository_paths_reject_line_breaks(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot contain line breaks"):
            entrypoint._workspace_path("report.md\nforged=value", "report-path", must_exist=False)

    def test_report_creation_never_replaces_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.md"
            report_path.write_text("keep me", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "already exists"):
                entrypoint._write_new_file(report_path, "replacement")

            self.assertEqual(report_path.read_text(encoding="utf-8"), "keep me")

    def test_large_job_summary_is_truncated_below_the_upload_limit(self) -> None:
        report = "é" * entrypoint.MAX_SUMMARY_BYTES

        summary = entrypoint._summary_content(report, finding_count=1)

        self.assertLessEqual(len(summary.encode("utf-8")), entrypoint.MAX_SUMMARY_BYTES)
        self.assertIn("Job summary truncated", summary)
        self.assertIn("Request a no-account scope review", summary)
        self.assertNotEqual(summary, report)

    def test_main_writes_report_summary_and_outputs(self) -> None:
        workflow = (REPOSITORY / "toolkit" / "examples" / "fixed-workflow.yml").read_text(
            encoding="utf-8"
        )
        original_workspace = entrypoint.WORKSPACE
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                workspace = Path(temporary_directory).resolve()
                (workspace / "workflow.yml").write_text(workflow, encoding="utf-8")
                entrypoint.WORKSPACE = workspace
                environment = {
                    "CI_RESCUE_WORKFLOW_PATH": "workflow.yml",
                    "CI_RESCUE_LOG_PATH": "",
                    "CI_RESCUE_REPORT_PATH": "report.md",
                    "CI_RESCUE_FAIL_ON": "none",
                    "GITHUB_OUTPUT": str(workspace / "outputs.txt"),
                    "GITHUB_STEP_SUMMARY": str(workspace / "summary.md"),
                }
                with patch.dict(os.environ, environment, clear=False):
                    self.assertEqual(entrypoint.main(), 0)

                report = (workspace / "report.md").read_text(encoding="utf-8")
                summary = (workspace / "summary.md").read_text(encoding="utf-8")
                outputs = (workspace / "outputs.txt").read_text(encoding="utf-8")
                self.assertIn("# CI Rescue action report", report)
                self.assertEqual(report, summary)
                self.assertIn("finding-count=0", outputs)
                self.assertIn("highest-severity=none", outputs)
        finally:
            entrypoint.WORKSPACE = original_workspace

    def test_fail_threshold_returns_failure_after_writing_report(self) -> None:
        workflow = (REPOSITORY / "toolkit" / "examples" / "broken-workflow.yml").read_text(
            encoding="utf-8"
        )
        original_workspace = entrypoint.WORKSPACE
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                workspace = Path(temporary_directory).resolve()
                (workspace / "workflow.yml").write_text(workflow, encoding="utf-8")
                entrypoint.WORKSPACE = workspace
                environment = {
                    "CI_RESCUE_WORKFLOW_PATH": "workflow.yml",
                    "CI_RESCUE_LOG_PATH": "",
                    "CI_RESCUE_REPORT_PATH": "report.md",
                    "CI_RESCUE_FAIL_ON": "error",
                    "GITHUB_OUTPUT": str(workspace / "outputs.txt"),
                    "GITHUB_STEP_SUMMARY": str(workspace / "summary.md"),
                }
                with patch.dict(os.environ, environment, clear=False):
                    self.assertEqual(entrypoint.main(), 1)

                self.assertTrue((workspace / "report.md").is_file())
                report = (workspace / "report.md").read_text(encoding="utf-8")
                summary = (workspace / "summary.md").read_text(encoding="utf-8")
                self.assertNotIn("Request a no-account scope review", report)
                self.assertIn("Request a no-account scope review", summary)
                self.assertIn("Review and redact this report", summary)
                self.assertIn("no payment yet", summary)
                outputs = (workspace / "outputs.txt").read_text(encoding="utf-8")
                self.assertIn("highest-severity=error", outputs)
        finally:
            entrypoint.WORKSPACE = original_workspace


if __name__ == "__main__":
    unittest.main()
