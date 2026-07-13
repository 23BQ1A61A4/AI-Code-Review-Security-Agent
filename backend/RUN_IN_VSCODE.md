# Running this project in VS Code (Windows PowerShell)

This project has **two separate local servers** you'll run side by side:

| Server | Port | Purpose |
|---|---|---|
| `server.py` (Flask) | 5000 | Serves the HTML UI + proxies AI analysis calls to Claude (keeps your API key server-side) |
| `backend/app/main.py` (FastAPI) | 8000 | Milestone 1 Code Submission Module, Code Analysis Agent, Security Vulnerability Agent |

The HTML frontend talks to **both**: it calls `localhost:8000` for code submission/language-detection/syntax-check, and `localhost:5000` (via `server.py`) for the AI-powered analysis itself.

---

## 1. Open the project

```powershell
cd path\to\AI-Code-Review-Security-Agent
code .
```
(`code .` opens the folder in VS Code — requires the `code` command to be on PATH, which the VS Code installer offers to set up.)

## 2. Create and activate a virtual environment

Open a terminal in VS Code (`` Ctrl+` ``), then:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script with an execution-policy error:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your prompt once activated.

## 3. Install dependencies

The FastAPI backend's dependencies (also covers `server.py`'s needs — both use `anthropic`):

```powershell
cd backend
pip install -r requirements.txt
pip install flask
cd ..
```

For running tests too:
```powershell
cd backend
pip install -r requirements-dev.txt
cd ..
```

## 4. Set your ANTHROPIC_API_KEY

Get a key from https://console.anthropic.com, then in the **same terminal session** you'll run the servers from:

```powershell
$env:ANTHROPIC_API_KEY = "your_key_here"
```

This only lasts for the current terminal session. To set it permanently for your user account:
```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your_key_here", "User")
```
(then open a **new** terminal for it to take effect).

## 5. Start the FastAPI backend

Open a terminal (Terminal → New Terminal), activate the venv if it isn't already, then:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`. Leave this terminal running.

**Verify it's up**: open http://localhost:8000/api/health in a browser — expect
`{"status":"ok","service":"ai-code-review-backend","module":"3 - security vulnerability agent"}`.

Interactive API docs: http://localhost:8000/docs

## 6. Run/open the frontend

Open a **second** terminal (Terminal → New Terminal — don't reuse the one running uvicorn), activate the venv, make sure `ANTHROPIC_API_KEY` is set in this terminal too (step 4), then from the project root:

```powershell
python server.py
```

You should see Flask start on port 5000. Open http://localhost:5000 in your browser.

**Do not** open `ai-code-review-platform.html` directly by double-clicking it, and **do not** use the VS Code "Live Server" extension for it — neither can hide your API key or proxy requests, so the AI analysis calls will fail. Always load it through `python server.py` at `http://localhost:5000`.

## 7. Test the Code Submission Module

With both servers running, in the UI:
1. Click "Get started"
2. Go to "Upload & analyze"
3. Paste some Python or Java code (or upload a `.py`/`.java` file)
4. Click "Run AI analysis"

You should see a green **"FastAPI backend (Submission Module)"** panel appear first, showing a real submission ID, detected language, and syntax-check result — confirming the frontend reached `localhost:8000`. Then the AI analysis results follow.

To test language auto-detection specifically: paste Python code **without** selecting a language (leave the dropdown on "Auto-detect") and confirm it's correctly identified.

To test syntax-error detection: paste deliberately broken code (e.g. `def f(:\n  pass`) and confirm the panel shows a syntax error with a line number instead of "Syntax valid".

You can also test the Submission Module directly via Swagger, independent of the HTML:
http://localhost:8000/docs → `POST /api/submissions/text` → Try it out.

## 8. Run pytest

In a terminal with the venv activated:

```powershell
cd backend
pytest -v
```

This runs all test files: `test_submission_module.py`, `test_static_analyzers.py`, `test_code_analysis_agent.py`, `test_security_rules.py`, `test_security_vulnerability_agent.py`, `test_knowledge_base.py`. All LLM calls are mocked in these tests, so they run without needing `ANTHROPIC_API_KEY` or a live agent call — but `pydantic` and `anthropic` (from step 3) do need to be installed for the imports to resolve.

## Troubleshooting

**`ModuleNotFoundError: No module named 'app'` when running pytest**
Run `pytest` from inside the `backend\` folder, not the project root — `pytest.ini` sets `pythonpath = .` relative to where you run it.

**`ModuleNotFoundError: No module named 'flask'`**
`server.py` needs Flask separately — it's not in `backend/requirements.txt` since it's not part of the FastAPI backend. Run `pip install flask` (already included in step 3 above).

**Frontend shows a red "Backend not reachable" panel**
The FastAPI server (step 5) isn't running, or isn't on port 8000. Check that terminal for errors, and confirm http://localhost:8000/api/health responds.

**AI analysis fails / spins forever**
Usually means `ANTHROPIC_API_KEY` isn't set in the terminal running `server.py` specifically — check that terminal's output for the "⚠️ ANTHROPIC_API_KEY is not set" warning printed at startup.

**Port already in use (`8000` or `5000`)**
Something else is using the port. Either stop that process, or run on a different port:
```powershell
uvicorn app.main:app --reload --port 8001
```
(if you change the FastAPI port, also update the `http://localhost:8000` references inside `ai-code-review-platform.html`'s `submitToBackend()` function to match).

**PowerShell won't let you activate the venv (execution policy error)**
See step 2 above — `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` fixes this for the current terminal session only (doesn't change your system-wide policy).

**`pip install` fails / times out**
Check your internet connection — all dependencies are pulled from PyPI at install time, nothing is bundled offline in this project.
