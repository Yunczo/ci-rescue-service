from pathlib import Path
import unittest

from ci_rescue.logs import analyze_logs


ROOT = Path(__file__).resolve().parents[1]


class LogAnalysisTests(unittest.TestCase):
    def test_npm_fixture_matches_lockfile_signature(self):
        text = (ROOT / "examples" / "npm-lockfile-failure.txt").read_text(encoding="utf-8")
        analysis = analyze_logs(text, "npm.log")

        self.assertEqual({item.code for item in analysis.findings}, {"LOG105"})

    def test_npm_eusage_alone_is_not_called_lockfile_drift(self):
        analysis = analyze_logs("npm ERR! code EUSAGE\nnpm ERR! Usage: npm publish <package>\n")

        codes = {item.code for item in analysis.findings}
        self.assertNotIn("LOG105", codes)
        self.assertIn("LOG199", codes)

    def test_exit_137_alone_is_not_called_out_of_memory(self):
        analysis = analyze_logs("Process completed with exit code 137\n")

        codes = {item.code for item in analysis.findings}
        self.assertNotIn("LOG102", codes)
        self.assertIn("LOG199", codes)

    def test_explicit_out_of_memory_message_still_matches(self):
        analysis = analyze_logs("FATAL ERROR: JavaScript heap out of memory\n")

        self.assertEqual({item.code for item in analysis.findings}, {"LOG102"})

    def test_cancellation_is_not_called_timeout(self):
        analysis = analyze_logs("The operation was canceled by the user.\n")

        self.assertNotIn("LOG107", {item.code for item in analysis.findings})

    def test_explicit_timeout_still_matches(self):
        analysis = analyze_logs("Command timed out after 300 seconds\n")

        self.assertEqual({item.code for item in analysis.findings}, {"LOG107"})

    def test_safe_directory_command_is_not_called_ownership_failure(self):
        analysis = analyze_logs("git config --global --add safe.directory /workspace\n")

        self.assertNotIn("LOG108", {item.code for item in analysis.findings})

    def test_dubious_ownership_message_still_matches(self):
        analysis = analyze_logs("fatal: detected dubious ownership in repository at '/workspace'\n")

        self.assertEqual({item.code for item in analysis.findings}, {"LOG108"})

    def test_generic_broken_lockfile_is_not_called_pnpm(self):
        analysis = analyze_logs("Cargo reported that its lockfile is broken\n")

        self.assertNotIn("LOG110", {item.code for item in analysis.findings})

    def test_explicit_pnpm_lockfile_error_still_matches(self):
        analysis = analyze_logs("ERR_PNPM_OUTDATED_LOCKFILE Cannot install with frozen-lockfile\n")

        self.assertEqual({item.code for item in analysis.findings}, {"LOG110"})

    def test_evidence_does_not_echo_log_content(self):
        marker = "PRIVATE_BUILD_VALUE"
        analysis = analyze_logs("{0}: command not found\n".format(marker))
        rendered_evidence = " ".join(
            evidence
            for finding in analysis.findings
            for evidence in finding.evidence
        )

        self.assertNotIn(marker, rendered_evidence)
        self.assertIn("line(s): 1", rendered_evidence)

    def test_unknown_error_gets_low_confidence_fallback(self):
        analysis = analyze_logs("Error: an unusual build tool failed\n")

        self.assertEqual([item.code for item in analysis.findings], ["LOG199"])
        self.assertEqual(analysis.findings[0].confidence, "low")

    def test_unknown_error_is_not_hidden_by_recognized_warning(self):
        analysis = analyze_logs(
            "No files were found with the provided path\n"
            "Process completed with exit code 2\n"
        )

        self.assertEqual({item.code for item in analysis.findings}, {"LOG112", "LOG199"})

    def test_generic_exit_line_does_not_duplicate_recognized_error(self):
        analysis = analyze_logs(
            "tool: command not found\n"
            "Error: Process completed with exit code 127\n"
        )

        self.assertEqual({item.code for item in analysis.findings}, {"LOG103"})

    def test_clean_log_has_no_findings(self):
        analysis = analyze_logs("Build complete\nAll tests passed\n")

        self.assertEqual(analysis.findings, [])

    def test_unrelated_exit_five_is_not_called_pytest(self):
        analysis = analyze_logs("Custom compiler stopped\nProcess completed with exit code 5\n")

        codes = {item.code for item in analysis.findings}
        self.assertNotIn("LOG106", codes)
        self.assertIn("LOG199", codes)

    def test_unrelated_http_429_is_not_called_docker(self):
        analysis = analyze_logs("API request failed: 429 Too Many Requests\n")

        self.assertNotIn("LOG113", {item.code for item in analysis.findings})


if __name__ == "__main__":
    unittest.main()
