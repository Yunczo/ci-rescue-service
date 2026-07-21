"""Composite GitHub Action entry point for the offline CI Rescue analyzer."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


ACTION_ROOT = Path(os.environ.get("GITHUB_ACTION_PATH", Path(__file__).parents[1])).resolve()
WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
sys.path.insert(0, str(ACTION_ROOT / "toolkit"))

from ci_rescue.logs import analyze_logs  # noqa: E402
from ci_rescue.models import Analysis  # noqa: E402
from ci_rescue.render import render  # noqa: E402
from ci_rescue.workflow import analyze_workflow  # noqa: E402


SEVERITY_RANK = {"none": 0, "info": 1, "warning": 2, "error": 3}
MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_SUMMARY_BYTES = 900 * 1024
RESCUE_FOOTER = (
    "\n\n---\n\n"
    "### Still blocked?\n\n"
    "Fixed-scope repair: **$49 equivalent in Bitcoin** · scope reply within 24h · "
    "delivery within 48h after accepted payment and sanitized inputs.\n\n"
    "Review and redact this report, then send it with the first redacted failing excerpt. "
    "[Request a no-account scope review — no payment yet]"
    "(https://yunczo.github.io/ci-rescue-service/#anonymous-intake).\n"
)


def _workspace_path(value: str, label: str, *, must_exist: bool) -> Path:
    if "\n" in value or "\r" in value:
        raise ValueError(f"{label} cannot contain line breaks")
    if not value or Path(value).is_absolute():
        raise ValueError(f"{label} must be a non-empty repository-relative path")
    path = (WORKSPACE / value).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"{label} must stay inside the repository workspace")
    if must_exist and not path.is_file():
        raise ValueError(f"{label} does not name a readable file: {value}")
    return path


def _read(path: Path) -> str:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds the 10 MiB limit: {path.name}")
    return path.read_text(encoding="utf-8")


def _highest(analyses: Iterable[Analysis]) -> str:
    highest = "none"
    for analysis in analyses:
        for finding in analysis.findings:
            if SEVERITY_RANK.get(finding.severity, 0) > SEVERITY_RANK[highest]:
                highest = finding.severity
    return highest


def _append_line(path_value: str | None, line: str) -> None:
    if not path_value:
        return
    with Path(path_value).open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def _write_new_file(path: Path, content: str) -> None:
    """Create a report atomically without following or replacing an existing path."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o666)
    except FileExistsError as error:
        raise ValueError("report-path already exists; choose a new path") from error

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", errors="strict") as stream:
            descriptor = -1
            stream.write(content)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _summary_content(report: str, finding_count: int = 0) -> str:
    """Keep the job summary below GitHub's per-step upload limit."""
    footer = RESCUE_FOOTER if finding_count > 0 else ""
    complete = report + footer
    encoded = complete.encode("utf-8")
    if len(encoded) <= MAX_SUMMARY_BYTES:
        return complete
    notice = (
        "\n\n> Job summary truncated to stay below GitHub's upload limit. "
        "The complete Markdown report remains at the `report-path` output.\n"
    )
    available = MAX_SUMMARY_BYTES - len((notice + footer).encode("utf-8"))
    prefix = report.encode("utf-8")[:available].decode("utf-8", errors="ignore").rstrip()
    return prefix + notice + footer


def _workflow_command_value(value: str) -> str:
    """Escape data before placing it in a GitHub workflow command."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    fail_on = os.environ.get("CI_RESCUE_FAIL_ON", "none").strip().lower()
    if fail_on not in SEVERITY_RANK:
        raise ValueError("fail-on must be one of: none, info, warning, error")

    workflow_path = _workspace_path(
        os.environ.get("CI_RESCUE_WORKFLOW_PATH", ""),
        "workflow-path",
        must_exist=True,
    )
    log_value = os.environ.get("CI_RESCUE_LOG_PATH", "").strip()
    report_path = _workspace_path(
        os.environ.get("CI_RESCUE_REPORT_PATH", "ci-rescue-report.md"),
        "report-path",
        must_exist=False,
    )
    if not report_path.parent.is_dir():
        raise ValueError("report-path parent directory does not exist")

    analyses: list[tuple[str, Analysis]] = [
        ("Workflow", analyze_workflow(_read(workflow_path), workflow_path.name)),
    ]
    if log_value:
        log_path = _workspace_path(log_value, "log-path", must_exist=True)
        analyses.append(("Saved log", analyze_logs(_read(log_path), log_path.name)))

    sections = [
        "# CI Rescue action report",
        "",
        "Offline, read-only analysis. Reports exclude raw logs and full input files; source basenames, workflow identifiers, action references, and line numbers can appear when needed to explain a finding.",
    ]
    for title, analysis in analyses:
        sections.extend(("", f"## {title}", "", render(analysis, "markdown").strip()))
    report = "\n".join(sections).rstrip() + "\n"
    _write_new_file(report_path, report)

    finding_count = sum(len(analysis.findings) for _, analysis in analyses)
    highest = _highest(analysis for _, analysis in analyses)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(_summary_content(report, finding_count))

    _append_line(os.environ.get("GITHUB_OUTPUT"), f"report-path={report_path}")
    _append_line(os.environ.get("GITHUB_OUTPUT"), f"finding-count={finding_count}")
    _append_line(os.environ.get("GITHUB_OUTPUT"), f"highest-severity={highest}")
    print(f"CI Rescue wrote {report_path} with {finding_count} finding(s); highest severity: {highest}")

    if fail_on != "none" and SEVERITY_RANK[highest] >= SEVERITY_RANK[fail_on]:
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError) as error:
        print(
            f"::error title=CI Rescue input error::{_workflow_command_value(str(error))}",
            file=sys.stderr,
        )
        raise SystemExit(2)
