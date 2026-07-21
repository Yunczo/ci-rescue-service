"""Command-line entry point for CI Rescue Kit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .logs import analyze_logs
from .models import Analysis
from .render import render
from .workflow import analyze_workflow


MAX_INPUT_BYTES = 10 * 1024 * 1024
EXIT_RANK = {"info": 1, "warning": 2, "error": 3}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ci-rescue",
        description="Offline diagnostics for GitHub Actions workflow YAML and CI logs.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("workflow", "Check a GitHub Actions workflow YAML file"),
        ("logs", "Diagnose a saved or pasted GitHub Actions log"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument(
            "path",
            help="Input path, or - to read from standard input",
        )
        command.add_argument(
            "--format",
            choices=("text", "markdown", "json"),
            default="text",
            help="Report format (default: text)",
        )
        command.add_argument(
            "--output",
            metavar="PATH",
            help="Write the sanitized report to PATH instead of standard output",
        )
        command.add_argument(
            "--force",
            action="store_true",
            help="Replace an existing output file (never the input file)",
        )
        command.add_argument(
            "--fail-on",
            choices=("none", "info", "warning", "error"),
            default="none",
            help="Exit 1 when this severity or higher is found (default: none)",
        )
    return parser


def _read_input(path_value: str) -> tuple[str, str]:
    if path_value == "-":
        text = sys.stdin.read(MAX_INPUT_BYTES + 1)
        encoded_size = len(text.encode("utf-8"))
        if encoded_size > MAX_INPUT_BYTES:
            raise ValueError("standard input exceeds the 10 MiB safety limit")
        return text, "<stdin>"

    path = Path(path_value)
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 10 MiB safety limit")
    return path.read_text(encoding="utf-8"), path.name


def _write_report(input_path_value: str, output_path_value: str, report: str, force: bool) -> None:
    """Write a report without accidentally replacing the input or another file."""

    output_path = Path(output_path_value)
    input_identity = None
    if input_path_value != "-":
        input_stat = Path(input_path_value).stat()
        input_identity = (input_stat.st_dev, input_stat.st_ino)

    try:
        output_stat = output_path.stat()
        output_identity = (output_stat.st_dev, output_stat.st_ino)
    except FileNotFoundError:
        output_identity = None

    if input_identity is not None and output_identity == input_identity:
        raise ValueError("output path resolves to the input file")
    if not force and (output_identity is not None or output_path.is_symlink()):
        raise ValueError("output already exists; use --force to replace it")

    flags = os.O_WRONLY | os.O_CREAT
    if not force:
        flags |= os.O_EXCL
    try:
        descriptor = os.open(output_path, flags, 0o666)
    except FileExistsError as error:
        raise ValueError("output already exists; use --force to replace it") from error

    try:
        opened_stat = os.fstat(descriptor)
        opened_identity = (opened_stat.st_dev, opened_stat.st_ino)
        if input_identity is not None and opened_identity == input_identity:
            raise ValueError("output path resolves to the input file")
        if force:
            os.ftruncate(descriptor, 0)
            os.lseek(descriptor, 0, os.SEEK_SET)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(report)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _threshold_failed(analysis: Analysis, threshold: str) -> bool:
    if threshold == "none":
        return False
    minimum = EXIT_RANK[threshold]
    return any(EXIT_RANK.get(item.severity, 0) >= minimum for item in analysis.findings)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.force and not args.output:
            raise ValueError("--force requires --output")
        text, source = _read_input(args.path)
        if args.command == "workflow":
            analysis = analyze_workflow(text, source)
        else:
            analysis = analyze_logs(text, source)
        report = render(analysis, args.format)
        if args.output:
            _write_report(args.path, args.output, report, args.force)
        else:
            sys.stdout.write(report)
        return 1 if _threshold_failed(analysis, args.fail_on) else 0
    except (OSError, UnicodeError, ValueError) as error:
        print("ci-rescue: {0}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
