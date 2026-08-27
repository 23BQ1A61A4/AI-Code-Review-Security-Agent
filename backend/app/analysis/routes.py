from flask import Blueprint, jsonify, request

from .. import storage
from ..agents.orchestrator import run_pipeline

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.post("/api/analysis/run")
def run_analysis():
    body = request.get_json(force=True, silent=True) or {}
    code = body.get("code", "")
    language = body.get("language") or "Unknown"
    filename = body.get("filename")

    if not code or not code.strip():
        return jsonify({"detail": "`code` is required"}), 400

    code = code[:12000]
    result = run_pipeline(code, language, filename)

    record = {
        "id": storage.new_id("a"),
        "ts": storage.now_ms(),
        "filename": filename,
        "language": language,
        "code": code,
        **result,
    }
    storage.save_analysis(record)
    return jsonify(record)


@analysis_bp.get("/api/analysis")
def list_analyses():
    return jsonify(storage.list_analyses())
