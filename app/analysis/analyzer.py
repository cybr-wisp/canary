
from app.analysis.diff_parser import parse_patch
from app.analysis.risk_rules import detect_function_signature_changes
from app.models import ChangedFile, RiskFinding


def analyze_file(changed_file: ChangedFile) -> list[RiskFinding]:
    """Run Canary's regression rules against one changed file."""

    if not changed_file.filename.endswith(".py"):
        return []

    lines = parse_patch(changed_file)

    findings: list[RiskFinding] = []

    findings.extend(
        detect_function_signature_changes(
            changed_file,
            lines,
        )
    )

    return findings