import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ci_rescue.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_json_output_is_machine_readable(self):
        output = io.StringIO()
        with patch("sys.stdout", output):
            status = main(
                [
                    "workflow",
                    str(ROOT / "examples" / "fixed-workflow.yml"),
                    "--format",
                    "json",
                ]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["kind"], "workflow")
        self.assertEqual(payload["summary"]["error"], 0)

    def test_stdin_log_and_fail_threshold(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("command not found\n")), patch("sys.stdout", output):
            status = main(["logs", "-", "--fail-on", "error"])

        self.assertEqual(status, 1)
        self.assertIn("LOG103", output.getvalue())
        self.assertIn("Input: <stdin>", output.getvalue())

    def test_report_can_be_written_to_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.md"
            status = main(
                [
                    "logs",
                    str(ROOT / "examples" / "npm-lockfile-failure.txt"),
                    "--format",
                    "markdown",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(status, 0)
            self.assertIn("# CI Rescue Kit report", output_path.read_text(encoding="utf-8"))

    def test_output_cannot_replace_input_even_with_force(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "failure.log"
            original = "command not found\n"
            input_path.write_text(original, encoding="utf-8")
            error = io.StringIO()

            with patch("sys.stderr", error):
                status = main(
                    [
                        "logs",
                        str(input_path),
                        "--output",
                        str(input_path),
                        "--force",
                    ]
                )

            self.assertEqual(status, 2)
            self.assertEqual(input_path.read_text(encoding="utf-8"), original)
            self.assertIn("input file", error.getvalue())

    def test_hard_link_to_input_is_rejected_even_with_force(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "failure.log"
            output_path = Path(directory) / "report.txt"
            original = "command not found\n"
            input_path.write_text(original, encoding="utf-8")
            try:
                os.link(input_path, output_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest("hard links are unavailable: {0}".format(error))

            error = io.StringIO()
            with patch("sys.stderr", error):
                status = main(
                    [
                        "logs",
                        str(input_path),
                        "--output",
                        str(output_path),
                        "--force",
                    ]
                )

            self.assertEqual(status, 2)
            self.assertEqual(input_path.read_text(encoding="utf-8"), original)
            self.assertEqual(output_path.read_text(encoding="utf-8"), original)
            self.assertIn("input file", error.getvalue())

    def test_existing_output_requires_force(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "failure.log"
            output_path = Path(directory) / "report.txt"
            input_path.write_text("command not found\n", encoding="utf-8")
            output_path.write_text("KEEP ME\n", encoding="utf-8")
            error = io.StringIO()

            with patch("sys.stderr", error):
                refused_status = main(
                    ["logs", str(input_path), "--output", str(output_path)]
                )

            self.assertEqual(refused_status, 2)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "KEEP ME\n")
            self.assertIn("--force", error.getvalue())

            forced_status = main(
                [
                    "logs",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--force",
                ]
            )

            self.assertEqual(forced_status, 0)
            self.assertIn("LOG103", output_path.read_text(encoding="utf-8"))

    def test_source_path_is_redacted_in_every_report_format(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "private" / "project"
            nested.mkdir(parents=True)
            input_path = nested / "failure.log"
            input_path.write_text("command not found\n", encoding="utf-8")

            for output_format in ("text", "markdown", "json"):
                with self.subTest(output_format=output_format):
                    output = io.StringIO()
                    with patch("sys.stdout", output):
                        status = main(
                            [
                                "logs",
                                str(input_path),
                                "--format",
                                output_format,
                            ]
                        )

                    report = output.getvalue()
                    self.assertEqual(status, 0)
                    self.assertNotIn(str(nested), report)
                    if output_format == "json":
                        self.assertEqual(json.loads(report)["source"], "failure.log")
                    else:
                        self.assertIn("failure.log", report)


if __name__ == "__main__":
    unittest.main()
