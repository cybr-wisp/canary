# Canary 🐤

**Catch risky API changes before they merge.**

Canary is a GitHub pull request analysis tool that detects potentially breaking Python function signature changes and surfaces them directly in GitHub Checks or from the terminal.

Instead of treating every diff as equally risky, Canary looks for changes to callable interfaces that may affect downstream code.

---

## What Canary detects

Canary v1 focuses on a small, deterministic set of regression signals.

It currently detects changes to Python function signatures, including modifications to:

- function names
- parameters
- default values
- type annotations
- return annotations
- synchronous vs. asynchronous declarations

Public function signature changes are treated as higher risk than private helper changes.

Example:

```diff
-def create_user(name: str) -> User:
+def create_user(name: str, organization_id: int) -> User:
```

Canary flags the change before it reaches production.

---

## GitHub Checks

Canary runs automatically when a pull request is:

- opened
- updated
- reopened
- marked ready for review

It analyzes the changed Python files and publishes a GitHub Check containing the detected risk level and supporting evidence.

<!--
Add before release:

![Canary GitHub Check](docs/images/github-check.png)
-->

---

## Terminal

Canary can also inspect a pull request directly from the command line.

```bash
canary inspect https://github.com/owner/repository/pull/123
```

The CLI retrieves the pull request through the Canary GitHub App and renders the analysis in the terminal.

<!--
Add before release:

![Canary terminal output](docs/images/terminal.png)
-->

---

## Architecture

```text
                         GitHub Pull Request
                                  │
                           webhook event
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     FastAPI     │
                         │     Webhook     │
                         └────────┬────────┘
                                  │
                                  ▼
┌────────────────┐       ┌─────────────────┐
│   Canary CLI   │──────▶│   PR Analysis   │
│    inspect     │       │     Service     │
└────────────────┘       └────────┬────────┘
                                  │
                             GitHub API
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Changed Files + │
                         │      Diffs      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Diff Parser   │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Risk Rules    │
                         │                 │
                         │ signature diff  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ AnalysisResult  │
                         │ HIGH / MEDIUM   │
                         │      / LOW      │
                         └───────┬───┬─────┘
                                 │   │
                       ┌─────────┘   └─────────┐
                       ▼                       ▼
              ┌─────────────────┐     ┌─────────────────┐
              │  GitHub Check   │     │ Terminal Output │
              └─────────────────┘     └─────────────────┘
```

Canary intentionally keeps the v1 analysis pipeline deterministic. The same pull request produces the same findings without relying on an LLM.

---

## Installation

Canary requires Python 3.11 or newer.

Clone the repository:

```bash
git clone https://github.com/cybr-wisp/canary.git
cd canary
```

Create a virtual environment:

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

The package exposes the `canary` command:

```bash
canary --help
```

---

## GitHub App configuration

Canary runs as a GitHub App.

Create a `.env` file from the provided example:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure:

```env
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GITHUB_WEBHOOK_SECRET=

GITHUB_API_URL=https://api.github.com
LOG_LEVEL=INFO
```

The GitHub App should be configured to:

- receive `pull_request` webhook events
- read pull request metadata and changed files
- create GitHub Checks

Install the App on the repositories Canary should analyze.

---

## Running the webhook service

Start the FastAPI application:

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET /health
```

GitHub should send webhook events to:

```text
POST /webhook
```

For local development, expose the local server through a webhook-accessible tunnel and use that address as the GitHub App webhook URL.

---

## CLI usage

Once the GitHub App is installed on a repository:

```bash
canary inspect https://github.com/owner/repository/pull/123
```

Canary automatically resolves its GitHub App installation for the repository, fetches the pull request, analyzes the changed files, and renders the result.

---

## Analysis output

A Canary analysis contains:

- number of files analyzed
- number of Python files analyzed
- additions and deletions
- changed-line count
- functions inspected
- regression findings
- risk severity

Findings are classified as:

| Severity | Meaning |
| --- | --- |
| `HIGH` | Potentially breaking public interface change |
| `MEDIUM` | Risky change with more limited scope |
| `LOW` | Lower-confidence or lower-impact signal |

A high-risk finding causes the Canary GitHub Check to fail so the change is visible before merge.

---

## Tests

Run the complete test suite with:

```bash
pytest -v
```

The project includes unit and integration tests covering the core analysis pipeline, webhook authentication, GitHub Check behavior, CLI behavior, and presentation logic.

---

## Project structure

```text
canary/
├── app/
│   ├── analysis/
│   │   ├── analyzer.py
│   │   ├── diff_parser.py
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
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## Limitations

Canary v1 is intentionally narrow.

Current limitations include:

- Python only
- analysis is based on changed diff content rather than complete repository semantics
- only function signature regressions are currently modeled
- no cross-file dependency or call-site analysis
- no type inference
- dynamically generated APIs cannot be reliably inspected
- large or truncated GitHub patches may provide incomplete context
- Canary identifies regression signals; it does not prove that a change will fail at runtime

These constraints keep the first version deterministic and easy to understand while establishing the foundation for deeper semantic analysis.

---

## Roadmap

### v2.0 — Semantic regression analysis

Canary v2 expands analysis beyond textual diffs into repository-aware Python semantics.

Planned work includes:

- AST-based source analysis
- semantic API compatibility detection
- removed public API detection
- parameter addition, removal, and reordering analysis
- default-value compatibility analysis
- return-type change detection
- sync / async compatibility analysis
- repository-wide symbol indexing
- cross-file call-site resolution
- dependency and blast-radius analysis
- argument-aware call-site validation
- richer GitHub Check explanations
- richer CLI analysis output

### Future

Potential later work includes:

- additional programming languages
- deeper type and data-flow analysis
- framework-specific compatibility rules
- configurable repository policies
- CI integrations beyond GitHub Apps

---

## Philosophy

Most pull request tooling asks whether code is syntactically valid or stylistically clean.

Canary asks a different question:

> **What behavior or interface might this change break?**

v1 starts with deterministic signature-level signals. Future versions build toward repository-aware semantic regression analysis.

---

## License

See [`LICENSE`](LICENSE).