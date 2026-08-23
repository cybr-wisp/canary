import re

from app.models import ChangedFile, ChangeType, DiffLine


HUNK_PATTERN = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,\d+)? "
    r"\+(?P<new_start>\d+)(?:,\d+)? @@"
)


def parse_patch(changed_file: ChangedFile) -> list[DiffLine]:
    """Parse a unified Git patch into structured changed lines."""

    parsed: list[DiffLine] = []

    old_line = 0
    new_line = 0
    inside_hunk = False

    for raw_line in changed_file.patch.splitlines():
        hunk = HUNK_PATTERN.match(raw_line)

        if hunk:
            old_line = int(hunk.group("old_start"))
            new_line = int(hunk.group("new_start"))
            inside_hunk = True
            continue

        if not inside_hunk:
            continue

        if raw_line.startswith("\\"):
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            parsed.append(
                DiffLine(
                    content=raw_line[1:],
                    change_type=ChangeType.ADDED,
                    old_line=None,
                    new_line=new_line,
                )
            )
            new_line += 1

        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            parsed.append(
                DiffLine(
                    content=raw_line[1:],
                    change_type=ChangeType.REMOVED,
                    old_line=old_line,
                    new_line=None,
                )
            )
            old_line += 1

        else:
            content = raw_line[1:] if raw_line.startswith(" ") else raw_line

            parsed.append(
                DiffLine(
                    content=content,
                    change_type=ChangeType.CONTEXT,
                    old_line=old_line,
                    new_line=new_line,
                )
            )

            old_line += 1
            new_line += 1

    return parsed