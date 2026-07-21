from pathlib import Path
import unittest

from ci_rescue.workflow import _job_blocks, _meaningful_lines, analyze_workflow


ROOT = Path(__file__).resolve().parents[1]


class WorkflowAnalysisTests(unittest.TestCase):
    @staticmethod
    def _codes(text):
        return [finding.code for finding in analyze_workflow(text).findings]

    def test_broken_example_reports_actionable_codes(self):
        text = (ROOT / "examples" / "broken-workflow.yml").read_text(encoding="utf-8")
        analysis = analyze_workflow(text, "broken")
        codes = {finding.code for finding in analysis.findings}

        self.assertTrue({"WF003", "WF021", "WF023", "WF030", "WF032", "WF040"} <= codes)
        self.assertEqual(analysis.stats["jobs"], 2)

    def test_fixed_example_has_no_findings(self):
        text = (ROOT / "examples" / "fixed-workflow.yml").read_text(encoding="utf-8")
        analysis = analyze_workflow(text, "fixed")

        self.assertEqual(analysis.findings, [])
        self.assertEqual(analysis.stats["jobs"], 2)

    def test_empty_workflow_is_error(self):
        analysis = analyze_workflow("  \n", "empty")

        self.assertEqual([item.code for item in analysis.findings], ["WF001"])

    def test_duplicate_top_level_key_is_reported(self):
        text = "on:\n  push:\njobs:\n  first:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: true\njobs:\n"
        analysis = analyze_workflow(text)

        self.assertIn("WF012", {item.code for item in analysis.findings})

    def test_quoted_mapping_keys_are_recognized(self):
        text = """"on":
  push:
"jobs":
  "build":
    "runs-on": ubuntu-latest
    "timeout-minutes": 5
    "steps":
      - run: true
"""

        self.assertEqual(self._codes(text), [])

    def test_empty_and_invalid_runner_values_are_errors(self):
        for value in ("", "''", "[]", "null", "false", "42", "[self-hosted"):
            with self.subTest(value=value):
                text = "on:\n  push:\njobs:\n  build:\n    runs-on: {0}\n    timeout-minutes: 5\n    steps:\n      - run: true\n".format(value)

                self.assertIn("WF025", self._codes(text))

    def test_runner_expressions_and_block_forms_are_preserved(self):
        text = """on:
  push:
jobs:
  matrix:
    runs-on: "${{ matrix.os }}"
    timeout-minutes: ${{ fromJSON(inputs.timeout) }}
    steps:
      - run: true
  group:
    runs-on:
      group: ubuntu-runners
      labels: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: true
  labels:
    runs-on:
      - self-hosted
      - linux
    timeout-minutes: 5
    steps:
      - run: true
"""

        codes = self._codes(text)
        self.assertNotIn("WF025", codes)
        self.assertNotIn("WF024", codes)

    def test_empty_steps_are_errors(self):
        values = {
            "blank": "steps:\n",
            "empty list": "steps: []\n",
            "null": "steps: null\n",
            "empty items": "steps:\n      - null\n      - {}\n",
        }
        for label, steps in values.items():
            with self.subTest(label=label):
                text = "on:\n  push:\njobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    {0}".format(steps)

                self.assertIn("WF026", self._codes(text))

    def test_non_sequence_step_scalars_are_errors(self):
        for value in ("false", "true", "42", "run-this", "'not a sequence'"):
            with self.subTest(value=value):
                text = "on:\n  push:\njobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps: {0}\n".format(value)

                self.assertIn("WF026", self._codes(text))

    def test_invalid_literal_timeout_values_are_errors(self):
        for value in ("", "0", "361", "-1", "1.5", "ten", "'10'"):
            with self.subTest(value=value):
                text = "on:\n  push:\njobs:\n  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: {0}\n    steps:\n      - run: true\n".format(value)

                self.assertIn("WF024", self._codes(text))

    def test_expression_check_ignores_comments_stray_closes_and_quoted_braces(self):
        text = """name: Expression examples
# An unmatched ${{ in a YAML comment is inert.
on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo "literal }} braces"
      - run: echo "${{ format('}}', github.ref) }}"
      - run: true # another inert ${{ comment
"""

        self.assertNotIn("WF003", self._codes(text))

    def test_quoted_action_references_are_checked_after_unquoting(self):
        text = """on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: "actions/checkout@main"
      - uses: 'example/action'
      - uses: "actions/setup-python@v5"
"""

        codes = self._codes(text)
        self.assertEqual(codes.count("WF032"), 1)
        self.assertEqual(codes.count("WF031"), 1)

    def test_script_text_and_nested_values_are_not_action_fields(self):
        text = """on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: |
          printf '%s\\n' 'uses: owner/repo@main'
          continue-on-error: true
      - run: true
        env:
          uses: owner/repo@main
          continue-on-error: true
"""

        codes = self._codes(text)
        self.assertNotIn("WF030", codes)
        self.assertNotIn("WF032", codes)

    def test_block_scalar_ends_before_sibling_step_fields(self):
        text = """on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: |
          echo true
          uses: owner/repo@main
        continue-on-error: true
"""

        codes = self._codes(text)
        self.assertEqual(codes.count("WF030"), 1)
        self.assertNotIn("WF032", codes)

    def test_block_list_needs_checks_each_job(self):
        text = """on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: true
  deploy:
    needs:
      - build
      - "missing_job"
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: true
"""

        findings = [finding for finding in analyze_workflow(text).findings if finding.code == "WF040"]
        self.assertEqual(len(findings), 1)
        self.assertIn("missing_job", findings[0].summary)

    def test_job_blocks_do_not_search_the_full_sequence_for_each_header(self):
        class NoIndexSequence:
            def __init__(self, values):
                self._values = values

            def __getitem__(self, position):
                return self._values[position]

            def __len__(self):
                return len(self._values)

            def index(self, *args, **kwargs):
                raise AssertionError("job parsing must not linearly search for known positions")

        text = """on:
  push:
jobs:
  alpha:
    uses: owner/repo/.github/workflows/alpha.yml@v1
  beta:
    uses: owner/repo/.github/workflows/beta.yml@v1
  gamma:
    uses: owner/repo/.github/workflows/gamma.yml@v1
name: boundary
"""

        jobs = _job_blocks(NoIndexSequence(_meaningful_lines(text)))

        self.assertEqual([job.name for job in jobs], ["alpha", "beta", "gamma"])
        self.assertEqual(
            [[line.content for line in job.block] for job in jobs],
            [
                ["uses: owner/repo/.github/workflows/alpha.yml@v1"],
                ["uses: owner/repo/.github/workflows/beta.yml@v1"],
                ["uses: owner/repo/.github/workflows/gamma.yml@v1"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
