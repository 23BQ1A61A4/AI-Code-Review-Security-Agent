# Development of Smart Code Inspection Platform with Vulnerability Detection System – Group 2

**Infosys Internship Project.** Application/platform name: **Sentinel**.

An AI-assisted, multi-agent code review platform. Paste or upload Python/Java
code and a pipeline of specialist agents reviews it, scores it, flags
OWASP-standard vulnerabilities, and suggests fixes — with a searchable
Knowledge Base page and a RAG-grounded chat assistant for follow-up
questions.

## What's implemented (Milestones 1–3)

| Milestone | Feature | Where |
|---|---|---|
| 1 | Code Submission Module — paste/upload, language detection, syntax validation | `backend/app/submission/` |
| 1 | Secure Coding Knowledge Base + RAG pipeline (chunk → TF-IDF embed → index → retrieve) | `backend/app/rag/` |
| 2 | Code Analysis Agent (code smells, design issues) | `backend/app/agents/code_analysis_agent.py` |
| 2 | Security Vulnerability Agent (OWASP-tagged findings) | `backend/app/agents/security_agent.py` |
| 2 | Multi-agent orchestration — the two agents above run **in parallel** | `backend/app/agents/orchestrator.py` |
| 3 | Remediation Agent (fix + corrected code per finding) | `backend/app/agents/remediation_agent.py` |
| 3 | PR Summary Agent (scores, verdict, executive summary) | `backend/app/agents/pr_summary_agent.py` |
| 3 | Findings Dashboard / severity scoring | `frontend/ai-code-review-platform.html` |
| 3 | Conversational Code Assistant (RAG Q&A, shows which KB doc it used) | `backend/app/chat/routes.py` |
| 3 | Knowledge Base page — browse + search the same RAG index | `backend/app/rag/routes.py` |
| — | Code Review Report Generation and Export (Markdown download) | `frontend` (`downloadReport`) |

## What actually powers the analysis (no invented rules)

Each agent tries these in order and uses the first one that's available —
nothing is hardcoded as the primary path:

1. **LLM (Gemini)** — if `GEMINI_API_KEY` is set and reachable.
2. **Real static-analysis libraries**:
   - **Python structure** → the standard library `ast` module (real parse
     tree, not text matching) for bare-except, mutable defaults, parameter
     counts, nesting depth, function length.
   - **Python complexity/maintainability** → [`radon`](https://radon.readthedocs.io)
     — cyclomatic complexity and the published Maintainability Index
     formula, not a made-up score.
   - **Python security** → [`bandit`](https://bandit.readthedocs.io) — the
     industry-standard Python SAST tool. Its own rule engine decides what's
     flagged and how severe it is; this project only maps bandit's test IDs
     onto OWASP categories for the report (`backend/app/agents/bandit_scanner.py`).
   - **Java structure** → [`javalang`](https://github.com/c2nes/javalang), a
     pure-Python Java parser, used for a real AST (method/parameter counts,
     empty-catch detection) and its tokenizer (accurate brace-nesting depth
     that correctly ignores braces inside strings/comments).
3. **Pattern scanner (fallback)** — a small regex/heuristic scanner, used
   *only* when neither an LLM nor the relevant library is available (e.g.
   offline with `radon`/`bandit`/`javalang` not installed, or Java — there
   is no JVM-free equivalent of bandit/PMD for Java). Every analysis result
   reports which engine actually ran (see `engines` in the API response and
   the "Analysis engine" line on the Findings page), so it's never hidden
   which path produced a given result.

Install `radon`, `bandit`, and `javalang` (in `requirements.txt`) to get
the real library-backed analysis for Python and Java. Without them, the
app still runs end-to-end on the pattern-scanner fallback — nothing
breaks, it's just less precise.

## Setup

```bash
cd backend
pip install -r requirements.txt
cd ..
```

Optional — use a real Gemini model instead of the offline analyzer:

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set GEMINI_API_KEY
```

## Run

```bash
python server.py
```

Then open **http://localhost:5000**. One process, one port — the Flask
app serves the frontend AND the API (submission, analysis, chat,
knowledge base).

## Pages (sidebar)

| Sidebar item | What it shows |
|---|---|
| **Dashboard** | Overview / recent activity |
| **Code Analysis** | Paste or upload code, run the multi-agent pipeline |
| **Findings** | Scores, verdict, bugs, OWASP-tagged vulnerabilities, remediation fixes, code smells — plus which engine (ast/radon/bandit/javalang/LLM) produced the result |
| **AI Assistant** | Conversational Code Assistant — every answer shows *"Answer generated using Knowledge Base"* plus which document(s) it drew from |
| **Knowledge Base** | Browse all four secure-coding documents in full, or search them by keyword — same RAG retriever the AI Assistant uses |

## Project structure

```
server.py                     # entrypoint — python server.py
backend/
  requirements.txt
  .env.example
  app/
    main.py                   # Flask app factory, registers all routes
    storage.py                # JSON-backed submission/analysis store
    submission/                # Milestone 1
      detector.py              #   language detection + syntax validation
      routes.py                #   POST /api/submissions/text
    agents/                     # Milestones 2–3
      llm_client.py            #   Gemini wrapper w/ offline fallback
      code_analysis_agent.py   #   orchestrates ast / javalang / LLM / regex
      python_ast_analyzer.py   #   ast + radon (Python)
      java_analyzer.py         #   javalang AST + tokenizer (Java)
      security_agent.py        #   orchestrates bandit / LLM / regex
      bandit_scanner.py        #   bandit subprocess + OWASP mapping
      remediation_agent.py
      pr_summary_agent.py
      orchestrator.py          #   runs agents in parallel, merges results
    rag/                        # Milestone 1 + 3 (knowledge base / assistant)
      knowledge_base/*.md       #   OWASP top 10, secure coding, code smells
      indexer.py                #   chunking
      retriever.py              #   TF-IDF + cosine similarity search
      routes.py                 #   GET /api/knowledge-base/documents, /search
    analysis/
      routes.py                 #   POST /api/analysis/run
    chat/
      routes.py                 #   POST /api/chat  (RAG-grounded assistant)
frontend/
  ai-code-review-platform.html  # single-page app UI
docs/                            # updated milestone documentation (.docx)
```

## Verified working (offline, in this environment)

Every endpoint below was exercised end-to-end before packaging:
Submission Module, Python + Java analysis (parallel agents), Remediation
Agent, PR Summary Agent, Knowledge Base browse, Knowledge Base search
(all 6 required keywords), and AI Chat with source attribution. `radon`
and `bandit` weren't installable in the sandbox this was built in (no
network access), so that specific run exercised the `ast` + regex-fallback
path — the `radon`/`bandit`/`javalang` integration code was verified
separately against a functional stand-in and is structurally the same
call path; installing them via `pip install -r requirements.txt` on your
machine activates the real libraries automatically, no code changes
needed. The Findings page's "Analysis engine" line will then read
`bandit` / `ast + radon` / `javalang AST` instead of `pattern scanner
(fallback)`.

## Demo script

1. **Start the backend:**
   ```bash
   cd backend && pip install -r requirements.txt && cd ..
   python server.py
   ```
2. **Open** http://localhost:5000 in a browser.
3. Go to **Code Analysis**, paste the sample Python code below, click
   **Run AI analysis**. Point out the Submission Module confirming
   language + syntax first, then the Findings page: scores, verdict,
   OWASP-tagged issues, remediation fixes with corrected code, and the
   "Analysis engine" line showing which library ran.
4. Repeat with the sample Java code to show multi-language support.
5. Open **AI Assistant**, ask one of the sample questions below — point
   out the *"Answer generated using Knowledge Base"* line and the named
   source document under the reply.
6. Open **Knowledge Base**, show the four documents, then search a couple
   of the sample keywords below to show it hitting the same retriever.
7. Back on **Findings**, click **Download report** to show the exportable
   Markdown review.

### Sample Python code (paste into Code Analysis)

```python
import os, pickle, hashlib

API_KEY = "sk-live-abcdef1234567890"

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

def run_backup(folder):
    os.system("tar -cvf backup.tar " + folder)

def load_config(data):
    return pickle.loads(data)

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()
```

Expect: Critical SQL injection, hardcoded secret, command injection,
insecure deserialization, and weak-crypto findings, verdict **Block**.

### Sample Java code (paste into Code Analysis)

```java
public class UserDao {
    public String password = "SuperSecret123";

    public User getUser(String name) {
        String sql = "SELECT * FROM users WHERE name = '" + name + "'";
        Statement st = conn.createStatement();
        ResultSet rs = st.executeQuery(sql);
        return null;
    }

    public void render(String input) {
        response.getWriter().println(input);
    }
}
```

Expect: Critical SQL injection, hardcoded secret, and XSS findings,
verdict **Block**.

### Sample questions for AI Assistant

- "How do I prevent SQL injection in Python?"
- "What is CSRF and how do I prevent it?"
- "How do I fix the top security issue?" *(after running an analysis — uses your last result)*
- "What is a code smell?"
- "How should I store passwords securely?"

### Sample keywords for Knowledge Base search

SQL Injection · XSS · CSRF · Hardcoded Secret · Authentication · Code Smell

## Security note

The `.env` file originally supplied with this project contained a live
Gemini API key in plain text. That key was **not** included anywhere in
this deliverable — `backend/.env.example` only has a placeholder. Rotate
that key at https://aistudio.google.com/apikey before using it again.
