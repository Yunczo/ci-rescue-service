"""Stable human- and machine-readable report rendering."""

from __future__ import annotations

import json
import re
import string
from typing import List

from .models import Analysis, Finding


_MARKDOWN_PUNCTUATION = frozenset(string.punctuation)


def _markdown_text(value: str) -> str:
    """Render arbitrary analyzer data as inert Markdown text."""
    return "".join(
        "\\" + character if character in _MARKDOWN_PUNCTUATION else character
        for character in value
    )


def _markdown_code(value: str) -> str:
    """Wrap arbitrary text in a Markdown code span with a safe delimiter."""
    runs = re.findall(r"`+", value)
    delimiter = "`" * (max((len(run) for run in runs), default=0) + 1)
    content = value
    if value.startswith((" ", "`")) or value.endswith((" ", "`")):
        content = " " + value + " "
    return delimiter + content + delimiter


def _finding_text(finding: Finding) -> List[str]:
    lines = [
        "[{0}] {1} {2}".format(finding.severity.upper(), finding.code, finding.title),
        "  Cause: {0}".format(finding.summary),
        "  Next:  {0}".format(finding.remediation),
        "  Confidence: {0}".format(finding.confidence),
    ]
    lines.extend("  Evidence: {0}".format(item) for item in finding.evidence)
    return lines


def render_text(analysis: Analysis) -> str:
    counts = analysis.counts()
    lines = [
        "CI Rescue Kit 1.0.0",
        "Input: {0} ({1})".format(analysis.source, analysis.kind),
        "Findings: {0} error, {1} warning, {2} info".format(
            counts["error"], counts["warning"], counts["info"]
        ),
    ]
    if not analysis.findings:
        lines.extend(["", "No recognized issues found. This is not proof that the workflow will run successfully."])
    else:
        for finding in analysis.sorted_findings():
            lines.append("")
            lines.extend(_finding_text(finding))
    return "\n".join(lines) + "\n"


def render_markdown(analysis: Analysis) -> str:
    counts = analysis.counts()
    lines = [
        "# CI Rescue Kit report",
        "",
        "- Input: {0}".format(_markdown_code(analysis.source)),
        "- Analyzer: {0}".format(_markdown_code(analysis.kind)),
        "- Findings: {0} error, {1} warning, {2} info".format(
            counts["error"], counts["warning"], counts["info"]
        ),
    ]
    if not analysis.findings:
        lines.extend(["", "No recognized issues found. This is not proof that the workflow will run successfully."])
    else:
        for finding in analysis.sorted_findings():
            lines.extend(
                [
                    "",
                    "## {0} · {1} · {2}".format(
                        _markdown_text(finding.code),
                        _markdown_text(finding.severity.upper()),
                        _markdown_text(finding.title),
                    ),
                    "",
                    _markdown_text(finding.summary),
                    "",
                    "**Recommended next step:** {0}".format(
                        _markdown_text(finding.remediation)
                    ),
                    "",
                    "**Confidence:** {0}".format(_markdown_text(finding.confidence)),
                ]
            )
            if finding.evidence:
                lines.extend(["", "**Evidence**"])
                lines.extend("- {0}".format(_markdown_text(item)) for item in finding.evidence)
    lines.extend(
        [
            "",
            "---",
            "Generated locally by CI Rescue Kit 1.0.0. Raw logs and full input files are not included; source basenames, workflow identifiers, action references, and line numbers can appear when needed to explain a finding.",
        ]
    )
    return "\n".join(lines) + "\n"


def render(analysis: Analysis, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(analysis.to_dict(), indent=2, sort_keys=True) + "\n"
    if output_format == "markdown":
        return render_markdown(analysis)
    return render_text(analysis)
