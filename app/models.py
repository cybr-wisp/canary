
from dataclasses import dataclass
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