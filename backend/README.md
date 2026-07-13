# Backend — Modules 1-3 (Submission, Code Analysis, Security Vulnerability)

## Setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:
```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

For running the test suite, also install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Run the test suite

```bash
pytest -v
```

All tests mock the LLM call, so they run with no API key and no network access.

## Test the API

### 1. Health check
http://localhost:8000/api/health

### 2. Interactive API docs
http://localhost:8000/docs

### 3. Full flow (curl)
```bash
# Submit code
curl -X POST http://localhost:8000/api/submissions/text \
  -H "Content-Type: application/json" \
  -d '{"language":"Python","code":"cursor.execute(f\"SELECT * FROM users WHERE id={user_id}\")","filename":"demo.py"}'

# Run the Code Analysis Agent
curl -X POST http://localhost:8000/api/analysis/code/<id>

# Run the Security Vulnerability Agent (independent — separate endpoint, separate service)
curl -X POST http://localhost:8000/api/analysis/security/<id>
```

## Folder structure

```
backend/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── README.md
├── tests/
│   ├── test_static_analyzers.py
│   ├── test_code_analysis_agent.py
│   ├── test_security_rules.py              NEW — 26 tests, no mocking
│   └── test_security_vulnerability_agent.py NEW — 9 tests, LLM mocked
└── app/
    ├── main.py
    ├── config.py
    ├── models/
    │   ├── submission.py
    │   ├── analysis.py
    │   └── security.py                      NEW — SecurityFinding, SecurityAnalysisResult
    ├── services/
    │   ├── submission_service.py
    │   ├── analysis_service.py
    │   └── security_service.py              NEW — SecurityAnalysisService
    ├── api/
    │   ├── submission_routes.py
    │   ├── analysis_routes.py
    │   └── security_routes.py               NEW — /api/analysis/security/*
    ├── agents/
    │   ├── base.py
    │   ├── llm_client.py
    │   ├── static_analyzers.py
    │   ├── code_analysis_agent.py
    │   ├── security_vulnerability_agent.py  NEW — the agent itself
    │   └── security/                        NEW subpackage
    │       ├── scanner_base.py               SecurityScanner interface
    │       ├── static_rules.py               regex rule engine, 17 categories
    │       ├── external_tools.py             Bandit/Semgrep/SpotBugs/Checkstyle placeholders
    │       └── merge.py                      duplicate-finding merge logic
    ├── rag/       (placeholder — later module)
    └── reports/   (placeholder — later module)
```

## Module 3 architecture

```
Submission
    │
    ▼
SecurityVulnerabilityAgent.run(submission)
    │
    ├── for each scanner in self._scanners:   (default: [StaticSecurityRuleEngine()])
    │       try: findings += scanner.scan(code, language, filename)
    │       except: continue   ← one scanner failing never stops the others
    │
    ├── try: findings += LLM semantic scan (separate call)
    │       except: pass       ← LLM failing never loses static findings
    │
    ├── merge_findings(findings)   ← dedupe same category + nearby line
    │
    └── SecurityAnalysisResult(security_score, highest_risk_score, findings)
```

**Pluggability**: `SecurityScanner` (app/agents/security/scanner_base.py) is the contract every finding source implements — `StaticSecurityRuleEngine` today, and `BanditScanner`/`SemgrepScanner`/`SpotBugsScanner`/`CheckstyleScanner` (currently empty placeholders in `external_tools.py`) later. Wiring in a real tool means writing its `scan()` body and adding it to the agent's `scanners` list — `SecurityVulnerabilityAgent.run()`, `SecurityAnalysisService`, and the API routes never change.

**Merge logic** (`agents/security/merge.py`): findings are grouped by `(category, line number within 3 lines)`. A group of 1 passes through unchanged. A group of 2+ is merged into one finding: the highest-severity/highest-confidence member becomes the base, every unique evidence string from the group is concatenated (so nothing is lost even if static and LLM worded it differently), confidence is boosted slightly (capped at 1.0) since independent agreement is itself a signal, and `merged_from` records every contributing source.

## Known limitations (documented honestly)

- **Static rule coverage varies by category.** Mechanical patterns (SQL Injection, Command Injection, Hardcoded Secrets, Insecure Deserialization, Unsafe Cryptography, CSRF-disable flags) are reliably regex-detectable. A few categories (Broken Access Control, Missing Input Validation) are inherently hard to detect via regex — the static engine provides only a very narrow signal or none, and the LLM semantic pass is explicitly told to focus there. This mirrors Module 2's honest static-vs-LLM split.
- **Regex-based detection has real false-positive/false-negative risk** — e.g. the Hardcoded Secrets rule will flag `password = "changeme12345"` even though that's a placeholder, and the Weak Authentication heuristic can miss password comparisons that don't match its exact pattern. Confidence scores per rule reflect this (0.4-0.8 range, not uniformly high).
- **The 4 external tool integrations are architectural placeholders, not working scanners** — `BanditScanner`, `SemgrepScanner`, `SpotBugsScanner`, `CheckstyleScanner` all currently return `[]`. The interface is real and tested (see `test_scanner_failure_does_not_crash_agent`), but actually running Bandit/Semgrep/SpotBugs/Checkstyle requires those binaries installed and isn't done in this module, per your "design for it, don't necessarily wire it up yet" framing.
- **Merge is heuristic** (category + nearby line), not a semantic "are these really the same vulnerability" check — it can occasionally merge two genuinely distinct issues that happen to sit close together in the same category, or miss a true duplicate that landed more than 3 lines apart.
- **`SecurityAnalysisService.run_security_analysis` couldn't be executed via `pytest` in this sandbox** (no network to install `pydantic`/`anthropic` here) — I manually re-verified all 9 agent-level test scenarios with a stubbed `anthropic`/`pydantic` and confirmed real, correct behavior (see the tool call transcript in this conversation). Run `pytest -v` in your own environment for the official confirmation. The 26 `test_security_rules.py` tests need no such stubbing and I ran them for real.


