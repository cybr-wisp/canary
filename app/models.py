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


class CallImpactStatus(str, Enum):
    UNAFFECTED = "unaffected"
    BREAKS = "breaks"
    UNKNOWN = "unknown"


@dataclass
class ChangedFile:
    filename: str
    patch: str
    additions: int = 0
    deletions: int = 0

    status: str = "modified"
    previous_filename: str | None = None


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
    symbol: str | None = None


@dataclass
class AnalysisResult:
    """
    Complete result of analyzing a pull request.

    Contains both regression findings and metadata used by
    Canary's GitHub and terminal interfaces.
    """

    findings: list[RiskFinding] = field(
        default_factory=list
    )

    validated_impacts: list[
        "ValidatedCompatibilityImpact"
    ] = field(
        default_factory=list
    )

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


@dataclass(frozen=True)
class ParameterInfo:
    name: str
    kind: str
    has_default: bool = False
    annotation: str | None = None


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    qualname: str
    line: int
    is_async: bool
    is_public: bool
    parameters: tuple[ParameterInfo, ...] = ()
    return_annotation: str | None = None


@dataclass
class ModuleAnalysis:
    filename: str

    functions: dict[str, FunctionInfo] = field(
        default_factory=dict
    )

    imports: set[str] = field(
        default_factory=set
    )


@dataclass(frozen=True)
class CallSite:
    filename: str
    line: int
    column: int
    callee: str
    resolved_callee: str
    enclosing_symbol: str | None = None

    positional_argument_count: int = 0
    keyword_arguments: tuple[str, ...] = ()

    has_star_args: bool = False
    has_star_kwargs: bool = False

    is_awaited: bool = False


@dataclass
class RepositoryAnalysis:
    modules: dict[str, ModuleAnalysis] = field(
        default_factory=dict
    )

    call_sites: list[CallSite] = field(
        default_factory=list
    )

    parse_errors: dict[str, str] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class CompatibilityImpact:
    finding: RiskFinding
    impact_severity: Severity
    call_sites: tuple[CallSite, ...] = ()

    @property
    def affected_call_count(self) -> int:
        return len(self.call_sites)

    @property
    def has_affected_calls(self) -> bool:
        return bool(self.call_sites)


@dataclass(frozen=True)
class CallSiteAssessment:
    call_site: CallSite
    status: CallImpactStatus
    reason: str


@dataclass(frozen=True)
class ValidatedCompatibilityImpact:
    impact: CompatibilityImpact
    assessments: tuple[CallSiteAssessment, ...] = ()

    @property
    def breaking_call_sites(
        self,
    ) -> tuple[CallSite, ...]:
        return tuple(
            assessment.call_site
            for assessment in self.assessments
            if assessment.status
            == CallImpactStatus.BREAKS
        )

    @property
    def breaking_call_count(self) -> int:
        return len(
            self.breaking_call_sites
        )

    @property
    def unknown_call_sites(
        self,
    ) -> tuple[CallSite, ...]:
        return tuple(
            assessment.call_site
            for assessment in self.assessments
            if assessment.status
            == CallImpactStatus.UNKNOWN
        )