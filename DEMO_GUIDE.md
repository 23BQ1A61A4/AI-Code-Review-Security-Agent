# Sentinel — Live Demo Guide

**Project:** Development of Smart Code Inspection Platform with Vulnerability
Detection System – Group 2 (Infosys Internship Project). Application name: Sentinel.

This is the exact sequence to run for the live demo, verified end-to-end
against the running app (not just described).

## 1. Install

```bash
cd backend
pip install -r requirements.txt
cd ..
```

Optional — only if you want to demonstrate the LLM tier instead of the
offline library/regex tiers (not required; the app is fully functional
without it):
```bash
cp backend/.env.example backend/.env
# edit backend/.env and set GEMINI_API_KEY=your-key
```

## 2. Start the app

There is a single entrypoint that serves both the backend API and the
frontend SPA on one port — there is no separate frontend server to start.

```bash
python server.py
```

Then open **http://localhost:5000** in a browser.

If the terminal shows `Sentinel is starting at http://localhost:5000` and
then `Running on http://127.0.0.1:5000`, the app is up.

## 3. Demo script (follow in order)

### Step 1 — Dashboard
Open `http://localhost:5000`. You land on the Dashboard. Click **Code
Analysis** in the left nav (or "Run an analysis").

### Step 2 — Submit Sample 1 (simple Python)
Upload `validation/samples/sample1_simple.py` via drag-and-drop or the file
picker (supports `.py .java .js .ts .c .cpp`), then click **Run AI
analysis**.

**Expected output:**
- A green "Submission Module" card appears first, showing the submission id,
  detected language `Python`, and a `Syntax valid` badge — this is the
  Milestone 1 Submission Module firing independently of the AI analysis.
- You're taken to **Findings**. The PR summary mentions "mutable default
  argument" style analysis, verdict is **Approve with suggestions**.
- Code Analysis Agent panel shows **Mutable default argument** (Medium).
- Security Vulnerability Agent panel shows **no issues**.
- Metrics gauges: Security score 100, Quality score ~92, Maintainability
  ~96, Complexity Low.
- Analysis engine line shows `ast+radon` (code analysis) and `bandit`
  (security scan) if those libraries are installed, confirming real
  library-backed analysis, not just regex.

### Step 3 — Submit Sample 2 (vulnerable Python)
Go back to **Code Analysis**, upload `validation/samples/sample2_vulnerable.py`,
run analysis.

**Expected output:**
- PR verdict: **Block**.
- Security Vulnerability Agent panel lists 5 issues: a SQL-injection
  finding, a hardcoded password, a command-injection ("shell") finding, a
  weak-crypto (MD5/hashlib) finding, and a bare-except/try-except-pass
  finding — each tagged with an OWASP category and severity.
- Remediation Agent panel shows concrete fixes with corrected-code
  snippets for the top findings.
- Best practice / performance suggestion panels are populated.

### Step 4 — Submit Sample 3 (Java)
Upload `validation/samples/sample3_sample.java`, run analysis.

**Expected output:**
- Submission Module card shows language `Java` (auto-detected from the
  `.java` extension) and `Syntax valid`.
- PR verdict: **Block**.
- Security panel: SQL injection and command injection (`Runtime.exec`)
  findings, Critical severity.
- Code Analysis panel: "Method with too many parameters" finding; code
  smells include "Empty catch block — exception silently swallowed".
- Analysis engine line shows `javalang` for code analysis (real Java AST
  parsing) and `regex-fallback` for security scan (documented — there is
  no offline Java-equivalent of bandit).
- **Note for the demo:** the hardcoded field `dbPassword` in this sample is
  intentionally NOT flagged — see "Known limitation" below. If asked, this
  is a good moment to show you know the system's real boundaries rather
  than overclaiming.

### Step 5 — Download reports
On the Findings page, click **Download PDF** (top-right of the PR summary
card). A real PDF opens/downloads containing: submission info, language,
PR summary, overall score, severity breakdown, every finding with
root cause / recommended fix / corrected code / best practice, and a
prioritized remediation roadmap.

Also demo the **Reports** page from the left nav — lists every past
analysis with both **.md** and **PDF** download buttons per row.

For a fuller demo, you can also hit the JSON/Markdown endpoints directly
in a second terminal to show the raw dynamic output:
```bash
curl "http://localhost:5000/api/report/<analysis_id>/markdown"
curl "http://localhost:5000/api/report/<analysis_id>/json"
```
(get `<analysis_id>` from the browser URL/network tab, or from the id
shown in the Submission Module card, or the History page.)

### Step 6 — Knowledge Base
Click **Knowledge Base** in the left nav.

**Expected output:** four documents listed (OWASP Top 10, Secure Coding
Python, Secure Coding Java, Code Smells), each expandable by section. Type
a query like `SQL Injection` or `Hardcoded Secret` into the search box —
results return ranked by relevance with a similarity score, proving the
TF-IDF retriever is live, not static text.

### Step 7 — AI Assistant
Click **AI Assistant** in the left nav. Ask, in order:
1. `"What's the top security issue in my last analysis?"` — the assistant
   should reference the actual finding from Sample 2 or 3's analysis.
2. `"How do I fix it?"` — follow-up using conversation history.
3. `"What is a secure way to handle passwords?"` — a general knowledge-base
   question.

**Expected output:** every assistant reply that draws on the knowledge
base shows a source tag under the message reading **"Answer generated
using Knowledge Base — <document names>"**, so the grounding is visible on
screen, not just claimed.

## 4. Known limitation (say this out loud if asked about accuracy)

The Java security scanner uses a regex fallback (there's no offline
bandit-equivalent for Java). Its `hardcoded_secret` pattern requires a
word boundary before keywords like `password`, so a camelCase field name
like `dbPassword` (used intentionally in `sample3_sample.java`) is not
flagged, even though a literal `password = "..."` would be. Measured
detection accuracy across the three demo samples is **10/11 (~91%)**, not
100% — see `docs/MILESTONE_4.md` §5 and `FINAL_SUBMISSION.md` for the full
table.

## 5. If something doesn't come up

- **Blank page at localhost:5000:** confirm `python server.py` printed
  `Running on http://127.0.0.1:5000` with no traceback.
- **"Backend not reachable" banner:** the server isn't running or crashed —
  check the terminal for a traceback.
- **PDF download does nothing:** check `pip install -r requirements.txt`
  included `reportlab` (it's in `backend/requirements.txt`).
- **Security scan shows `regex-fallback` for Python too:** `bandit` isn't
  installed — run `pip install bandit` (or reinstall requirements.txt) and
  restart the server; results will upgrade to the `bandit` engine
  automatically, no code changes needed.
