"""
Sentinel — Smart Code Inspection Platform with Vulnerability Detection.

App factory: wires together the Submission Module (Milestone 1), the
multi-agent Analysis pipeline (Milestone 2+3), and the Conversational Code
Assistant (Milestone 3) behind a single Flask app, and serves the frontend
SPA at `/`. Run with `python server.py` from the project root.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, send_from_directory

from .analysis.routes import analysis_bp
from .chat.routes import chat_bp
from .rag.routes import kb_bp
from .report.routes import report_bp
from .submission.routes import submission_bp

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
HTML_FILE = "ai-code-review-platform.html"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

    app.register_blueprint(submission_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(kb_bp)
    app.register_blueprint(report_bp)

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, HTML_FILE)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
