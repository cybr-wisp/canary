from pathlib import Path
from time import perf_counter
from statistics import median
import hashlib
import platform
import sys

from app.analysis.repository_analyzer import analyze_repository_sources


EXCLUDED = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "benchmarks",
}


files = [
    p for p in Path(".").rglob("*.py")
    if not any(part in EXCLUDED for part in p.parts)
]

sources = {
    p.as_posix(): p.read_text(encoding="utf-8")
    for p in files
}

loc = sum(
    text.count("\n") + 1
    for text in sources.values()
)


# Five warm-up runs before timing.
for _ in range(5):
    analyze_repository_sources(sources)


times = []
fingerprints = []

for _ in range(50):
    start = perf_counter()

    result = analyze_repository_sources(sources)

    times.append(
        perf_counter() - start
    )

    semantic_state = []

    for filename, module in sorted(result.modules.items()):
        semantic_state.append(filename)

        for name, fn in sorted(module.functions.items()):
            semantic_state.append(
                (
                    filename,
                    name,
                    fn.is_async,
                    tuple(
                        (
                            parameter.name,
                            parameter.kind,
                            parameter.has_default,
                        )
                        for parameter in fn.parameters
                    ),
                    fn.return_annotation,
                )
            )

    for call in result.call_sites:
        semantic_state.append(
            (
                call.filename,
                call.line,
                call.column,
                call.resolved_callee,
                call.positional_argument_count,
                call.keyword_arguments,
                call.has_star_args,
                call.has_star_kwargs,
                call.is_awaited,
            )
        )

    fingerprint = hashlib.sha256(
        repr(semantic_state).encode()
    ).hexdigest()

    fingerprints.append(fingerprint)


sorted_times = sorted(times)

p50 = median(times)

p95 = sorted_times[
    int(len(sorted_times) * 0.95) - 1
]

functions = sum(
    len(module.functions)
    for module in result.modules.values()
)

unique_fingerprints = len(set(fingerprints))


print()
print("=" * 74)
print("CANARY — REPOSITORY BENCHMARK")
print("=" * 74)

print()
print("ENVIRONMENT")
print(f"Python:                       {sys.version.split()[0]}")
print(f"Platform:                     {platform.platform()}")

print()
print("CORPUS")
print(f"Python files indexed:         {len(sources):,}")
print(f"Lines of Python analyzed:     {loc:,}")
print(f"Functions indexed:            {functions:,}")
print(f"Call sites indexed:           {len(result.call_sites):,}")
print(f"Parse errors:                 {len(result.parse_errors):,}")

print()
print("PERFORMANCE")
print(f"Median analysis latency:      {p50 * 1000:.2f} ms")
print(f"P95 analysis latency:         {p95 * 1000:.2f} ms")
print(f"Median file throughput:       {len(sources) / p50:,.0f} files/s")
print(f"Median source throughput:     {loc / p50:,.0f} LOC/s")

print()
print("DETERMINISM")
print(f"Deterministic:                {unique_fingerprints == 1}")
print(f"Identical fingerprints:       {50 if unique_fingerprints == 1 else 'N/A'}/50")
print(f"Unique fingerprints:          {unique_fingerprints}")

print()
print("=" * 74)
