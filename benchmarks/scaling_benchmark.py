from time import perf_counter
from statistics import median
import platform
import sys

from app.analysis.repository_analyzer import analyze_repository_sources


SOURCE = """
from shared.auth import authenticate as auth

def process_user(user_id: int, strict: bool = False) -> str:
    token = str(user_id)
    return auth(token, strict=strict)

def validate_user(user_id: int):
    return process_user(user_id)

async def fetch_user(user_id: int):
    return validate_user(user_id)
"""


print()
print("=" * 74)
print("CANARY — SYNTHETIC REPOSITORY SCALING BENCHMARK")
print("=" * 74)

print()
print("ENVIRONMENT")
print(f"Python:                       {sys.version.split()[0]}")
print(f"Platform:                     {platform.platform()}")


for count in (100, 500, 1000):
    sources = {
        f"package/module_{index}.py": SOURCE
        for index in range(count)
    }

    lines = sum(
        source.count("\n") + 1
        for source in sources.values()
    )

    # Warm-up.
    analyze_repository_sources(sources)

    times = []

    for _ in range(7):
        start = perf_counter()

        result = analyze_repository_sources(
            sources
        )

        times.append(
            perf_counter() - start
        )

    elapsed = median(times)

    functions = sum(
        len(module.functions)
        for module in result.modules.values()
    )

    print()
    print(f"{count:,} FILE REPOSITORY")
    print(f"  Lines analyzed:             {lines:,}")
    print(f"  Functions indexed:          {functions:,}")
    print(f"  Call sites indexed:         {len(result.call_sites):,}")
    print(f"  Median latency:             {elapsed * 1000:,.2f} ms")
    print(f"  File throughput:            {count / elapsed:,.0f} files/s")
    print(f"  Source throughput:          {lines / elapsed:,.0f} LOC/s")
    print(f"  Parse errors:               {len(result.parse_errors)}")


print()
print("=" * 74)
