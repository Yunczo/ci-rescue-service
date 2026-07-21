"""Shared result models for CI Rescue Kit."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Finding:
    """One actionable diagnostic result."""

    code: str
    severity: str
    title: str
    summary: str
    remediation: str
    evidence: List[str] = field(default_factory=list)
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Analysis:
    """Complete analysis of one local input."""

    kind: str
    source: str
    findings: List[Finding]
    stats: Dict[str, int]

    def sorted_findings(self) -> List[Finding]:
        return sorted(
            self.findings,
            key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.code),
        )

    def counts(self) -> Dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": "CI Rescue Kit",
            "version": "1.0.0",
            "kind": self.kind,
            "source": self.source,
            "summary": self.counts(),
            "stats": self.stats,
            "findings": [item.to_dict() for item in self.sorted_findings()],
        }
