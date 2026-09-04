from app.analysis.ast_analyzer import analyze_python_source
from app.analysis.compatibility import compare_modules


CASES = [
    (
        "PUBLIC_API_REMOVED",
        "def api(a):\n    return a\n",
        "x = 1\n",
    ),
    (
        "REQUIRED_PARAMETER_ADDED",
        "def api(a):\n    return a\n",
        "def api(a, b):\n    return a\n",
    ),
    (
        "PARAMETER_REMOVED",
        "def api(a, b):\n    return a\n",
        "def api(a):\n    return a\n",
    ),
    (
        "PARAMETER_REORDERED",
        "def api(a, b):\n    return a\n",
        "def api(b, a):\n    return a\n",
    ),
    (
        "PARAMETER_DEFAULT_REMOVED",
        "def api(a=1):\n    return a\n",
        "def api(a):\n    return a\n",
    ),
    (
        "RETURN_TYPE_CHANGED",
        "def api() -> str:\n    return 'x'\n",
        "def api() -> int:\n    return 1\n",
    ),
    (
        "ASYNC_BEHAVIOR_CHANGED",
        "def api():\n    return 1\n",
        "async def api():\n    return 1\n",
    ),
]


passed = 0


print()
print("=" * 74)
print("CANARY — SEMANTIC COMPATIBILITY RULE BENCHMARK")
print("=" * 74)


for expected, before_source, after_source in CASES:
    before = analyze_python_source(
        before_source,
        "api.py",
    )

    after = analyze_python_source(
        after_source,
        "api.py",
    )

    findings = compare_modules(
        before,
        after,
    )

    categories = {
        finding.category
        for finding in findings
    }

    success = expected in categories

    passed += int(success)

    marker = (
        "PASS"
        if success
        else "FAIL"
    )

    print(
        f"{marker:<4}  {expected}"
    )


print()
print("-" * 74)
print(f"Semantic rules detected:     {passed}/{len(CASES)}")
print(f"Targeted rule coverage:      {(passed / len(CASES)) * 100:.1f}%")
print("=" * 74)
