"""Conservative, dependency-free checks for GitHub Actions workflow YAML.

This is intentionally not a general YAML parser. It recognizes the structural
subset used by GitHub Actions and only reports conditions it can explain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import Analysis, Finding


_MAPPING_RE = re.compile(
    r"^(?P<indent> *)(?:(?P<quote>['\"])(?P<quoted_key>[A-Za-z_][A-Za-z0-9_-]*)(?P=quote)|"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_-]*)):(?P<value>.*)$"
)
_USES_RE = re.compile(r"^\s*-?\s*uses\s*:(?P<value>.*)$", re.IGNORECASE)
_CONTINUE_RE = re.compile(r"^\s*continue-on-error\s*:\s*true\s*(?:#.*)?$", re.IGNORECASE)
_EXPRESSION_OPEN = "${{"
_EXPRESSION_CLOSE = "}}"


@dataclass(frozen=True)
class _Line:
    number: int
    raw: str
    indent: int
    content: str


@dataclass(frozen=True)
class _Job:
    name: str
    line: int
    indent: int
    block: Sequence[_Line]


def _mapping_key(match: re.Match[str]) -> str:
    """Return an allowed mapping key with optional YAML quotes removed."""

    return match.group("key") or match.group("quoted_key")


def _meaningful_lines(text: str) -> List[_Line]:
    result: List[_Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        expanded = raw.rstrip()
        content = expanded.lstrip(" ")
        if not content or content.startswith("#"):
            continue
        result.append(_Line(number, raw, len(expanded) - len(content), content))
    return result


def _top_level(lines: Iterable[_Line]) -> List[Tuple[str, _Line]]:
    found: List[Tuple[str, _Line]] = []
    for line in lines:
        match = _MAPPING_RE.match(line.raw.rstrip())
        if match and len(match.group("indent")) == 0:
            found.append((_mapping_key(match), line))
    return found


def _job_blocks(lines: Sequence[_Line]) -> List[_Job]:
    jobs_index: Optional[int] = None
    jobs_indent = 0
    for index, line in enumerate(lines):
        match = _MAPPING_RE.match(line.raw.rstrip())
        if line.indent == 0 and match and _mapping_key(match) == "jobs":
            jobs_index = index
            jobs_indent = line.indent
            break
    if jobs_index is None:
        return []

    candidates: List[Tuple[int, _Line]] = []
    for position in range(jobs_index + 1, len(lines)):
        line = lines[position]
        if line.indent <= jobs_indent:
            break
        match = _MAPPING_RE.match(line.raw.rstrip())
        if match and not line.content.startswith("-"):
            candidates.append((position, line))
    if not candidates:
        return []

    job_indent = min(line.indent for _, line in candidates)
    headers = [
        (position, line)
        for position, line in candidates
        if line.indent == job_indent and _MAPPING_RE.match(line.raw.rstrip())
    ]
    jobs: List[_Job] = []
    for header_index, (header_position, header) in enumerate(headers):
        next_position = len(lines)
        if header_index + 1 < len(headers):
            next_position = headers[header_index + 1][0]
        else:
            for index in range(header_position + 1, len(lines)):
                if lines[index].indent <= jobs_indent:
                    next_position = index
                    break
        name_match = _MAPPING_RE.match(header.raw.rstrip())
        if name_match:
            jobs.append(
                _Job(
                    name=_mapping_key(name_match),
                    line=header.number,
                    indent=header.indent,
                    block=lines[header_position + 1 : next_position],
                )
            )
    return jobs


def _immediate_fields(job: _Job) -> Dict[str, List[_Line]]:
    mapping_lines = [
        line
        for line in job.block
        if _MAPPING_RE.match(line.raw.rstrip()) and not line.content.startswith("-")
    ]
    if not mapping_lines:
        return {}
    field_indent = min(line.indent for line in mapping_lines)
    fields: Dict[str, List[_Line]] = {}
    for line in mapping_lines:
        if line.indent != field_indent:
            continue
        match = _MAPPING_RE.match(line.raw.rstrip())
        if match:
            fields.setdefault(_mapping_key(match), []).append(line)
    return fields


def _strip_yaml_comment(value: str) -> str:
    """Remove a YAML comment while preserving hashes inside quoted scalars."""

    single_quoted = False
    double_quoted = False
    escaped = False
    index = 0
    while index < len(value):
        character = value[index]
        if double_quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                double_quoted = False
        elif single_quoted:
            if character == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 1
                else:
                    single_quoted = False
        elif character == "'":
            single_quoted = True
        elif character == '"':
            double_quoted = True
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        index += 1
    return value.rstrip()


def _scalar_parts(value: str) -> Tuple[str, bool]:
    """Return a comment-free scalar and whether YAML quotes surrounded it."""

    value = _strip_yaml_comment(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        scalar = value[1:-1]
        if value[0] == "'":
            scalar = scalar.replace("''", "'")
        return scalar, True
    return value, False


def _mapping_match_for_line(line: _Line) -> Optional[re.Match[str]]:
    """Match a normal mapping or the mapping that starts a sequence item."""

    raw = line.raw.rstrip()
    if line.content.startswith("-"):
        raw = " " * line.indent + line.content[1:].lstrip()
    return _MAPPING_RE.match(raw)


def _block_scalar_content_numbers(lines: Sequence[_Line]) -> set[int]:
    """Return lines that are data inside YAML literal or folded block scalars."""

    result: set[int] = set()
    scalar_indent: Optional[int] = None
    for line in lines:
        if scalar_indent is not None:
            if line.indent > scalar_indent:
                result.add(line.number)
                continue
            scalar_indent = None

        match = _mapping_match_for_line(line)
        if not match:
            continue
        value = _strip_yaml_comment(match.group("value")).strip()
        if re.fullmatch(r"[|>](?:[1-9][+-]?|[+-][1-9]?)?", value):
            if line.content.startswith("-"):
                after_dash = line.content[1:]
                key_offset = len(after_dash) - len(after_dash.lstrip())
                scalar_indent = line.indent + 1 + key_offset
            else:
                scalar_indent = line.indent
    return result


def _mapping_value(line: _Line) -> str:
    match = _MAPPING_RE.match(line.raw.rstrip())
    return match.group("value") if match else ""


def _field_block(job: _Job, field: _Line) -> List[_Line]:
    """Return meaningful lines nested under one immediate job field."""

    result: List[_Line] = []
    found = False
    for line in job.block:
        if line.number == field.number:
            found = True
            continue
        if not found:
            continue
        if line.indent <= field.indent:
            break
        result.append(line)
    return result


def _step_fields(job: _Job, steps_field: _Line) -> Dict[str, List[_Line]]:
    """Return only actual immediate fields from each block-sequence step."""

    scalar_content = _block_scalar_content_numbers(job.block)
    block = [
        line
        for line in _field_block(job, steps_field)
        if line.number not in scalar_content
    ]
    if not block:
        return {}

    item_indents = [
        line.indent for line in block if line.content.lstrip().startswith("-")
    ]
    if not item_indents:
        return {}
    item_indent = min(item_indents)
    positions = [
        index
        for index, line in enumerate(block)
        if line.indent == item_indent and line.content.lstrip().startswith("-")
    ]

    fields: Dict[str, List[_Line]] = {}
    for item_index, position in enumerate(positions):
        end = positions[item_index + 1] if item_index + 1 < len(positions) else len(block)
        item_lines = block[position:end]
        header = item_lines[0]
        header_match = _mapping_match_for_line(header)
        if header_match:
            normalized = _Line(
                header.number,
                " " * header.indent + header.content[1:].lstrip(),
                header.indent,
                header.content[1:].lstrip(),
            )
            fields.setdefault(_mapping_key(header_match), []).append(normalized)

        nested = [
            line
            for line in item_lines[1:]
            if _MAPPING_RE.match(line.raw.rstrip()) and not line.content.startswith("-")
        ]
        if not nested:
            continue
        field_indent = min(line.indent for line in nested)
        for line in nested:
            if line.indent != field_indent:
                continue
            match = _MAPPING_RE.match(line.raw.rstrip())
            if match:
                fields.setdefault(_mapping_key(match), []).append(line)
    return fields


def _runner_value_has_content(value: str) -> bool:
    """Recognize a non-empty runner scalar/list/map without fully parsing YAML."""

    value = _strip_yaml_comment(value).strip()
    if _EXPRESSION_OPEN in value:
        return True
    scalar, quoted = _scalar_parts(value)
    if not scalar:
        return False
    if quoted:
        return True

    compact = re.sub(r"\s+", "", scalar)
    if compact in {"[]", "{}"} or scalar.lower() in {"null", "~", "true", "false"}:
        return False
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", scalar):
        return False

    if scalar.startswith("[") or scalar.endswith("]"):
        if not (scalar.startswith("[") and scalar.endswith("]")):
            return False
        return any(_runner_value_has_content(item) for item in scalar[1:-1].split(","))
    if scalar.startswith("{") or scalar.endswith("}"):
        return scalar.startswith("{") and scalar.endswith("}") and bool(scalar[1:-1].strip())
    return True


def _runs_on_problem(job: _Job, field: _Line) -> Optional[str]:
    value = _mapping_value(field)
    if _strip_yaml_comment(value).strip():
        if _runner_value_has_content(value):
            return None
        return "the value is empty or is not a runner label, expression, list, or group mapping"

    block = _field_block(job, field)
    for line in block:
        content = _strip_yaml_comment(line.content).strip()
        if content.startswith("-"):
            candidate = content[1:].strip()
        else:
            match = _MAPPING_RE.match(line.raw.rstrip())
            candidate = match.group("value") if match else content
        if _runner_value_has_content(candidate):
            return None
    return "the field has no non-empty runner labels or group values"


def _steps_problem(job: _Job, field: _Line) -> Optional[str]:
    value = _strip_yaml_comment(_mapping_value(field)).strip()
    if value:
        scalar, quoted = _scalar_parts(value)
        if not scalar or re.sub(r"\s+", "", scalar).lower() in {"[]", "{}", "null", "~"}:
            return "the inline `steps` value is empty"
        if _EXPRESSION_OPEN in scalar or (not quoted and scalar.startswith("*")):
            return None
        if scalar.startswith("[") and not scalar.endswith("]"):
            return "the inline `steps` sequence is not closed"
        if scalar.startswith("[") and scalar.endswith("]"):
            return None
        if not quoted and scalar.startswith("&"):
            # A YAML anchor can prefix a block sequence. Inspect the block below.
            value = ""
        else:
            return "the inline `steps` value is not a sequence"

    block = _field_block(job, field)
    if not block:
        return "the `steps` field has no sequence items"

    direct_indent = min(line.indent for line in block)
    item_positions = [
        index
        for index, line in enumerate(block)
        if line.indent == direct_indent and _strip_yaml_comment(line.content).lstrip().startswith("-")
    ]
    for item_index, position in enumerate(item_positions):
        line = block[position]
        item = _strip_yaml_comment(line.content).lstrip()[1:].strip()
        scalar, _ = _scalar_parts(item)
        if scalar and re.sub(r"\s+", "", scalar).lower() not in {"{}", "null", "~"}:
            return None
        next_position = item_positions[item_index + 1] if item_index + 1 < len(item_positions) else len(block)
        if any(nested.indent > line.indent for nested in block[position + 1 : next_position]):
            return None
    return "the `steps` field has no non-empty sequence items"


def _timeout_problem(field: _Line) -> Optional[str]:
    value = _strip_yaml_comment(_mapping_value(field)).strip()
    if _EXPRESSION_OPEN in value:
        return None
    scalar, quoted = _scalar_parts(value)
    if not scalar:
        return "the value is empty"
    if quoted:
        return "the value is a quoted string rather than a whole number"
    if not re.fullmatch(r"\d+", scalar):
        return "the value is not a whole number"
    if not 1 <= int(scalar) <= 360:
        return "the value is outside GitHub's supported range of 1 through 360"
    return None


def _unclosed_expression_lines(text: str) -> List[int]:
    """Find expressions left open, ignoring YAML comments and quoted braces inside them."""

    expression_line: Optional[int] = None
    expression_quote: Optional[str] = None
    expression_escaped = False

    for line_number, raw in enumerate(text.splitlines(), start=1):
        yaml_single_quoted = False
        yaml_double_quoted = False
        yaml_escaped = False
        index = 0
        while index < len(raw):
            if expression_line is not None:
                character = raw[index]
                if expression_quote == '"':
                    if expression_escaped:
                        expression_escaped = False
                    elif character == "\\":
                        expression_escaped = True
                    elif character == '"':
                        expression_quote = None
                elif expression_quote == "'":
                    if character == "'":
                        if index + 1 < len(raw) and raw[index + 1] == "'":
                            index += 1
                        else:
                            expression_quote = None
                elif character in {"'", '"'}:
                    expression_quote = character
                elif raw.startswith(_EXPRESSION_CLOSE, index):
                    expression_line = None
                    index += len(_EXPRESSION_CLOSE)
                    continue
                index += 1
                continue

            character = raw[index]
            if character == "#" and not yaml_single_quoted and not yaml_double_quoted and (
                index == 0 or raw[index - 1].isspace()
            ):
                break
            if raw.startswith(_EXPRESSION_OPEN, index):
                expression_line = line_number
                expression_quote = None
                expression_escaped = False
                index += len(_EXPRESSION_OPEN)
                continue
            if yaml_double_quoted:
                if yaml_escaped:
                    yaml_escaped = False
                elif character == "\\":
                    yaml_escaped = True
                elif character == '"':
                    yaml_double_quoted = False
            elif yaml_single_quoted:
                if character == "'":
                    if index + 1 < len(raw) and raw[index + 1] == "'":
                        index += 1
                    else:
                        yaml_single_quoted = False
            elif character == "'":
                yaml_single_quoted = True
            elif character == '"':
                yaml_double_quoted = True
            index += 1

    return [expression_line] if expression_line is not None else []


def _parse_needs(value: str, block: Sequence[_Line] = ()) -> List[str]:
    value = _strip_yaml_comment(value).strip()
    if _EXPRESSION_OPEN in value:
        return []
    if value:
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
            candidates = value.split(",")
        else:
            candidates = [value]
    else:
        if not block:
            return []
        direct_indent = min(line.indent for line in block)
        candidates = []
        for line in block:
            content = _strip_yaml_comment(line.content).strip()
            if line.indent == direct_indent and content.startswith("-"):
                candidates.append(content[1:].strip())

    result: List[str] = []
    for candidate in candidates:
        candidate, _ = _scalar_parts(candidate)
        if candidate and _EXPRESSION_OPEN not in candidate:
            result.append(candidate)
    return result


def analyze_workflow(text: str, source: str = "<memory>") -> Analysis:
    """Analyze workflow text without network access or third-party packages."""

    lines = _meaningful_lines(text)
    findings: List[Finding] = []

    if not text.strip():
        findings.append(
            Finding(
                "WF001",
                "error",
                "Workflow is empty",
                "GitHub Actions cannot load an empty workflow file.",
                "Add a workflow name, one or more triggers under `on`, and at least one job.",
                ["input contains no non-whitespace content"],
            )
        )
        return Analysis("workflow", source, findings, {"lines": 0, "jobs": 0})

    tab_lines = [str(index) for index, raw in enumerate(text.splitlines(), 1) if raw.startswith("\t") or re.match(r"^ +\t", raw)]
    if tab_lines:
        findings.append(
            Finding(
                "WF002",
                "error",
                "Tab used for indentation",
                "YAML indentation must use spaces; tabs commonly prevent the workflow from loading.",
                "Replace leading tabs with spaces and keep indentation consistent.",
                ["leading tab on line(s): " + ", ".join(tab_lines)],
            )
        )

    unclosed_expression_lines = _unclosed_expression_lines(text)
    if unclosed_expression_lines:
        findings.append(
            Finding(
                "WF003",
                "error",
                "Unbalanced GitHub expression",
                "A `${{` expression is not followed by a matching `}}` delimiter.",
                "Close the incomplete expression or remove the unmatched delimiter.",
                ["unclosed expression begins on line {0}".format(unclosed_expression_lines[0])],
            )
        )

    top = _top_level(lines)
    top_keys = [key for key, _ in top]
    for required in ("on", "jobs"):
        if required not in top_keys:
            findings.append(
                Finding(
                    "WF010" if required == "on" else "WF011",
                    "error",
                    "Missing top-level `{0}` key".format(required),
                    "A GitHub Actions workflow requires a top-level `{0}` mapping.".format(required),
                    "Add `{0}:` at the root of the workflow.".format(required),
                    ["top-level keys found: " + (", ".join(top_keys) or "none")],
                )
            )

    for key in sorted(set(top_keys)):
        occurrences = [line.number for found_key, line in top if found_key == key]
        if len(occurrences) > 1:
            findings.append(
                Finding(
                    "WF012",
                    "error",
                    "Duplicate top-level key",
                    "YAML loaders can silently replace an earlier `{0}` block with a later one.".format(key),
                    "Merge the duplicate `{0}` blocks into one mapping.".format(key),
                    ["`{0}` appears on lines: {1}".format(key, ", ".join(map(str, occurrences)))],
                )
            )

    jobs = _job_blocks(lines)
    if "jobs" in top_keys and not jobs:
        findings.append(
            Finding(
                "WF020",
                "error",
                "No jobs detected",
                "The `jobs` mapping does not contain a recognizable job definition.",
                "Add at least one job ID below `jobs:` and give it `runs-on` plus `steps`, or a reusable-workflow `uses` field.",
                ["recognized jobs: 0"],
            )
        )

    job_names = {job.name for job in jobs}
    for job in jobs:
        fields = _immediate_fields(job)
        if "runs-on" not in fields and "uses" not in fields:
            findings.append(
                Finding(
                    "WF021",
                    "error",
                    "Job has no runner or reusable workflow",
                    "Job `{0}` has neither `runs-on` nor a job-level `uses` field.".format(job.name),
                    "Add `runs-on` and `steps`, or call a reusable workflow with job-level `uses`.",
                    ["job `{0}` begins on line {1}".format(job.name, job.line)],
                )
            )
        for line in fields.get("runs-on", []):
            problem = _runs_on_problem(job, line)
            if problem:
                findings.append(
                    Finding(
                        "WF025",
                        "error",
                        "Job has an invalid runner",
                        "Job `{0}` has an invalid `runs-on` field: {1}.".format(job.name, problem),
                        "Set `runs-on` to a runner label, a non-empty label list, a runner group mapping, or a GitHub expression.",
                        ["line {0}".format(line.number)],
                    )
                )
        if "runs-on" in fields and "steps" not in fields:
            findings.append(
                Finding(
                    "WF022",
                    "warning",
                    "Runner job has no steps",
                    "Job `{0}` declares a runner but no `steps` mapping was detected.".format(job.name),
                    "Add at least one step or convert the job to a reusable-workflow call.",
                    ["job `{0}` begins on line {1}".format(job.name, job.line)],
                )
            )
        for line in fields.get("steps", []):
            problem = _steps_problem(job, line)
            if problem:
                findings.append(
                    Finding(
                        "WF026",
                        "error",
                        "Runner job has empty steps",
                        "Job `{0}` cannot run because {1}.".format(job.name, problem),
                        "Add at least one `run` or `uses` step below `steps`.",
                        ["line {0}".format(line.number)],
                    )
                )
        if "runs-on" in fields and "timeout-minutes" not in fields:
            findings.append(
                Finding(
                    "WF023",
                    "warning",
                    "Job has no explicit timeout",
                    "Job `{0}` can consume runner time until GitHub's platform limit.".format(job.name),
                    "Set a realistic `timeout-minutes` value for this job.",
                    ["job `{0}` begins on line {1}".format(job.name, job.line)],
                )
            )

        for line in fields.get("timeout-minutes", []):
            problem = _timeout_problem(line)
            if problem:
                findings.append(
                    Finding(
                        "WF024",
                        "error",
                        "Invalid timeout value",
                        "Job `{0}` has an invalid `timeout-minutes` field: {1}.".format(job.name, problem),
                        "Use a whole number from 1 through 360, or a GitHub expression that evaluates to one.",
                        ["line {0}".format(line.number)],
                    )
                )

        nested_step_fields: Dict[str, List[_Line]] = {}
        for steps_field in fields.get("steps", []):
            for key, found_lines in _step_fields(job, steps_field).items():
                nested_step_fields.setdefault(key, []).extend(found_lines)

        continue_lines = list(fields.get("continue-on-error", []))
        continue_lines.extend(nested_step_fields.get("continue-on-error", []))
        for line in continue_lines:
            if _CONTINUE_RE.match(line.raw):
                findings.append(
                    Finding(
                        "WF030",
                        "warning",
                        "Failure is explicitly ignored",
                        "`continue-on-error: true` can make a broken command look successful.",
                        "Keep it only when the failure is expected, and add a later step that records or validates the outcome.",
                        ["job `{0}`, line {1}".format(job.name, line.number)],
                    )
                )

        uses_lines = list(fields.get("uses", []))
        uses_lines.extend(nested_step_fields.get("uses", []))
        for line in uses_lines:
            uses_match = _USES_RE.match(line.raw)
            if uses_match:
                reference, _ = _scalar_parts(uses_match.group("value"))
                if reference.startswith("./") or reference.startswith("docker://"):
                    continue
                if "@" not in reference:
                    findings.append(
                        Finding(
                            "WF031",
                            "error",
                            "Action reference has no version",
                            "An external action must include an `@ref` suffix.",
                            "Choose a documented release ref, for example `actions/checkout@v4`.",
                            ["job `{0}`, line {1}".format(job.name, line.number)],
                        )
                    )
                else:
                    ref = reference.rsplit("@", 1)[1].lower()
                    if ref in {"main", "master", "latest", "head"}:
                        findings.append(
                            Finding(
                                "WF032",
                                "warning",
                                "Action uses a moving branch",
                                "`{0}` can change without a workflow edit and make CI behavior drift.".format(reference),
                                "Use a documented release tag or commit accepted by your dependency policy.",
                                ["job `{0}`, line {1}".format(job.name, line.number)],
                            )
                        )

        for line in fields.get("needs", []):
            for needed in _parse_needs(_mapping_value(line), _field_block(job, line)):
                if needed not in job_names:
                    findings.append(
                        Finding(
                            "WF040",
                            "error",
                            "Job depends on an unknown job",
                            "Job `{0}` declares `needs: {1}`, but no matching job ID exists.".format(job.name, needed),
                            "Correct the job ID or add the missing job.",
                            ["line {0}; known jobs: {1}".format(line.number, ", ".join(sorted(job_names)))],
                        )
                    )

    return Analysis(
        "workflow",
        source,
        findings,
        {"lines": len(text.splitlines()), "jobs": len(jobs)},
    )
