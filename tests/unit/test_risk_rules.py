from app.analysis.analyzer import analyze_file
from app.models import ChangedFile, Severity


def test_detect_public_function_signature_change():
    patch = """@@ -10,3 +10,3 @@
-def authenticate(token):
+def authenticate(token, strict=False):
     return decode(token)
 """

    changed_file = ChangedFile(
        filename="auth/token.py",
        patch=patch,
    )

    findings = analyze_file(changed_file)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.category == "PUBLIC_API_CHANGE"
    assert finding.severity == Severity.HIGH
    assert finding.line == 10
    assert "authenticate" in finding.message


def test_ignore_unchanged_function_signature():
    patch = """@@ -10,3 +10,3 @@
 def authenticate(token):
-    return decode(token)
+    return validate(token)
 """

    changed_file = ChangedFile(
        filename="auth/token.py",
        patch=patch,
    )

    findings = analyze_file(changed_file)

    assert findings == []