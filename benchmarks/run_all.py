from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent

BENCHMARKS = [
    "canary_repository_benchmark.py",
    "scaling_benchmark.py",
    "semantic_rules_benchmark.py",
    "semantic_mutation_benchmark.py",
]


print()
print("=" * 74)
print("CANARY — COMPLETE BENCHMARK SUITE")
print("=" * 74)


for benchmark in BENCHMARKS:
    path = (
        ROOT
        / "benchmarks"
        / benchmark
    )

    print()
    print("#" * 74)
    print(f"# {benchmark}")
    print("#" * 74)

    completed = subprocess.run(
        [
            sys.executable,
            str(path),
        ],
        cwd=ROOT,
        check=False,
    )

    if completed.returncode != 0:
        raise SystemExit(
            f"{benchmark} failed with "
            f"exit code "
            f"{completed.returncode}"
        )


print()
print("=" * 74)
print("ALL CANARY BENCHMARKS COMPLETED")
print("=" * 74)
