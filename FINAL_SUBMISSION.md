# Final Submission — Development of Smart Code Inspection Platform with Vulnerability Detection System – Group 2

**Infosys Internship Project.** Application/platform name: **Sentinel**.

## Project Title
**Development of Smart Code Inspection Platform with Vulnerability Detection System – Group 2**
(Application/platform: Sentinel)

## Problem Statement
Manual code review is slow, inconsistent, and easy to skip under deadline
pressure, especially for security-relevant issues (SQL injection,
hardcoded secrets, command injection, weak cryptography) that don't
surface as obvious bugs. Junior developers in particular lack a fast,
consistent way to get both a structural code-quality review and a
security review on the same submission, along with concrete remediation
guidance grounded in established secure-coding references.

## Objectives
1. Accept a code submission (paste or file upload), detect its language,
   and validate its syntax before analysis.
2. Run structural code-quality analysis and OWASP-aligned security
   analysis as parallel agents.
3. Turn raw findings into remediation guidance (root cause, fix,
   corrected-code example) and an overall PR-style verdict.
4. Ground a conversational assistant in a secure-coding knowledge base so
   answers cite real reference material, not free-floating LLM text.
5. Produce a professional, exportable report (PDF/Markdown/JSON) suitable
   for sharing outside the tool.
6. Validate all of the above against real code samples with measured
   (not assumed) accuracy.

## Technologies / Libraries Used
| Layer | Technology |
|---|---|
| Backend framework | Flask 3.x |
| Python static analysis | `ast` (stdlib), `radon` (cyclomatic complexity + Maintainability Index) |
| Python security scan | `bandit` (industry-standard SAST), subprocess-invoked |
| Java parsing | `javalang` (pure-Python Java AST parser) |
| RAG / retrieval | `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`) |
| LLM (optional tier) | Google Gemini via `google-genai`, only if `GEMINI_API_KEY` is set |
| Persistence | JSON-file-backed in-memory store (`storage.py`) — adequate for a demo/single-process app |
| Report generation | `reportlab` (Platypus) for PDF; native Python for Markdown/JSON |
| Frontend | Single-page HTML/CSS/vanilla JS app (`frontend/ai-code-review-platform.html`) |
| Testing | `pytest`, Flask's `test_client()` |

## Architecture / Workflow
```
Submission (paste/upload)
        |
Submission Module  ->  language detection, syntax validation (Milestone 1)
        |
   Orchestrator (ThreadPoolExecutor, 2 workers)
        |-- Code Analysis Agent  (ast/radon or javalang; LLM tier optional)
        |-- Security Vulnerability Agent  (bandit for Python; regex fallback for Java; LLM tier optional)
        |
   merged findings
        |
Remediation Agent  ->  per-finding fix + corrected-code example (Milestone 3)
        |
PR Summary Agent   ->  severity-weighted scores, verdict, executive summary (Milestone 3)
        |
Report Generation Module  ->  PDF / Markdown / JSON (Milestone 4)
        |
Frontend  ->  Findings dashboard, Reports page, Knowledge Base page, AI Assistant

Conversational Assistant (separate path):
  user question -> TF-IDF retriever over knowledge_base/*.md -> grounded
  answer (+ visible "Answer generated using Knowledge Base" source tag)
```

## Agents Implemented
1. **Code Analysis Agent** (`agents/code_analysis_agent.py`) — structural
   bugs/code smells via `ast` (Python) or `javalang` (Java), LLM tier
   optional, regex last resort.
2. **Security Vulnerability Agent** (`agents/security_agent.py`) — OWASP-
   aligned findings via `bandit` (Python) or a shared regex rule table
   (Java/fallback), LLM tier optional.
3. **Remediation Agent** (`agents/remediation_agent.py`) — maps each
   finding to a recommendation + corrected-code example.
4. **PR Summary Agent** (`agents/pr_summary_agent.py`) — severity-weighted
   scores, Maintainability Index integration (via radon when available),
   PR verdict (Approve / Approve with suggestions / Request changes /
   Block), executive summary text.

## Modules Implemented
- **Submission Module** — `submission/detector.py`, `submission/routes.py`
- **Analysis Module (orchestration)** — `agents/orchestrator.py`,
  `analysis/routes.py`
- **RAG Knowledge Base** — `rag/indexer.py`, `rag/retriever.py`,
  `rag/routes.py`, 4 knowledge-base documents
- **Conversational Assistant** — `chat/routes.py`
- **Report Generation Module** (Milestone 4) — `report/generator.py`,
  `report/routes.py`
- **Frontend SPA** — `frontend/ai-code-review-platform.html`

## Milestone Status

### Milestone 1 — Submission Module + RAG foundation: **100%**
Language detection (extension + signature regex fallback), real syntax
validation (`compile()` for Python; balanced-token check for others), the
TF-IDF knowledge base index. Verified live via `POST /api/submissions/text`
for both a `.py` and a `.java` file in this session.

### Milestone 2 — Code Analysis + Security agents (parallel): **100%**
Real AST-based Python analysis (`ast` + `radon`), real Java AST analysis
(`javalang`), real `bandit` security scanning for Python, documented regex
fallback where no offline equivalent exists. Verified live for all three
samples.

### Milestone 3 — Remediation, PR Summary, Conversational Assistant: **100%**
Per-finding remediation with corrected-code examples, severity-weighted PR
verdicts, and a knowledge-base-grounded chat assistant that visibly cites
its sources. Verified live: 3-turn conversation, sources returned for
grounded questions.

### Milestone 4 — Report Generation, Testing, Validation, Documentation: **~97%**
PDF/Markdown/JSON report generation wired to real pipeline output; 28
automated tests, all passing; validation run against 3 real samples with
an honestly-measured accuracy table; `DEMO_GUIDE.md` and this document.
The remaining ~3% is presentation/delivery of the live demo itself, which
is outside what can be verified by automated testing.

## Testing Results
Command: `python -m pytest tests/ -v`

**28 tests collected, 28 passed, 0 failed, 0 skipped.** (Re-run and
confirmed in this session, in addition to a separate live HTTP smoke test
against a running server covering: Python submission, Java submission,
full pipeline for all 3 samples, PDF/Markdown/JSON report generation for
all 3 analyses, knowledge-base document listing, knowledge-base search,
and a grounded chat reply with sources — all via real HTTP requests, not
just the pytest test client.)

Coverage areas: submission (language detection, syntax validation, both
valid and invalid Python), full pipeline for Python and Java, report
generation and 404 handling, RAG retrieval for realistic secure-coding
questions, multi-turn conversational assistant behavior, remediation
completeness (every finding has a non-generic root cause / fix /
corrected code / best practice), and severity-scoring consistency
(monotonic weighting, deterministic, never negative, correct verdict
thresholds).

## Validation Accuracy (measured, not assumed)

| Sample | Expected characteristic | Detected? |
|---|---|---|
| 1 — simple Python | Mutable default argument | ✅ |
| 2 — vulnerable Python | SQL injection | ✅ |
| 2 — vulnerable Python | Hardcoded password | ✅ |
| 2 — vulnerable Python | Command injection | ✅ |
| 2 — vulnerable Python | Weak crypto (MD5) | ✅ |
| 2 — vulnerable Python | Bare except | ✅ |
| 3 — Java | SQL injection | ✅ |
| 3 — Java | Command injection | ✅ |
| 3 — Java | Empty catch block | ✅ |
| 3 — Java | Too many parameters | ✅ |
| 3 — Java | Hardcoded secret field | ❌ |

**10 / 11 correctly detected (≈91%).** This is not reported as 100%
because it isn't — see Known Limitations.

## Known Limitations
1. **Java hardcoded-secret detection gap.** The security agent's regex
   rule for hardcoded secrets requires a `\b` word boundary before
   keywords like `password`; a camelCase Java field (`dbPassword`) doesn't
   match. Python's bandit-backed scan does not have this gap. Documented,
   not silently patched, since fixing it touches a shared rule table also
   used by Python's fallback path.
2. **Java has no offline SAST engine.** There is no pure-Python
   equivalent of bandit for Java, so Java security scanning always uses
   the regex fallback tier, never a library tier.
3. **Persistence is a JSON file**, not a database — fine for a demo/single
   process, not for concurrent multi-user production use.
4. **RAG is TF-IDF/cosine similarity** over 4 markdown documents — proves
   the retrieve-and-ground pattern correctly, but is not a production-
   scale embedding index.
5. **LLM tier untested in this environment** (no `GEMINI_API_KEY`
   configured here) — only the library-based and regex-fallback tiers
   were exercised in testing and the live smoke test.

## Future Scope
- Replace the Java regex security scanner with a javalang-driven,
  AST-based rule set (removing limitation #1 and reducing #2).
- Move persistence to a real database (SQLite at minimum) for multi-user
  use and concurrent submissions.
- Add authentication and per-user analysis history.
- Add PDF report caching so repeated downloads of the same analysis don't
  re-render.
- Expand the knowledge base and evaluate a proper embedding-based
  retriever if the document set grows significantly.
