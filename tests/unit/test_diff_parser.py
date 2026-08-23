
from app.analysis.diff_parser import parse_patch
from app.models import ChangedFile, ChangeType


def test_parse_added_and_removed_lines():
    patch = """@@ -10,3 +10,4 @@
 def authenticate(token):
-    return decode(token)
+    payload = decode(token)
+    return validate(payload)
 """

    changed_file = ChangedFile(
        filename="auth/token.py",
        patch=patch,
    )

    result = parse_patch(changed_file)

    removed = [
        line for line in result
        if line.change_type == ChangeType.REMOVED
    ]

    added = [
        line for line in result
        if line.change_type == ChangeType.ADDED
    ]

    assert removed[0].content == "    return decode(token)"
    assert removed[0].old_line == 11

    assert added[0].content == "    payload = decode(token)"
    assert added[0].new_line == 11

    assert added[1].content == "    return validate(payload)"
    assert added[1].new_line == 12