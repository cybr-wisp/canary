from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.analysis.ast_analyzer import analyze_python_source
from app.analysis.call_validation import validate_compatibility_impacts
from app.analysis.compatibility import compare_modules
from app.analysis.impact import analyze_compatibility_impact
from app.analysis.repository_analyzer import analyze_repository_sources
from app.models import CallImpactStatus


@dataclass(frozen=True)
class Case:
    name: str
    category: str
    before_api: str
    after_api: str
    caller: str
    expected: str


def caller_source(
    function: str,
    args: str,
    style: int,
    *,
    awaited: bool = False,
) -> str:
    if style % 3 == 0:
        import_line = (
            f"from api import {function}"
        )
        call = f"{function}({args})"

    elif style % 3 == 1:
        import_line = (
            f"from api import {function} as target"
        )
        call = f"target({args})"

    else:
        import_line = "import api as api_module"
        call = f"api_module.{function}({args})"

    if awaited:
        return (
            f"{import_line}\n\n"
            "async def downstream():\n"
            f"    return await {call}\n"
        )

    return (
        f"{import_line}\n\n"
        "def downstream():\n"
        f"    return {call}\n"
    )


cases: list[Case] = []


# ------------------------------------------------------------
# 60 confirmed breaking cases
# ------------------------------------------------------------

for i in range(10):
    function = f"required_added_{i}"

    cases.append(
        Case(
            name=f"required parameter added #{i}",
            category="REQUIRED_PARAMETER_ADDED",
            before_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a, b):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1",
                i,
            ),
            expected="BREAKS",
        )
    )


for i in range(10):
    function = f"parameter_removed_{i}"

    cases.append(
        Case(
            name=f"parameter removed #{i}",
            category="PARAMETER_REMOVED",
            before_api=(
                f"def {function}(a, b):\n"
                "    return a + b\n"
            ),
            after_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1, 2",
                i,
            ),
            expected="BREAKS",
        )
    )


for i in range(10):
    function = f"parameter_reordered_{i}"

    cases.append(
        Case(
            name=f"parameter reordered #{i}",
            category="PARAMETER_REORDERED",
            before_api=(
                f"def {function}(a, b):\n"
                "    return a - b\n"
            ),
            after_api=(
                f"def {function}(b, a):\n"
                "    return a - b\n"
            ),
            caller=caller_source(
                function,
                "1, 2",
                i,
            ),
            expected="BREAKS",
        )
    )


for i in range(10):
    function = f"default_removed_{i}"

    cases.append(
        Case(
            name=f"default removed #{i}",
            category="PARAMETER_DEFAULT_REMOVED",
            before_api=(
                f"def {function}(a=1):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "",
                i,
            ),
            expected="BREAKS",
        )
    )


for i in range(10):
    function = f"async_changed_{i}"

    cases.append(
        Case(
            name=f"sync to async #{i}",
            category="ASYNC_BEHAVIOR_CHANGED",
            before_api=(
                f"def {function}():\n"
                "    return 1\n"
            ),
            after_api=(
                f"async def {function}():\n"
                "    return 1\n"
            ),
            caller=caller_source(
                function,
                "",
                i,
            ),
            expected="BREAKS",
        )
    )


for i in range(10):
    function = f"removed_api_{i}"

    cases.append(
        Case(
            name=f"public API removed #{i}",
            category="PUBLIC_API_REMOVED",
            before_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            after_api=(
                "def surviving_api(a):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1",
                i,
            ),
            expected="BREAKS",
        )
    )


# ------------------------------------------------------------
# 30 safe controls
# ------------------------------------------------------------

for i in range(5):
    function = f"safe_required_{i}"

    cases.append(
        Case(
            name=f"safe required parameter #{i}",
            category="REQUIRED_PARAMETER_ADDED",
            before_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a, b):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1, 2",
                i,
            ),
            expected="SAFE",
        )
    )


for i in range(5):
    function = f"safe_removed_{i}"

    cases.append(
        Case(
            name=f"safe removed parameter #{i}",
            category="PARAMETER_REMOVED",
            before_api=(
                f"def {function}(a, b=2):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1",
                i,
            ),
            expected="SAFE",
        )
    )


for i in range(5):
    function = f"safe_reorder_{i}"

    cases.append(
        Case(
            name=f"safe parameter reorder #{i}",
            category="PARAMETER_REORDERED",
            before_api=(
                f"def {function}(a, b):\n"
                "    return a - b\n"
            ),
            after_api=(
                f"def {function}(b, a):\n"
                "    return a - b\n"
            ),
            caller=caller_source(
                function,
                "a=1, b=2",
                i,
            ),
            expected="SAFE",
        )
    )


for i in range(5):
    function = f"safe_default_{i}"

    cases.append(
        Case(
            name=f"safe default removal #{i}",
            category="PARAMETER_DEFAULT_REMOVED",
            before_api=(
                f"def {function}(a=1):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            caller=caller_source(
                function,
                "1",
                i,
            ),
            expected="SAFE",
        )
    )


for i in range(5):
    function = f"safe_async_{i}"

    cases.append(
        Case(
            name=f"safe sync to async #{i}",
            category="ASYNC_BEHAVIOR_CHANGED",
            before_api=(
                f"def {function}():\n"
                "    return 1\n"
            ),
            after_api=(
                f"async def {function}():\n"
                "    return 1\n"
            ),
            caller=caller_source(
                function,
                "",
                i,
                awaited=True,
            ),
            expected="SAFE",
        )
    )


for i in range(5):
    function = f"safe_removed_api_{i}"

    cases.append(
        Case(
            name=f"unused removed API #{i}",
            category="PUBLIC_API_REMOVED",
            before_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            after_api=(
                "def surviving_api(a):\n"
                "    return a\n"
            ),
            caller=(
                "from api import surviving_api\n\n"
                "def downstream():\n"
                "    return surviving_api(1)\n"
            ),
            expected="SAFE",
        )
    )


# ------------------------------------------------------------
# 10 deliberately ambiguous cases
# ------------------------------------------------------------

for i in range(5):
    function = f"return_changed_{i}"

    cases.append(
        Case(
            name=f"return type changed #{i}",
            category="RETURN_TYPE_CHANGED",
            before_api=(
                f"def {function}() -> str:\n"
                "    return '1'\n"
            ),
            after_api=(
                f"def {function}() -> int:\n"
                "    return 1\n"
            ),
            caller=caller_source(
                function,
                "",
                i,
            ),
            expected="UNKNOWN",
        )
    )


for i in range(5):
    function = f"star_args_{i}"

    if i % 2 == 0:
        caller = (
            f"from api import {function}\n\n"
            "def downstream(args):\n"
            f"    return {function}(*args)\n"
        )
    else:
        caller = (
            f"from api import {function}\n\n"
            "def downstream(kwargs):\n"
            f"    return {function}(**kwargs)\n"
        )

    cases.append(
        Case(
            name=f"dynamic argument binding #{i}",
            category="REQUIRED_PARAMETER_ADDED",
            before_api=(
                f"def {function}(a):\n"
                "    return a\n"
            ),
            after_api=(
                f"def {function}(a, b):\n"
                "    return a\n"
            ),
            caller=caller,
            expected="UNKNOWN",
        )
    )


def run_case(
    case: Case,
) -> tuple[str, bool]:
    before = analyze_python_source(
        case.before_api,
        "api.py",
    )

    after = analyze_python_source(
        case.after_api,
        "api.py",
    )

    findings = compare_modules(
        before,
        after,
    )

    category_found = any(
        finding.category == case.category
        for finding in findings
    )

    repository = analyze_repository_sources(
        {
            "api.py": case.after_api,
            "caller.py": case.caller,
        }
    )

    impacts = analyze_compatibility_impact(
        findings,
        before=before,
        after=after,
        repository=repository,
    )

    validated = validate_compatibility_impacts(
        impacts,
        before=before,
        after=after,
    )

    statuses = [
        assessment.status
        for impact in validated
        for assessment in impact.assessments
        if impact.impact.finding.category
        == case.category
    ]

    if CallImpactStatus.BREAKS in statuses:
        prediction = "BREAKS"

    elif CallImpactStatus.UNKNOWN in statuses:
        prediction = "UNKNOWN"

    else:
        prediction = "SAFE"

    return prediction, category_found


results = []

category_results = defaultdict(
    lambda: {
        "total": 0,
        "correct": 0,
    }
)


for case in cases:
    prediction, category_found = run_case(
        case
    )

    correct = prediction == case.expected

    results.append(
        (
            case,
            prediction,
            category_found,
            correct,
        )
    )

    category_results[
        case.category
    ]["total"] += 1

    category_results[
        case.category
    ]["correct"] += int(correct)


labeled = [
    result
    for result in results
    if result[0].expected
    in {"BREAKS", "SAFE"}
]


tp = sum(
    case.expected == "BREAKS"
    and prediction == "BREAKS"
    for case, prediction, _, _ in labeled
)

fn = sum(
    case.expected == "BREAKS"
    and prediction != "BREAKS"
    for case, prediction, _, _ in labeled
)

fp = sum(
    case.expected == "SAFE"
    and prediction == "BREAKS"
    for case, prediction, _, _ in labeled
)

tn = sum(
    case.expected == "SAFE"
    and prediction != "BREAKS"
    for case, prediction, _, _ in labeled
)


unexpected_abstentions = sum(
    prediction == "UNKNOWN"
    for case, prediction, _, _ in labeled
)


precision = (
    tp / (tp + fp)
    if (tp + fp)
    else 0.0
)

recall = (
    tp / (tp + fn)
    if (tp + fn)
    else 0.0
)

specificity = (
    tn / (tn + fp)
    if (tn + fp)
    else 0.0
)

f1 = (
    2 * precision * recall
    / (precision + recall)
    if (precision + recall)
    else 0.0
)

accuracy = (
    (tp + tn) / len(labeled)
    if labeled
    else 0.0
)


expected_unknown = [
    result
    for result in results
    if result[0].expected == "UNKNOWN"
]

correct_unknown = sum(
    prediction == "UNKNOWN"
    for case, prediction, _, _ in expected_unknown
)

semantic_detection = sum(
    category_found
    for _, _, category_found, _ in results
)


print()
print("=" * 74)
print("CANARY — SEEDED SEMANTIC MUTATION BENCHMARK")
print("=" * 74)

print()
print("DATASET")
print(f"Total seeded cases:             {len(results):>4}")
print(f"Confirmed-break cases:          {sum(c.expected == 'BREAKS' for c in cases):>4}")
print(f"Safe controls:                  {sum(c.expected == 'SAFE' for c in cases):>4}")
print(f"Conservative / UNKNOWN cases:   {sum(c.expected == 'UNKNOWN' for c in cases):>4}")

print()
print("CONFIRMED BREAKAGE CLASSIFICATION")
print(f"True positives:                 {tp:>4}")
print(f"True negatives:                 {tn:>4}")
print(f"False positives:                {fp:>4}")
print(f"False negatives:                {fn:>4}")
print(f"Unexpected abstentions:         {unexpected_abstentions:>4}")

print()
print("METRICS")
print(f"Precision:                       {precision * 100:>7.2f}%")
print(f"Recall:                          {recall * 100:>7.2f}%")
print(f"Specificity:                     {specificity * 100:>7.2f}%")
print(f"F1 score:                        {f1:>7.4f}")
print(f"Labeled-case accuracy:           {accuracy * 100:>7.2f}%")

print()
print("CONSERVATIVE ANALYSIS")
print(
    "Expected UNKNOWN classified UNKNOWN: "
    f"{correct_unknown}/{len(expected_unknown)}"
)

print()
print("SEMANTIC DETECTION")
print(
    "Expected compatibility category found: "
    f"{semantic_detection}/{len(results)}"
)

print()
print("BY CATEGORY")

for category in sorted(category_results):
    values = category_results[category]

    rate = (
        values["correct"]
        / values["total"]
        * 100
    )

    print(
        f"{category:<34}"
        f"{values['correct']:>3}/{values['total']:<3}"
        f"{rate:>7.1f}%"
    )


failures = [
    (
        case,
        prediction,
        category_found,
    )
    for (
        case,
        prediction,
        category_found,
        correct,
    ) in results
    if not correct or not category_found
]


print()
print("FAILURES / MISMATCHES")

if not failures:
    print("None")
else:
    for (
        case,
        prediction,
        category_found,
    ) in failures:
        print(
            f"{case.name}: "
            f"expected={case.expected}, "
            f"predicted={prediction}, "
            f"semantic_rule_found="
            f"{category_found}"
        )


print()
print("=" * 74)
