<h1 align="center">c a n a r y</h1>

**Canary is a deterministic, repository-aware static analysis engine for Python pull requests.**

It compares API contracts across BASE and HEAD, traces changed interfaces into repository call sites, statically re-binds existing calls against new signatures, and surfaces confirmed incompatibilities before merge.

<p align="center">
  <img src="assets/canary-header.png" alt="Canary" width="75%">
</p>

<p align="center">
  <strong>64.45 ms</strong> median analysis
  &nbsp; · &nbsp;
  <strong>118.5K LOC/s</strong> throughput
  &nbsp; · &nbsp;
  <strong>100/100</strong> seeded cases
  &nbsp; · &nbsp;
  <strong>50/50</strong> deterministic runs
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GitHub-App-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub App">
  <img src="https://img.shields.io/badge/FastAPI-Webhooks-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/pytest-88%20passed-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="pytest">
  <a href="https://github.com/cybr-wisp/canary/actions/workflows/ci.yml">
    <img src="https://github.com/cybr-wisp/canary/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/cybr-wisp/canary/releases">
    <img src="https://img.shields.io/github/v/release/cybr-wisp/canary" alt="Release">
  </a>
</p>

---

## The problem

A pull request can pass CI, type checking, linting, and its existing test suite while still introducing an interface change that breaks an unexercised downstream caller.

```diff
-def authenticate(token):
+def authenticate(token, strict):
     ...
```

The modified function is valid. The project may still build. Its tests may still pass. But elsewhere in the repository:

```python
from auth import authenticate

def login():
    return authenticate("demo-token")
```

That caller no longer satisfies the API contract.

The important question is not only *what changed in this pull request*, but:

> **Which existing callers depend on that contract, and which of them are now incompatible?**

<p align="center">
  <img src="assets/the-gap.png" alt="The gap between passing CI and breaking callers" width="75%">
</p>

---

## How it works

Canary compares the BASE and HEAD versions of changed Python APIs, builds a static repository call index, resolves affected callers, and validates those calls against the new callable contract.

<p align="center">
  <img src="assets/analysis-pipeline.png" alt="Canary analysis pipeline" width="75%">
</p>

There is **no LLM in the analysis loop**. For identical repository state and pull-request input, Canary produces deterministic findings. When available static evidence is insufficient to justify a compatibility decision, Canary returns `UNKNOWN` instead of guessing.

### Semantic compatibility rules

| Finding | What changed | Potential impact |
|---|---|---|
| `REQUIRED_PARAMETER_ADDED` | New required argument | Existing caller provides too few arguments |
| `PARAMETER_REMOVED` | Existing parameter deleted | Caller still supplies the removed argument |
| `PARAMETER_REORDERED` | Positional order changes | Existing arguments bind to different parameters |
| `PARAMETER_DEFAULT_REMOVED` | Optional becomes required | Caller relied on the previous default |
| `RETURN_TYPE_CHANGED` | Return annotation changes | Downstream usage may no longer be compatible |
| `ASYNC_BEHAVIOR_CHANGED` | Sync/async contract changes | Missing or invalid `await` |
| `PUBLIC_API_REMOVED` | Public callable disappears | Existing caller references a missing API |

Each changed interface is then traced into repository usage. Canary statically validates positional-only, keyword-only, `*args`, `**kwargs`, duplicate bindings, and awaited versus non-awaited calls:

```text
valid before + invalid now  →  BREAKS
still valid                 →  UNAFFECTED
cannot prove safely         →  UNKNOWN
```

Resolution covers direct imports, aliased imports, module-qualified calls, relative imports, same-file calls, and class-qualified calls.

---

## Benchmarks

Canary is evaluated across its own repository (42 Python files, 7,641 LOC, 211 functions, 861 call sites), a 100-case seeded semantic mutation suite, and generated repositories up to 1,000 files.

| | |
|---|---:|
| Median analysis latency | **64.45 ms** |
| Source throughput | **118,549 LOC/s** |
| Deterministic executions | **50/50 identical** |
| Precision / Recall / F1 | **100% / 100% / 1.0** |
| Ambiguous cases correctly abstained | **10/10** |
| Semantic categories covered | **7/7** |
| 1,000-file repository | **210.36 ms** |

Full methodology, raw results, and reproduction instructions are documented in [`benchmark.md`](benchmark.md).

```bash
python benchmarks/run_all.py
```

<sub>Benchmark results describe controlled evaluation conditions and should not be interpreted as universal production accuracy.</sub>

---

## What ships: GitHub Check and CLI

Canary runs as a GitHub App and surfaces analysis directly during pull-request review. High-risk findings fail the check before merge.

<p align="center">
  <img src="assets/what-ships.png" alt="Canary output" width="75%">
</p>

GitHub Check output includes risk level, semantic finding category, old/new interface evidence, affected repository callers, confirmed incompatibilities, compatible callers, unresolved callers requiring review, exact source locations, and inline annotations.

The same analysis engine is available from the terminal:

```bash
canary inspect https://github.com/owner/repository/pull/123
```

---

## Architecture

The webhook and CLI entry points converge on a shared analysis service. Source resolution, AST extraction, compatibility analysis, repository indexing, impact analysis, and argument validation run through the same deterministic engine.

<p align="center">
  <img src="assets/architecture-diagram.png" alt="Canary system architecture" width="75%">
</p>

---

## Quick start

```bash
git clone https://github.com/cybr-wisp/canary.git
cd canary
python -m venv .venv
source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .
canary --help
```

Inspect a pull request:

```bash
canary inspect https://github.com/owner/repository/pull/123
```

Run the tests and benchmarks:

```bash
pytest -q
python benchmarks/run_all.py
```

---

## Design principles

**Deterministic.** No probabilistic model or LLM participates in semantic classification.

**Repository-aware.** A changed signature is only the beginning. Canary follows that interface into callers that depend on it.

**Conservative.** When compatibility cannot be justified from static evidence, Canary reports `UNKNOWN`.

**Explainable.** Every finding maps to a concrete compatibility rule, changed symbol, source location, and affected call site.

**Reproducible.** Performance, scaling, determinism, and semantic behavior are backed by executable benchmark suites.

**PR-native.** Results surface directly through GitHub Checks and the CLI.

### Limitations

Canary is a lightweight static analysis system, not a complete Python interpreter or whole-program type engine. Current constraints include:

- Python-only analysis
- no runtime type inference
- limited instance-method resolution
- no dynamic import resolution
- no monkey-patch or reflection modeling
- no full interprocedural return-value consumption analysis
- ambiguous dynamic argument binding may remain `UNKNOWN`

These boundaries are deliberate: unsupported certainty is treated as a limitation, not hidden behind a confident classification.

---

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3.11+ |
| Semantic analysis | Python `ast` |
| API / webhook | FastAPI |
| GitHub integration | GitHub Apps, Checks API, REST API |
| CLI | Typer |
| Terminal presentation | Rich |
| Configuration | Pydantic Settings |
| HTTP client | HTTPX |
| Testing | pytest, pytest-asyncio |
| CI/CD | GitHub Actions |

---

## Roadmap

### Shipped

- [x] Python AST analysis
- [x] 7 semantic compatibility classes
- [x] Repository-wide symbol and call-site indexing
- [x] Import and alias resolution
- [x] Argument-aware static binding
- [x] `BREAKS / UNAFFECTED / UNKNOWN` classification
- [x] GitHub Checks with inline annotations
- [x] CLI
- [x] 88-test regression suite
- [x] 100-case seeded semantic mutation benchmark
- [x] Repository scaling benchmark

### Next

- [ ] Deeper Python type inference
- [ ] Instance-method resolution
- [ ] Interprocedural data-flow analysis
- [ ] Historical real-world regression corpus
- [ ] External open-source repository evaluation
- [ ] Configurable repository policies
- [ ] Additional language support

---

## Project structure

```
canary/
├── app/
│   ├── analysis/
│   │   ├── analyzer.py
│   │   ├── ast_analyzer.py
│   │   ├── call_validation.py
│   │   ├── compatibility.py
│   │   ├── diff_parser.py
│   │   ├── impact.py
│   │   ├── repository_analyzer.py
│   │   └── risk_rules.py
│   ├── github/
│   │   ├── auth.py
│   │   ├── checks.py
│   │   ├── client.py
│   │   └── presentation.py
│   ├── services/
│   │   └── pr_analysis.py
│   ├── terminal/
│   │   └── presentation.py
│   ├── cli.py
│   ├── config.py
│   ├── main.py
│   └── models.py
├── tests/
│   ├── integration/
│   └── unit/
├── benchmarks/
│   ├── canary_repository_benchmark.py
│   ├── scaling_benchmark.py
│   ├── semantic_rules_benchmark.py
│   ├── semantic_mutation_benchmark.py
│   ├── run_all.py
│   └── latest_results.txt
├── .github/workflows/
├── benchmark.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## License

MIT

---

<p align="center">
  made by marie with ☕
</p>