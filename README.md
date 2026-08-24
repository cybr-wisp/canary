# Canary 🐤

**Repository-aware semantic regression detection for GitHub pull requests.**

Canary analyzes Python API changes, traces their impact across a repository, and identifies call sites that are likely to break before the pull request is merged.

It runs as a GitHub App or from the command line and produces deterministic, explainable findings directly inside the developer workflow.

```text
API change
    ↓
semantic compatibility analysis
    ↓
repository-wide call-site discovery
    ↓
argument-aware validation
    ↓
confirmed breakages
```

---

## Why Canary

A pull request can pass syntax checks, unit tests, linting, and type checking while still introducing an interface change that breaks downstream code.

For example:

```diff
-def authenticate(token):
+def authenticate(token, strict):
     ...
```

Elsewhere in the repository:

```python
from auth import authenticate


def login():
    return authenticate("demo-token")
```

The function definition is valid Python.

The call site is valid Python.

But together, the change is incompatible.

Canary detects the API change, finds the affected call site, validates the new signature against the existing arguments, and reports the breakage:

```text
🔴 HIGH RISK

REQUIRED_PARAMETER_ADDED

Required parameter `strict` was added to `authenticate`.

Repository impact
1 call site analyzed
1 confirmed breaking

Confirmed breakages
caller.py:5
```

---

## Canary v2

Canary v2 moves beyond diff-level signature inspection into **repository-aware semantic regression analysis**.

The analysis pipeline combines:

- Python AST analysis
- semantic API compatibility rules
- repository-wide symbol and call-site indexing
- blast-radius analysis
- argument-aware call validation
- GitHub Check annotations
- terminal presentation

The result is a deterministic answer to a more useful question than simply whether code changed:

> **What existing code could this change break?**

---

## What Canary detects

Canary currently analyzes Python function and method interfaces.

### Public API removal

```diff
-def create_user(name: str):
-    ...
```

Canary reports:

```text
PUBLIC_API_REMOVED
```

---

### Required parameter addition

```diff
-def create_user(name: str):
+def create_user(name: str, organization_id: int):
     ...
```

Canary reports:

```text
REQUIRED_PARAMETER_ADDED
```

It then searches the repository for existing callers and determines whether each call remains valid.

---

### Parameter removal

```diff
-def create_user(name: str, active: bool):
+def create_user(name: str):
     ...
```

Canary reports:

```text
PARAMETER_REMOVED
```

---

### Parameter reordering

```diff
-def create_user(name: str, age: int):
+def create_user(age: int, name: str):
     ...
```

Canary reports:

```text
PARAMETER_REORDERED
```

This matters particularly for positional callers.

---

### Parameter default removal

```diff
-def create_user(name: str, active: bool = True):
+def create_user(name: str, active: bool):
     ...
```

Canary reports:

```text
PARAMETER_DEFAULT_REMOVED
```

---

### Return annotation change

```diff
-def get_user() -> str:
+def get_user() -> int:
     ...
```

Canary reports:

```text
RETURN_TYPE_CHANGED
```

---

### Sync / async behavior change

```diff
-def fetch_user():
+async def fetch_user():
     ...
```

Canary reports:

```text
ASYNC_BEHAVIOR_CHANGED
```

Repository callers are inspected to determine whether the new behavior is compatible with how the function is used.

---

## Repository-aware impact analysis

Detecting an API change is only the first stage.

Canary builds a lightweight repository index to determine where the changed symbol is used.

For each semantic compatibility finding, Canary can associate repository call sites such as:

```text
app/api.py:14
services/users.py:31
workers/sync.py:87
```

It then evaluates those callers against the changed API.

Each call site is classified as:

| Status | Meaning |
| --- | --- |
| `BREAKS` | Canary can statically confirm that the call is incompatible |
| `UNAFFECTED` | The existing call remains compatible |
| `UNKNOWN` | Static analysis cannot safely determine compatibility |

This lets Canary distinguish between:

```text
Potentially risky API change
```

and:

```text
Confirmed repository breakage
```

---

## Argument-aware validation

Canary performs static argument binding against changed function signatures.

The validator accounts for:

- positional arguments
- keyword arguments
- required parameters
- optional parameters
- positional-only parameters
- keyword-only parameters
- duplicate argument binding
- excess positional arguments
- unexpected keyword arguments
- `*args`
- `**kwargs`
- awaited versus non-awaited calls

For example:

```python
def create_user(
    name: str,
    organization_id: int,
):
    ...
```

Existing call:

```python
create_user("Marie")
```

Canary can statically determine that the call is incompatible because the required `organization_id` argument is missing.

---

## GitHub Checks

Canary runs automatically when a pull request is:

- opened
- updated
- reopened
- marked ready for review

The GitHub Check summarizes:

- overall risk level
- detected compatibility findings
- files analyzed
- Python files analyzed
- functions inspected
- additions and deletions
- changed lines
- repository call sites analyzed
- confirmed breaking calls
- compatible calls
- calls requiring manual review

High-risk findings cause the Canary Check to fail so the regression is visible before merge.

Example:

```text
❌ 1 potential regression risk detected

🐤 CANARY

🔴 HIGH RISK

1 regression signal detected across 2 files.

Repository impact

Call sites analyzed      1
Confirmed breaking       1
Already compatible       0
Requires review          0

REQUIRED_PARAMETER_ADDED

Required parameter `strict` was added to `authenticate`.

Confirmed breakages

caller.py:5 — Call was valid before the API change but is
incompatible with the new signature.
```

Canary also creates inline GitHub annotations on affected source lines.

---

## CLI

The same analysis engine is available from the terminal.

```bash
canary inspect https://github.com/owner/repository/pull/123
```

Example:

```text
CANARY

HIGH RISK
REQUIRED_PARAMETER_ADDED

Required parameter `organization_id` was added to `create_user`.

Repository impact
1 call site analyzed
1 confirmed breaking

Confirmed breakages
app/api.py:14
```

The GitHub App and CLI share the same underlying analysis pipeline.

---

## Architecture

```text
                           GitHub Pull Request
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
               GitHub Webhook                Canary CLI
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │    PR Analysis    │
                         │      Service      │
                         └─────────┬─────────┘
                                   │
                    base SHA + head SHA
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
                 ▼                                   ▼
         Base Python sources                 Head repository
                                              Python sources
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │    Python AST     │
                         │     Analysis      │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │  Compatibility    │
                         │      Engine       │
                         └─────────┬─────────┘
                                   │
                 semantic compatibility findings
                                   │
                                   ▼
                         ┌───────────────────┐
                         │    Repository     │
                         │ Symbol/Call Index │
                         └─────────┬─────────┘
                                   │
                              call sites
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ Impact / Blast    │
                         │ Radius Analysis   │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ Argument-aware    │
                         │ Call Validation   │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │  AnalysisResult   │
                         └─────────┬─────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
            GitHub Check Run               Terminal Output
```

Canary's v2 analysis remains deterministic.

The same repository state and pull request produce the same findings without relying on an LLM.

---

## Analysis pipeline

A pull request is processed in the following order:

```text
1. Fetch changed files
2. Resolve BASE and HEAD commits
3. Load the HEAD Python repository snapshot
4. Build the repository symbol and call-site index
5. Load BASE and HEAD versions of changed Python files
6. Parse both versions into Python ASTs
7. Compare callable interfaces
8. Produce semantic compatibility findings
9. Find repository call sites for changed symbols
10. Estimate impact and blast radius
11. Validate callers against the new interface
12. Produce AnalysisResult
13. Render GitHub Check and/or CLI output
```

If a changed Python file cannot be parsed successfully, Canary can fall back to its diff-based analysis path rather than failing the entire pull-request analysis.

---

## Installation

Canary requires Python 3.11 or newer.

Clone the repository:

```bash
git clone https://github.com/cybr-wisp/canary.git
cd canary
```

Create a virtual environment.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

Install Canary:

```bash
pip install -e .
```

Verify the CLI:

```bash
canary --help
```

---

## GitHub App configuration

Canary runs as a GitHub App.

Create a `.env` file from the provided example:

### Windows

```powershell
Copy-Item .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

Configure:

```env
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GITHUB_WEBHOOK_SECRET=

GITHUB_API_URL=https://api.github.com
LOG_LEVEL=INFO
```

The GitHub App requires access to:

- pull request metadata
- repository contents
- GitHub Checks

It should receive `pull_request` webhook events.

Install the App on every repository Canary should analyze.

---

## Running the webhook service

Start Canary's FastAPI service:

```bash
uvicorn app.main:app --reload
```

Health endpoint:

```text
GET /health
```

For Canary v2:

```json
{
  "status": "ok",
  "service": "canary",
  "version": "2.0.0"
}
```

Webhook endpoint:

```text
POST /webhook
```

During local development, expose the FastAPI service through a webhook-accessible tunnel and configure the resulting address as the GitHub App webhook URL.

---

## CLI usage

Inspect a pull request:

```bash
canary inspect https://github.com/owner/repository/pull/123
```

Canary:

1. resolves the GitHub App installation for the repository
2. retrieves the pull request
3. fetches BASE and HEAD repository information
4. analyzes the changed Python APIs
5. evaluates repository call sites
6. renders the result in the terminal

---

## Risk model

Canary findings use three risk levels.

| Severity | Meaning |
| --- | --- |
| `HIGH` | Potentially breaking public interface or confirmed high-impact compatibility change |
| `MEDIUM` | Risky change with more limited scope |
| `LOW` | Lower-impact deterministic signal |

A high-risk finding causes the GitHub Check to fail.

The severity of semantic changes may also be informed by repository impact.

---

## Project structure

```text
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
│   │
│   ├── github/
│   │   ├── auth.py
│   │   ├── checks.py
│   │   ├── client.py
│   │   └── presentation.py
│   │
│   ├── services/
│   │   └── pr_analysis.py
│   │
│   ├── terminal/
│   │   └── presentation.py
│   │
│   ├── cli.py
│   ├── config.py
│   ├── main.py
│   └── models.py
│
├── tests/
│   ├── integration/
│   └── unit/
│
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Tests

Run the complete suite:

```bash
pytest -q
```

For verbose output:

```bash
pytest -v
```

The v2 test suite covers:

- AST extraction
- semantic compatibility rules
- repository symbol analysis
- cross-file call-site discovery
- blast-radius analysis
- argument-aware call validation
- pull-request orchestration
- GitHub authentication
- GitHub API behavior
- GitHub Check presentation
- CLI behavior
- terminal presentation
- webhook behavior
- regression fallbacks

The v2.0.0 release passes:

```text
88 passed
```

---

## Design principles

### Deterministic

Canary's core analysis does not depend on an LLM.

Findings are derived from repository structure, Python syntax, compatibility rules, and statically observable call behavior.

### Explainable

Every finding has a concrete reason.

Where possible, Canary reports the exact repository call sites affected by the change.

### Repository-aware

A signature change alone is not the complete story.

Canary attempts to determine how that changed interface is actually used elsewhere in the codebase.

### Conservative

When static analysis cannot reliably prove compatibility or incompatibility, Canary can classify the call site as requiring review rather than pretending to know more than it does.

### Pull-request native

The analysis appears directly where developers already review code: GitHub Checks, diff annotations, and the terminal.

---

## Limitations

Canary v2 intentionally remains a lightweight static analysis system.

Current limitations include:

- Python is the only language with semantic analysis
- symbol resolution is static and does not perform full runtime type inference
- instance-method resolution cannot reliably infer arbitrary object types
- dynamic imports may not be resolvable
- monkey-patched or dynamically generated APIs cannot be reliably modeled
- reflection and runtime dispatch may escape static call-site analysis
- calls using ambiguous `*args` or `**kwargs` may require manual review
- Canary tracks whether a parameter has a default, but does not currently compare the actual default expression value
- return-type analysis uses explicit annotations rather than whole-program type inference
- repository call-site analysis does not guarantee that every possible runtime call path is known
- Canary identifies deterministic compatibility risks; it does not prove that a change will fail in every runtime environment

These constraints are deliberate.

When Canary cannot statically justify a conclusion, the goal is to surface uncertainty rather than produce false precision.

---

## Roadmap

### v2.0 — Repository-aware semantic regression analysis

Released capabilities include:

- Python AST analysis
- semantic API compatibility detection
- public API removal detection
- required parameter addition detection
- parameter removal detection
- parameter reordering detection
- parameter default removal detection
- return annotation change detection
- sync / async compatibility detection
- repository-wide symbol indexing
- cross-file call-site discovery
- blast-radius analysis
- argument-aware call validation
- GitHub Check repository-impact summaries
- inline GitHub annotations
- terminal repository-impact reporting

### Future

Potential future work includes:

- additional programming languages
- deeper Python type inference
- richer instance-method resolution
- interprocedural data-flow analysis
- framework-specific compatibility rules
- configurable repository policies
- repository-specific severity thresholds
- additional CI integrations
- richer dependency graph visualization
- package-level compatibility analysis

---

## v1 → v2

Canary v1 established the deterministic PR-analysis pipeline:

```text
GitHub PR
→ diff parsing
→ signature-level risk rules
→ GitHub Check
```

Canary v2 extends that foundation into repository-aware semantic analysis:

```text
GitHub PR
→ BASE / HEAD source analysis
→ Python AST
→ semantic compatibility
→ repository call-site discovery
→ impact analysis
→ argument validation
→ confirmed breakages
→ GitHub Check / CLI
```

The key change is that Canary no longer stops at:

> This API changed.

It can now continue to:

> This API changed, these repository call sites use it, and these calls are no longer compatible.

---

## Philosophy

Most pull-request tooling asks:

> Does this code compile, lint, type-check, or pass tests?

Canary asks:

> **What existing behavior or interface might this change break?**

The goal is not to replace tests or static type checkers.

It is to add another layer of review focused specifically on behavioral compatibility across a changing codebase.

---

## License

See [`LICENSE`](LICENSE).