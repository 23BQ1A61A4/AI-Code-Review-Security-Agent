"""
Report Generation API routes (Milestone 4, Task 1).

All three endpoints look up a real, already-computed analysis record by
id (saved by POST /api/analysis/run) and render it — no re-analysis, no
placeholder data. 404 if the id doesn't exist.
"""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from .. import storage
from . import generator

report_bp = Blueprint("report", __name__)


def _load(analysis_id: str):
    record = storage.get_analysis(analysis_id)
    if record is None:
        return None, (jsonify({"detail": f"No analysis found with id '{analysis_id}'"}), 404)
    return generator.build_report_data(record), None


@report_bp.get("/api/report/<analysis_id>/json")
def report_json(analysis_id: str):
    data, err = _load(analysis_id)
    if err:
        return err
    return jsonify(data)


@report_bp.get("/api/report/<analysis_id>/markdown")
def report_markdown(analysis_id: str):
    data, err = _load(analysis_id)
    if err:
        return err
    md = generator.render_markdown(data)
    filename = f"sentinel-report-{analysis_id}.md"
    return Response(md, mimetype="text/markdown",
                     headers={"Content-Disposition": f"attachment; filename={filename}"})


@report_bp.get("/api/report/<analysis_id>/pdf")
def report_pdf(analysis_id: str):
    data, err = _load(analysis_id)
    if err:
        return err
    pdf_bytes = generator.render_pdf(data)
    filename = f"sentinel-report-{analysis_id}.pdf"
    download = request.args.get("download") == "1"
    disposition = "attachment" if download else "inline"
    return Response(pdf_bytes, mimetype="application/pdf",
                     headers={"Content-Disposition": f"{disposition}; filename={filename}"})
