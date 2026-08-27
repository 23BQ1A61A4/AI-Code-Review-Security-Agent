# Milestone 4 — Development of Smart Code Inspection Platform with Vulnerability Detection System – Group 2

**Infosys Internship Project.** Application/platform name: **Sentinel**.

This document covers only what was added/changed for Milestone 4. It assumes
Milestones 1–3 (submission module, multi-agent analysis pipeline, remediation
agent, PR summary agent, RAG knowledge base, conversational assistant) are
already implemented, which they are — see `README.md` and the Milestone 2/3
`.docx` files in this folder for that work.

## 1. What Milestone 4 adds

| Area | New files |
|---|---|
| Report generation | `backend/app/report/generator.py`, `backend/app/report/routes.py` |
| Validation samples | `validation/samples/sample1_simple.py`, `sample2_vulnerable.py`, `sample3_sample.java` |
| Validation runner | `validation/run_validation.py` (+ generated `validation_report.json`, `validation_report.md`, and 3 PDF reports) |
| Automated tests | `tests/conftest.py`, `tests/test_end_to_end.py`, `tests/test_rag_and_chat.py`, `tests/test_remediation_and_severity.py` |
| Frontend | Two buttons added to the Results view and Reports view (`Download PDF`), wired to the new `/api/report/<id>/pdf` endpoint. No other UI was changed. |

Nothing in Milestones 1–3 was rewritten. `orchestrator.py`, all four agents,
`rag/indexer.py`, `rag/retriever.py`, `chat/routes.py`, and `submission/detector.py`
are untouched.

## 2. Report Generation Architecture

`build_report_data(record)` in `report/generator.py` takes the exact dict
already saved by `POST /api/analysis/run` (produced by
`agents.orchestrator.run_pipeline`) and normalizes it into a report model:
submission info, language, PR summary, verdict, overall score, severity
breakdown, a per-finding list (each with root cause / recommended fix /
corrected code example / best practice), and a prioritized roadmap of
Critical/High items.

No values are invented. Per-finding recommendation text and corrected-code
examples are read from `remediation_agent`'s own template resolvers
(`_local_fix_for_security` / `_local_fix_for_bug`), which are imported, not
duplicated. `root_cause` and `best_practice` text is a small category-level
reference table added in the report module, keyed by the exact same `kind`
vocabulary the security agent's rule table and bandit-test-ID map already
use — it mirrors the existing `SECURITY_TEMPLATES` pattern in
`remediation_agent.py` rather than introducing a new mechanism. This lets
every finding in the PDF get a complete remediation block, since the
pipeline's own `fixes` list is intentionally capped to 4 items for the chat
assistant's use case.

Three renderers consume the same data model:
- `render_pdf()` — reportlab Platypus (`SimpleDocTemplate` + `Paragraph`/`Table`).
- `render_markdown()` — plain Markdown string.
- `render_json()` — the report data model as-is.

### Endpoints (new)

```
GET /api/report/<analysis_id>/pdf         -> application/pdf
GET /api/report/<analysis_id>/pdf?download=1  -> forces a download instead of inline view
GET /api/report/<analysis_id>/markdown    -> text/markdown
GET /api/report/<analysis_id>/json        -> application/json
```

All three 404 if `analysis_id` doesn't exist in `storage`. `analysis_id` is
the `id` field returned by `POST /api/analysis/run`.

## 3. Testing approach

`tests/` uses `pytest` against a real `flask.Flask.test_client()` — every
test calls the actual HTTP routes, which call the actual agents (`ast`,
`radon`, `bandit`, `javalang` when installed; documented fallbacks
otherwise). No responses are mocked and no expected output is hardcoded
into the app itself — only the *input* samples are fixed, per the
requirement.

- `test_end_to_end.py` — submission → language detection → syntax
  validation → analysis pipeline → findings → report generation, for
  Python and Java, plus negative cases (empty code, invalid syntax, unknown
  report id).
- `test_rag_and_chat.py` — RAG retrieval for three realistic secure-coding
  questions, empty-query edge case, and a 3-turn conversational-assistant
  flow (flag → explain → remediate → best-practice question) verifying
  grounding sources are returned.
- `test_remediation_and_severity.py` — every finding in a generated report
  has a non-empty, finding-specific remediation block; SQL-injection fixes
  actually mention parameterization; severity scoring is monotonic,
  deterministic, and never negative; PR verdict logic blocks on Critical
  and approves clean code.

**Actual result of the last run:** see the final chat response for the
exact `pytest` output — 28 tests, 28 passed, 0 failed, run in this
environment with `bandit`, `radon`, and `javalang` installed (so the real
tier-2 library path executed, not the regex fallback, for every sample).

## 4. Three demo samples

| Sample | Language | Purpose |
|---|---|---|
| `validation/samples/sample1_simple.py` | Python | One basic code-quality issue (mutable default argument) |
| `validation/samples/sample2_vulnerable.py` | Python | Five realistic security issues: SQL injection, hardcoded password, command injection (shell), weak hash (MD5), bare except |
| `validation/samples/sample3_sample.java` | Java | SQL injection, command injection (`Runtime.exec`), empty catch block, too-many-parameters method, and a hardcoded field (see limitation below) |

Run `python validation/run_validation.py` (from `backend/`, or with
`backend` on `PYTHONPATH`) to regenerate `validation_report.json`,
`validation_report.md`, and a real PDF report per sample.

## 5. Detection accuracy — actual results (not claimed, measured)

| Sample | Expected characteristic | Actually detected | Result |
|---|---|---|---|
| 1 | Mutable default argument | `Mutable default argument` (Medium), via `ast` | ✅ |
| 2 | SQL injection | `Hardcoded Sql Expressions` (bandit), `Critical` in the regex path / `Medium` per bandit's own severity | ✅ |
| 2 | Hardcoded secret | `Hardcoded Password String` (bandit) | ✅ |
| 2 | Command injection | `Start Process With A Shell` (bandit), `Critical` | ✅ |
| 2 | Weak crypto (MD5) | `Hashlib` (bandit), `Critical` | ✅ |
| 2 | Bare except | `Try Except Pass` (bandit) + `Bare except clause` (ast) | ✅ |
| 3 | SQL injection | `Possible SQL Injection (string-built query)` (Critical) | ✅ |
| 3 | Command injection | `Command Injection` (Critical) | ✅ |
| 3 | Empty catch block | `Empty catch block — exception silently swallowed (1x)` code smell, via `javalang` | ✅ |
| 3 | Too many parameters | `Method with too many parameters` (Low), via `javalang` | ✅ |
| 3 | Hardcoded secret (`dbPassword`) | **Not flagged** | ❌ |

**10 / 11 (≈91%)** of the deliberately-planted characteristics across the
three samples were detected. This is not 100%, and that is reported
honestly rather than adjusted.

**Known gap (not fixed, documented instead):** the security agent's
`hardcoded_secret` regex requires a `\b` word boundary before the keyword
(`password`, `secret`, etc.). Java's conventional camelCase field name
`dbPassword` has no word boundary before `Password`, so it doesn't match —
this is the Java fallback's regex scanner (bandit only covers Python; Java
has no bandit-equivalent available offline, as `security_agent.py` already
documents). Fixing this regex was out of scope for "make only necessary
changes for Milestone 4" and risks changing Milestone 2 behavior for
existing Python detections that rely on the same rule table, so it's
recorded here as a limitation rather than patched silently.

## 6. Remediation quality validation

For every finding in a generated report, `root_cause`, `recommended_fix`,
`corrected_code_example`, and `best_practice` are non-empty and specific to
that finding's category (verified in
`tests/test_remediation_and_severity.py`). SQL-injection findings are
checked to actually mention parameterization/binding, not generic text.
Findings covered by the existing template library never fall back to the
generic "review this finding" placeholder.

## 7. RAG retrieval validation

`tests/test_rag_and_chat.py` queries the live TF-IDF retriever with three
realistic questions (SQL injection prevention, password storage, input
validation) and asserts the returned chunks are topically relevant, plus
verifies an empty query returns no results rather than an arbitrary
citation. The knowledge base itself (`rag/knowledge_base/*.md`) was not
modified.

## 8. Conversational assistant validation

A four-turn conversation (flag a vulnerability from a real analysis →
explain it → ask for a fix → ask a general secure-coding best-practice
question) is exercised against `/api/chat`, checking that each reply is
non-empty and that knowledge-base sources are actually returned for
grounded questions, using the real `analysis_context` payload from a
completed pipeline run.

## 9. Report completeness validation

For all three samples, JSON, Markdown, and PDF reports are generated from
the real analysis record and checked for: correct filename/language,
severity-breakdown presence, non-empty findings, a valid `%PDF-` header,
and a plausible non-trivial file size (see `test_report_generation_for_each_sample`
and the standalone `validation/run_validation.py` run, which also writes
the three PDFs to disk under `validation/`).

## 10. How to run

### Install
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # optional — only needed for the Gemini LLM tier
```

### Run the app
```bash
python server.py
# open http://localhost:5000
```

### Run in VS Code
1. Open the project root folder in VS Code.
2. Open a terminal (`` Ctrl+` ``), `cd backend && pip install -r requirements.txt`.
3. Run `python server.py` (or use the VS Code "Run Python File" on `backend/server.py` — note the actual entry point is the repo-root `server.py`, so run that one).
4. Open the printed local URL in a browser.

### Configure `GEMINI_API_KEY`
Copy `backend/.env.example` to `backend/.env` and set
`GEMINI_API_KEY=your-key-here`. This is optional — every agent has a real,
non-LLM fallback (`ast`/`radon`/`bandit`/`javalang`, or regex as the last
resort), so the app runs fully offline without it.

### Run the tests
```bash
pip install pytest
python -m pytest tests/ -v
```

### Generate a report for a specific submission
```bash
curl -X POST http://localhost:5000/api/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"code": "...", "language": "Python", "filename": "example.py"}'
# take the "id" from the response, then:
curl -o report.pdf "http://localhost:5000/api/report/<id>/pdf"
curl "http://localhost:5000/api/report/<id>/markdown"
curl "http://localhost:5000/api/report/<id>/json"
```

### Run the three demo scenarios
```bash
cd backend
python ../validation/run_validation.py
# writes validation/validation_report.json, validation_report.md,
# and report_sample{1,2,3}_*.pdf
```

## 11. Limitations

- Java has no offline SAST-equivalent to bandit; its security scan uses the
  same regex rule table as the Python fallback, which has the word-boundary
  gap documented in §5.
- `storage.py` is a JSON-file-backed dict, adequate for a demo/single
  process, not a production datastore.
- The RAG index is TF-IDF/cosine similarity over 4 markdown documents —
  good enough to demonstrate the retrieve→ground pattern, not a
  production-scale embedding index.
- The LLM tier for every agent is untested in this environment (no
  `GEMINI_API_KEY` configured here); only the library and regex-fallback
  tiers were exercised.

## 12. Future scope

- Expand the Java security rule set with a proper AST-based scan (e.g. a
  javalang-driven equivalent of bandit's checks) instead of the regex
  fallback.
- Add authentication and per-user submission history instead of a single
  shared JSON store.
- Add a PDF report caching layer so repeated downloads of the same
  analysis don't re-render.
