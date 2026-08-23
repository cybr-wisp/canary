
import re

from app.models import (
    ChangedFile,
    ChangeType,
    DiffLine,
    RiskFinding,
    Severity,
)


FUNCTION_PATTERN = re.compile(
    r"^\s*(?:async\s+)?def\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*"
    r"\((?P<params>.*)\)"
)


def detect_function_signature_changes(
    changed_file: ChangedFile,
    lines: list[DiffLine],
) -> list[RiskFinding]:
    """Detect Python functions whose signatures changed in a patch."""

    removed_functions: dict[str, DiffLine] = {}
    added_functions: dict[str, DiffLine] = {}

    for line in lines:
        match = FUNCTION_PATTERN.match(line.content)

        if not match:
            continue

        function_name = match.group("name")

        if line.change_type == ChangeType.REMOVED:
            removed_functions[function_name] = line

        elif line.change_type == ChangeType.ADDED:
            added_functions[function_name] = line

    findings: list[RiskFinding] = []

    for function_name, old_line in removed_functions.items():
        new_line = added_functions.get(function_name)

        if not new_line:
            continue

        if old_line.content.strip() == new_line.content.strip():
            continue

        is_public = not function_name.startswith("_")

        severity = (
            Severity.HIGH
            if is_public
            else Severity.MEDIUM
        )

        findings.append(
            RiskFinding(
                category="PUBLIC_API_CHANGE",
                severity=severity,
                filename=changed_file.filename,
                line=new_line.new_line,
                message=(
                    f"Function signature changed for "
                    f"`{function_name}`."
                ),
                evidence=(
                    f"{old_line.content.strip()} "
                    f"→ {new_line.content.strip()}"
                ),
            )
        )

    return findings