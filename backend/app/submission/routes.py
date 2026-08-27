from flask import Blueprint, jsonify, request

from .. import storage
from .detector import process_submission

submission_bp = Blueprint("submission", __name__)


@submission_bp.post("/api/submissions/text")
def submit_text():
    body = request.get_json(force=True, silent=True) or {}
    code = body.get("code", "")
    filename = body.get("filename")
    declared_language = body.get("language")

    if not code or not code.strip():
        return jsonify({"detail": "`code` is required"}), 400

    result = process_submission(code, filename, declared_language)

    record = {
        "id": storage.new_id("sub"),
        "ts": storage.now_ms(),
        "filename": filename,
        "language": result.language,
        "language_auto_detected": result.auto_detected,
        "syntax_valid": result.syntax_valid,
        "syntax_error": result.syntax_error,
        "code_length": len(code),
    }
    storage.save_submission(record)
    return jsonify(record)
