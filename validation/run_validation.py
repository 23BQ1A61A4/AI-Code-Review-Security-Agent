"""
Milestone 4 / Task 2, 3, 4, 8 — end-to-end validation runner.

Runs the REAL pipeline (submission -> analysis -> report) against the
three sample files in validation/samples/, and writes out the actual
results as JSON + Markdown. Nothing in this script's output is
predetermined; every field comes from the live agents.

Usage:
    cd backend && python ../validation/run_validation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.submission.detector import process_submission  # noqa: E402
from app.agents.orchestrator import run_pipeline  # noqa: E402
from app.report import generator  # noqa: E402

SAMPLES_DIR = ROOT / "validation" / "samples"
OUT_DIR = ROOT / "validation"

SAMPLES = [
    ("sample1_simple.py", "Python", "Basic code-quality issue (mutable default argument)"),
    ("sample2_vulnerable.py", "Python", "Realistic security vulnerabilities (SQLi, hardcoded secret, command injection, weak crypto, bare except)"),
    ("sample3_sample.java", "Java", "Java code-quality/security issues (SQLi, hardcoded secret, empty catch, too many params)"),
]


def run() -> dict:
    results = []
    for filename, language, expected_note in SAMPLES:
        code = (SAMPLES_DIR / filename).read_text()

        submission = process_submission(code, filename, language)
        pipeline_result = run_pipeline(code, language, filename)
        record = {"id": f"validation_{filename}", "ts": 0, "filename": filename,
                  "language": language, "code": code, **pipeline_result}
        report_data = generator.build_report_data(record)

        pdf_bytes = generator.render_pdf(report_data)
        pdf_path = OUT_DIR / f"report_{filename.replace('.', '_')}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        results.append({
            "sample": filename,
            "language": language,
            "expected_characteristic": expected_note,
            "submission": {
                "language_detected": submission.language,
                "auto_detected": submission.auto_detected,
                "syntax_valid": submission.syntax_valid,
                "syntax_error": submission.syntax_error,
            },
            "engines_used": pipeline_result["engines"],
            "bugs_detected": [{"title": b["title"], "severity": b["severity"]} for b in pipeline_result["bugs"]],
            "security_issues_detected": [
                {"title": s["title"], "severity": s["severity"], "owasp_category": s.get("owasp_category")}
                for s in pipeline_result["security_issues"]
            ],
            "code_smells_detected": pipeline_result["code_smells"],
            "metrics": pipeline_result["metrics"],
            "pr_verdict": pipeline_result["pr_verdict"],
            "fixes_generated": len(pipeline_result["fixes"]),
            "report_findings_count": len(report_data["findings"]),
            "report_severity_breakdown": report_data["severity_breakdown"],
            "pdf_report_path": str(pdf_path.relative_to(ROOT)),
            "pdf_report_bytes": len(pdf_bytes),
            "pdf_valid_header": pdf_bytes[:5] == b"%PDF-",
        })
    return {"results": results}


def render_markdown(data: dict) -> str:
    lines = ["# Milestone 4 — Detection & Report Validation (Real Pipeline Run)", ""]
    for r in data["results"]:
        lines += [
            f"## {r['sample']} ({r['language']})",
            f"**Expected characteristic:** {r['expected_characteristic']}",
            "",
            f"- Language detected: **{r['submission']['language_detected']}** "
            f"(auto-detected: {r['submission']['auto_detected']})",
            f"- Syntax valid: **{r['submission']['syntax_valid']}**"
            + (f" — error: {r['submission']['syntax_error']}" if r['submission']['syntax_error'] else ""),
            f"- Engines used: code analysis = `{r['engines_used']['code_analysis']}`, "
            f"security scan = `{r['engines_used']['security_scan']}`",
            "",
            "**Bugs detected:**",
        ]
        lines += [f"  - [{b['severity']}] {b['title']}" for b in r["bugs_detected"]] or ["  - None"]
        lines += ["", "**Security issues detected:**"]
        lines += [f"  - [{s['severity']}] {s['title']} ({s['owasp_category']})" for s in r["security_issues_detected"]] or ["  - None"]
        lines += ["", "**Code smells detected:**"]
        lines += [f"  - {s}" for s in r["code_smells_detected"]] or ["  - None"]
        lines += [
            "",
            f"- PR verdict: **{r['pr_verdict']}**",
            f"- Metrics: {r['metrics']}",
            f"- Fixes generated (pipeline `fixes` list): {r['fixes_generated']}",
            f"- Report findings count (per-finding remediation, report module): {r['report_findings_count']}",
            f"- Report severity breakdown: {r['report_severity_breakdown']}",
            f"- PDF report: `{r['pdf_report_path']}` ({r['pdf_report_bytes']} bytes, "
            f"valid PDF header: {r['pdf_valid_header']})",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    data = run()
    (OUT_DIR / "validation_report.json").write_text(json.dumps(data, indent=2))
    (OUT_DIR / "validation_report.md").write_text(render_markdown(data))
    print(json.dumps(data, indent=2))
