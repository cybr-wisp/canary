# Canary Benchmarks

Canary includes a reproducible benchmark suite covering four properties of the analysis engine:

1. **Performance** on the Canary repository
2. **Determinism** across repeated executions
3. **Scaling** across generated repositories up to 1,000 Python files
4. **Semantic correctness** across controlled API-regression cases

All benchmark implementations live in [`benchmarks/`](benchmarks/).

Run the complete suite from the repository root:

```bash
python benchmarks/run_all.py
```

---

## Summary

| Measurement | Last verified result |
|---|---:|
| Median Canary repository analysis | **64.45 ms** |
| Canary repository throughput | **118,549 LOC/s** |
| Deterministic executions | **50/50 identical** |
| 1,000-file synthetic analysis | **210.36 ms** |
| Functions indexed at 1,000 files | **3,000** |
| Call sites indexed at 1,000 files | **4,000** |
| Semantic compatibility classes exercised | **7/7** |
| Seeded semantic cases handled as expected | **100/100** |
| Breaking callers detected | **60/60** |
| Safe controls preserved | **30/30** |
| Ambiguous cases correctly returned `UNKNOWN` | **10/10** |
| Precision | **100.00%** |
| Recall | **100.00%** |
| Specificity | **100.00%** |
| F1 score | **1.0000** |
| False positives | **0** |
| False negatives | **0** |

> Performance values are machine-dependent. Re-run the suite on the current checkout for current measurements.

---

# 1. Canary Repository Benchmark

Implementation:

[`benchmarks/canary_repository_benchmark.py`](benchmarks/canary_repository_benchmark.py)

This benchmark measures Canary's repository indexing and semantic-analysis path against the Canary codebase itself.

It excludes:

- `.venv/`
- `venv/`
- `.git/`
- `__pycache__/`
- `benchmarks/`

Excluding `benchmarks/` prevents benchmark infrastructure itself from inflating the measured corpus.

## Last Verified Corpus

| Characteristic | Result |
|---|---:|
| Python files indexed | **42** |
| Python LOC analyzed | **7,641** |
| Functions indexed | **211** |
| Call sites indexed | **861** |

## Last Verified Performance

| Metric | Result |
|---|---:|
| Median analysis latency | **64.45 ms** |
| P95 analysis latency | **102.66 ms** |
| Median file throughput | **652 files/s** |
| Median source throughput | **118,549 LOC/s** |
| Deterministic executions | **50/50 identical** |

The benchmark executes five warm-up runs followed by 50 measured runs.

It records:

- median latency
- P95 latency
- file throughput
- source throughput
- parse errors
- semantic fingerprints across repeated runs

File loading occurs before timing begins, so the benchmark measures the analysis engine rather than disk-read performance.

---

# 2. Determinism

Determinism is measured as part of the Canary repository benchmark.

For every measured execution, the benchmark constructs a semantic representation containing:

- indexed modules
- functions
- async/sync state
- parameter names
- parameter kinds
- default-value presence
- return annotations
- resolved call sites
- positional argument counts
- keyword arguments
- `*args`
- `**kwargs`
- awaited-call state

That semantic representation is hashed with SHA-256.

## Last Verified Result

| Measurement | Result |
|---|---:|
| Repeated executions | **50** |
| Identical semantic fingerprints | **50/50** |
| Divergent fingerprints | **0** |

This establishes deterministic behavior for identical input under the same benchmark environment.

---

# 3. Synthetic Repository Scaling

Implementation:

[`benchmarks/scaling_benchmark.py`](benchmarks/scaling_benchmark.py)

The scaling benchmark evaluates Canary against generated repositories at three sizes:

- 100 Python files
- 500 Python files
- 1,000 Python files

Each generated module contains multiple functions, imported symbols, aliases, function calls, keyword arguments, and async code.

## Verified Scaling Results

| Python files | LOC | Functions | Call sites | Median latency | Files/s | LOC/s | Parse errors |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **100** | 1,300 | 300 | 400 | **19.65 ms** | 5,089 | 66,151 | 0 |
| **500** | 6,500 | 1,500 | 2,000 | **106.33 ms** | 4,702 | 61,132 | 0 |
| **1,000** | 13,000 | 3,000 | 4,000 | **210.36 ms** | 4,754 | 61,798 | 0 |

The benchmark performs one warm-up run followed by seven measured executions at each repository size.

The reported latency is the median of those executions.

> These are synthetic scaling measurements, not universal production latency claims.

---

# 4. Semantic Compatibility Rule Benchmark

Implementation:

[`benchmarks/semantic_rules_benchmark.py`](benchmarks/semantic_rules_benchmark.py)

This benchmark directly exercises all seven semantic compatibility classes currently implemented by Canary.

| Semantic compatibility class | Result |
|---|---:|
| `PUBLIC_API_REMOVED` | **PASS** |
| `REQUIRED_PARAMETER_ADDED` | **PASS** |
| `PARAMETER_REMOVED` | **PASS** |
| `PARAMETER_REORDERED` | **PASS** |
| `PARAMETER_DEFAULT_REMOVED` | **PASS** |
| `RETURN_TYPE_CHANGED` | **PASS** |
| `ASYNC_BEHAVIOR_CHANGED` | **PASS** |

**7/7 implemented semantic compatibility classes were identified in their targeted validation cases.**

This measures targeted rule coverage rather than universal production accuracy.

---

# 5. Seeded Semantic Mutation Benchmark

Implementation:

[`benchmarks/semantic_mutation_benchmark.py`](benchmarks/semantic_mutation_benchmark.py)

This benchmark evaluates Canary's complete repository-aware semantic regression pipeline:

```text
BASE / HEAD
    |
    v
AST analysis
    |
    v
Semantic compatibility detection
    |
    v
Repository caller discovery
    |
    v
Impact analysis
    |
    v
Argument-aware validation
    |
    v
BREAKS / SAFE / UNKNOWN
```

## Dataset

| Ground-truth case type | Count |
|---|---:|
| Confirmed breaking callers | **60** |
| Safe controls | **30** |
| Deliberately ambiguous cases | **10** |
| **Total** | **100** |

The cases exercise:

- newly required parameters
- removed parameters
- reordered parameters
- removed parameter defaults
- public API removal
- sync-to-async changes
- return-type changes
- direct imports
- aliased imports
- module-qualified calls
- positional calls
- keyword calls
- `*args`
- `**kwargs`
- awaited calls
- non-awaited calls

---

## Classification Results

| Metric | Result |
|---|---:|
| True positives | **60** |
| True negatives | **30** |
| False positives | **0** |
| False negatives | **0** |
| Unexpected abstentions | **0** |
| Precision | **100.00%** |
| Recall | **100.00%** |
| Specificity | **100.00%** |
| F1 score | **1.0000** |
| Labeled-case accuracy | **100.00%** |

These measurements apply only to this controlled seeded benchmark.

They are not estimates of universal production accuracy.

---

# 6. Conservative `UNKNOWN` Handling

Canary deliberately returns `UNKNOWN` when static evidence is insufficient to justify a confident compatibility decision.

| Metric | Result |
|---|---:|
| Deliberately ambiguous cases | **10** |
| Correctly returned `UNKNOWN` | **10/10** |
| Incorrect confident classifications | **0** |

The ambiguous cases include dynamic argument binding through `*args` and `**kwargs`, as well as return-type changes whose downstream consumption cannot currently be proven.

This behavior is intentional: Canary prefers visible uncertainty over an unsupported compatibility claim.

---

# 7. Results by Semantic Category

| Category | Cases handled as expected |
|---|---:|
| `ASYNC_BEHAVIOR_CHANGED` | **15/15** |
| `PARAMETER_DEFAULT_REMOVED` | **15/15** |
| `PARAMETER_REMOVED` | **15/15** |
| `PARAMETER_REORDERED` | **15/15** |
| `PUBLIC_API_REMOVED` | **15/15** |
| `REQUIRED_PARAMETER_ADDED` | **20/20** |
| `RETURN_TYPE_CHANGED` | **5/5** |
| **Total** | **100/100** |

---

# Methodology

## Performance Timing

Performance benchmarks use Python's `time.perf_counter()`.

### Canary repository benchmark

1. Discover the measured Python corpus.
2. Load source files into memory.
3. Execute five warm-up analyses.
4. Execute 50 measured analyses.
5. Calculate median latency.
6. Calculate P95 latency.
7. Derive file and LOC throughput.
8. Compare semantic fingerprints across all 50 runs.

### Synthetic scaling benchmark

For each repository size:

1. Generate the corpus in memory.
2. Execute one warm-up analysis.
3. Execute seven measured analyses.
4. Report median latency.
5. Derive file and LOC throughput.

Disk I/O is outside the timed analysis region.

---

# Semantic Ground Truth

Every seeded mutation case has an explicit expected outcome:

```text
BREAKS
SAFE
UNKNOWN
```

Canary independently performs:

1. BASE/HEAD AST extraction
2. semantic API comparison
3. repository indexing
4. call-site discovery
5. impact analysis
6. argument-aware compatibility validation

The predictions are compared against the predefined expected outcomes to calculate the reported metrics.

---

# Reproducing the Benchmarks

Clone and enter the repository:

```bash
git clone https://github.com/cybr-wisp/canary.git
cd canary
```

Create a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install Canary:

```bash
pip install -e .
```

Run the complete benchmark suite:

```bash
python benchmarks/run_all.py
```

Run individual benchmarks:

```bash
python benchmarks/canary_repository_benchmark.py
python benchmarks/scaling_benchmark.py
python benchmarks/semantic_rules_benchmark.py
python benchmarks/semantic_mutation_benchmark.py
```

---

# Limitations

These benchmarks do not establish universal production accuracy or performance.

Current limitations include:

- the semantic mutation corpus is controlled and synthetic
- scaling repositories are generated
- runtime depends on hardware, operating system, Python version, and repository structure
- dynamic Python behavior remains outside parts of Canary's static model
- the corpus does not yet consist of independently sourced historical production regressions

Future benchmark work can include:

- historical breaking pull requests
- independently sourced open-source repositories
- larger repository corpora
- Python metaprogramming and dynamic-dispatch cases
- baseline static-analysis comparisons
- independently generated semantic mutations

---

# Last Verified Environment

The currently documented local measurements were collected on Windows using:

```text
Python 3.14.2
```

Canary CI separately validates the project on:

```text
Python 3.11
Python 3.12
Python 3.13
```

For current measurements, run:

```bash
python benchmarks/run_all.py
```



