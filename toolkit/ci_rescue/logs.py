"""Offline diagnosis of common GitHub Actions log signatures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Pattern, Sequence, Tuple

from .models import Analysis, Finding


@dataclass(frozen=True)
class _Signature:
    code: str
    severity: str
    title: str
    patterns: Sequence[Pattern[str]]
    summary: str
    remediation: str
    confidence: str = "high"


def _compiled(*patterns: str) -> Tuple[Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


SIGNATURES: Tuple[_Signature, ...] = (
    _Signature(
        "LOG101",
        "error",
        "Runner storage is exhausted",
        _compiled(r"no space left on device", r"enospc"),
        "A command could not write because the runner filesystem ran out of free space or inodes.",
        "Delete unneeded tool caches or build outputs before the failing step, reduce image layers, and measure free space with `df -h`.",
    ),
    _Signature(
        "LOG102",
        "error",
        "Process likely exceeded memory",
        _compiled(r"javascript heap out of memory", r"fatal process out of memory", r"killed process .* out of memory"),
        "The log explicitly reports that the process exhausted its memory allowance.",
        "Reduce parallelism or memory use, split the job, or select a runner with sufficient memory after measuring the peak.",
    ),
    _Signature(
        "LOG103",
        "error",
        "Command is missing from PATH",
        _compiled(r"command not found", r"process completed with exit code 127", r"is not recognized as an internal or external command"),
        "The shell could not locate a requested executable.",
        "Install the tool in an earlier step, use the correct setup action, and print the tool version before use.",
    ),
    _Signature(
        "LOG104",
        "error",
        "Operation was denied",
        _compiled(r"resource not accessible by integration", r"permission denied", r"http 403", r"status code: 403"),
        "The job reached an operation that the current runner process or workflow token is not allowed to perform.",
        "Identify the denied operation, then grant only the documented workflow permission or correct the local file ownership/mode as appropriate.",
        "medium",
    ),
    _Signature(
        "LOG105",
        "error",
        "npm lockfile is out of sync",
        _compiled(r"npm ci.*can only install", r"package\.json and .*lock.*not in sync"),
        "`npm ci` rejected dependency metadata because the committed lockfile and package manifest do not agree.",
        "Run the matching npm version locally, refresh the lockfile intentionally, commit it, and rerun `npm ci` before pushing.",
    ),
    _Signature(
        "LOG106",
        "error",
        "pytest collected no tests",
        _compiled(r"no tests ran", r"collected 0 items", r"pytest.*exit code 5"),
        "pytest found no matching tests; by default that condition exits with status 5.",
        "Check the test path, discovery naming, configuration, and conditional markers. Do not mask the exit unless an empty suite is intentional.",
        "medium",
    ),
    _Signature(
        "LOG107",
        "error",
        "Job or step timed out",
        _compiled(r"timed out after", r"exceeded the maximum execution time"),
        "The runner stopped waiting before the command completed.",
        "Find the slow step, add bounded retries only for transient work, remove deadlocks, and set a measured `timeout-minutes` value.",
        "medium",
    ),
    _Signature(
        "LOG108",
        "error",
        "Git rejected repository ownership",
        _compiled(r"detected dubious ownership"),
        "Git's repository ownership check does not trust the current workspace path.",
        "Correct the checkout ownership when possible; otherwise add only the exact workspace path to Git's `safe.directory` configuration.",
    ),
    _Signature(
        "LOG109",
        "error",
        "Action reference could not be resolved",
        _compiled(r"unable to resolve action", r"repository not found.*actions", r"can't find .*action\.yml", r"can't find .*action\.yaml"),
        "GitHub Actions could not fetch or load the referenced action and ref.",
        "Verify the owner, repository, path, and release ref. For a local action, ensure checkout runs first and the metadata file is committed.",
        "medium",
    ),
    _Signature(
        "LOG110",
        "error",
        "pnpm frozen lockfile check failed",
        _compiled(r"err_pnpm_outdated_lockfile", r"err_pnpm_broken_lockfile", r"pnpm.*frozen-lockfile.*cannot", r"pnpm.*lockfile is broken"),
        "pnpm determined that the lockfile does not match the project manifest or selected pnpm version.",
        "Use the repository's declared pnpm version, update the lockfile intentionally, commit it, and retry the frozen install locally.",
    ),
    _Signature(
        "LOG111",
        "error",
        "Script has incompatible line endings",
        _compiled(r"/bin/(?:ba)?sh\^m", r"bad interpreter:.*\^m", r"\$'\\r': command not found"),
        "A shell script appears to contain CRLF line endings on a Unix runner.",
        "Convert the script to LF and enforce the intended line ending with `.gitattributes`.",
    ),
    _Signature(
        "LOG112",
        "warning",
        "Artifact pattern matched no files",
        _compiled(r"no files were found with the provided path", r"no files found for artifact"),
        "The artifact upload step did not find output at the configured path.",
        "Confirm the producing step ran, inspect the runner working directory, and correct the artifact path or conditional.",
    ),
    _Signature(
        "LOG113",
        "error",
        "Docker registry pull was throttled",
        _compiled(r"toomanyrequests.*pull rate limit", r"docker hub.*rate limit", r"docker.*429 too many requests"),
        "The job exceeded a registry's anonymous or account pull allowance.",
        "Reduce repeated pulls, use GitHub's cache where appropriate, or use an approved authenticated mirror configured by the repository owner.",
        "medium",
    ),
)


def _line_matches(lines: Sequence[str], patterns: Sequence[Pattern[str]]) -> List[int]:
    return [
        number
        for number, line in enumerate(lines, start=1)
        if any(pattern.search(line) for pattern in patterns)
    ]


def _evidence(line_numbers: Sequence[int]) -> List[str]:
    visible = list(line_numbers[:8])
    suffix = "" if len(line_numbers) <= 8 else " (+{0} more)".format(len(line_numbers) - 8)
    return [
        "signature matched on line(s): {0}{1}; raw log text is not reproduced".format(
            ", ".join(map(str, visible)), suffix
        )
    ]


def analyze_logs(text: str, source: str = "<memory>") -> Analysis:
    """Match known failure signatures without sending or persisting the log."""

    lines = text.splitlines()
    findings: List[Finding] = []
    for signature in SIGNATURES:
        matched = _line_matches(lines, signature.patterns)
        if matched:
            findings.append(
                Finding(
                    signature.code,
                    signature.severity,
                    signature.title,
                    signature.summary,
                    signature.remediation,
                    _evidence(matched),
                    signature.confidence,
                )
            )

    # A warning should not hide a separate fatal marker. Conversely, once a
    # recognized error explains the failure, avoid adding a generic LOG199 for
    # the usual trailing exit-code line.
    has_recognized_error = any(finding.severity == "error" for finding in findings)
    if text.strip() and not has_recognized_error:
        exit_matches = _line_matches(
            lines,
            _compiled(
                r"process completed with exit code [1-9][0-9]*",
                r"##\[error\]",
                r"error:",
                r"npm err! code",
            ),
        )
        if exit_matches:
            findings.append(
                Finding(
                    "LOG199",
                    "info",
                    "Unclassified failure marker",
                    "The log contains a failure marker, but it does not match a high-confidence signature in this kit.",
                    "Start at the first failing command, reproduce that exact command locally, and inspect the first error rather than the final exit-code line.",
                    _evidence(exit_matches),
                    "low",
                )
            )

    return Analysis(
        "logs",
        source,
        findings,
        {"lines": len(lines), "characters": len(text)},
    )
