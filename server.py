"""
Development of Smart Code Inspection Platform with Vulnerability Detection
System – Group 2  (Infosys Internship Project; application name: Sentinel)

Single entrypoint that runs the whole app: the Flask backend (Submission
Module, multi-agent Analysis pipeline, and RAG-powered Conversational Code
Assistant) plus serving the frontend SPA — all on one port.

Setup:
    cd backend
    pip install -r requirements.txt
    cd ..

Optional (for real LLM-backed agents instead of the offline analyzer):
    cp backend/.env.example backend/.env
    # then edit backend/.env and set GEMINI_API_KEY

Run:
    python server.py

Then open:
    http://localhost:5000
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.main import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")

    print("\n" + "=" * 60)
    print("  [*] Sentinel Code Inspection Platform is LIVE!")
    print(f"  [*] Web UI Link: http://localhost:{port} (or http://{host}:{port})")
    print(f"  [*] Health Check: http://localhost:{port}/api/health")
    print("=" * 60 + "\n")

    app.run(host=host, port=port, debug=debug)
