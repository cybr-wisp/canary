from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"


@dataclass
class ChangedFile:
    filename: str
    patch: str
    additions: int = 0
    deletions: int = 0


@dataclass
class DiffLine:
    content: str
    change_type: ChangeType
    old_line: int | None = None
    new_line: int | None = None


@dataclass
class RiskFinding:
    category: str
    severity: Severity
    filename: str
    message: str
    line: int | None = None
    evidence: str | None = None


@dataclass
class AnalysisResult:
    """
    Complete result of analyzing a pull request.

    Contains both regression findings and metadata used by
    Canary's GitHub and terminal interfaces.
    """

    findings: list[RiskFinding] = field(default_factory=list)

    files_analyzed: int = 0
    python_files_analyzed: int = 0
    functions_inspected: int = 0

    changed_lines: int = 0
    additions: int = 0
    deletions: int = 0

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_risk_count(self) -> int:
        return sum(
            finding.severity == Severity.HIGH
            for finding in self.findings
        )

    @property
    def medium_risk_count(self) -> int:
        return sum(
            finding.severity == Severity.MEDIUM
            for finding in self.findings
        )

    @property
    def low_risk_count(self) -> int:
        return sum(
            finding.severity == Severity.LOW
            for finding in self.findings
        )

    @property
    def has_high_risk(self) -> bool:
        return self.high_risk_count > 0