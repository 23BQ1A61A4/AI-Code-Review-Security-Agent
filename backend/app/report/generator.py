"""
Code Review Report Generation Module (Milestone 4, Task 1).

Turns an existing analysis record (the exact dict already produced by
`agents.orchestrator.run_pipeline` and saved by `storage.save_analysis`)
into a report in three formats: PDF (reportlab), Markdown, and JSON.

Nothing here re-runs analysis or invents findings/scores. Every value in
the report — findings, severities, scores, verdict, fixes — is read
straight from the analysis record that Milestones 2 and 3 already
produced. The only new content added by this module is *category-level*
root-cause / best-practice text (a static reference lookup, the same
pattern the existing `remediation_agent.SECURITY_TEMPLATES` and
`BUG_KEYWORD_TEMPLATES` already use) so that every individual finding in
the PDF has a complete remediation block, not just the first four that
`orchestrator.run_pipeline` caps `fixes` to.
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone

from ..agents import remediation_agent, security_agent
from ..rules import load_report_knowledge

# Dynamically loaded category-level root-cause / best-practice knowledge
ROOT_CAUSE, BEST_PRACTICE, BUG_ROOT_CAUSE, BUG_BEST_PRACTICE = load_report_knowledge()

# title -> kind, straight from the Security Vulnerability Agent's own rule
# table, so a regex/LLM-sourced finding maps back to real category text.
_TITLE_TO_KIND = {title: kind for kind, title, *_ in security_agent.RULES}
_BANDIT_ID_RE = re.compile(r"bandit\s+B(\d+)", re.I)


def _security_kind(issue: dict) -> str:
    m = _BANDIT_ID_RE.search(issue.get("detail", ""))
    if m:
        return remediation_agent.BANDIT_TEMPLATE_KEY.get(f"B{m.group(1)}", "")
    kind = _TITLE_TO_KIND.get(issue.get("title", ""), "")
    if not kind:
        title_l = issue.get("title", "").lower()
        for k in ROOT_CAUSE:
            if k.replace("_", " ") in title_l or k in title_l:
                return k
        if "sql" in title_l:
            return "sql_injection"
        if "secret" in title_l or "password" in title_l or "key" in title_l:
            return "hardcoded_secret"
        if "command" in title_l or "exec" in title_l:
            return "command_injection"
        if "crypto" in title_l or "hash" in title_l:
            return "weak_crypto"
    return kind


def _bug_keyword(bug: dict) -> str | None:
    title_l = bug.get("title", "").lower()
    for keyword, _ in BUG_ROOT_CAUSE:
        if keyword in title_l:
            return keyword
    return None


def _remediation_for_security(issue: dict) -> dict:
    """Real recommendation/corrected-code from remediation_agent's own
    template resolver, plus category root-cause/best-practice text."""
    fix = remediation_agent._local_fix_for_security(issue)
    kind = _security_kind(issue)
    return {
        "root_cause": ROOT_CAUSE.get(kind, issue.get("detail", "See finding detail above.")),
        "recommended_fix": fix["recommendation"],
        "corrected_code_example": fix.get("corrected_code", ""),
        "best_practice": BEST_PRACTICE.get(kind, "Review this finding against the Secure Coding Knowledge Base."),
    }


def _remediation_for_bug(bug: dict) -> dict:
    fix = remediation_agent._local_fix_for_bug(bug)
    keyword = _bug_keyword(bug)
    root = next((r for k, r in BUG_ROOT_CAUSE if k == keyword), bug.get("detail", "See finding detail above."))
    best = next((b for k, b in BUG_BEST_PRACTICE if k == keyword), "Follow the language's standard style/lint guidance for this pattern.")
    return {
        "root_cause": root,
        "recommended_fix": fix["recommendation"],
        "corrected_code_example": fix.get("corrected_code", ""),
        "best_practice": best,
    }


_LOCATION_RE = re.compile(r"line\s+(\d+)", re.I)


def _location(detail: str) -> str:
    m = _LOCATION_RE.search(detail or "")
    return f"Line {m.group(1)}" if m else "Not specified"


def build_report_data(record: dict) -> dict:
    """Normalize a saved analysis record into the report's data model.
    `record` is exactly what `/api/analysis/run` saved — no re-analysis,
    no invented fields."""
    bugs = record.get("bugs", [])
    security_issues = record.get("security_issues", [])
    metrics = record.get("metrics", {})

    findings = []
    for issue in security_issues:
        findings.append({
            "title": issue.get("title", ""),
            "category": issue.get("owasp_category", "Code Quality"),
            "severity": issue.get("severity", "Low"),
            "location": _location(issue.get("detail", "")),
            "explanation": issue.get("detail", ""),
            "type": "Security",
            "remediation": _remediation_for_security(issue),
        })
    for bug in bugs:
        findings.append({
            "title": bug.get("title", ""),
            "category": "Code Quality",
            "severity": bug.get("severity", "Low"),
            "location": _location(bug.get("detail", "")),
            "explanation": bug.get("detail", ""),
            "type": "Code Quality",
            "remediation": _remediation_for_bug(bug),
        })

    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 5))

    breakdown = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for f in findings:
        breakdown[f["severity"]] = breakdown.get(f["severity"], 0) + 1

    # Prioritized remediation roadmap: Critical/High findings first, using
    # each finding's own real recommended_fix (no separately invented plan).
    roadmap = [
        {"priority": i + 1, "title": f["title"], "severity": f["severity"],
         "action": f["remediation"]["recommended_fix"]}
        for i, f in enumerate(f for f in findings if f["severity"] in ("Critical", "High"))
    ]
    if not roadmap:
        roadmap = [
            {"priority": i + 1, "title": f["title"], "severity": f["severity"],
             "action": f["remediation"]["recommended_fix"]}
            for i, f in enumerate(findings[:5])
        ]

    overall_score = round((metrics.get("security_score", 0) + metrics.get("quality_score", 0)) / 2) \
        if metrics else 0

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "analysis_id": record.get("id", ""),
        "filename": record.get("filename") or "submitted snippet",
        "language": record.get("language", "Unknown"),
        "pr_summary": record.get("summary", ""),
        "pr_verdict": record.get("pr_verdict", ""),
        "metrics": metrics,
        "overall_score": overall_score,
        "severity_breakdown": breakdown,
        "findings": findings,
        "roadmap": roadmap,
        "code_smells": record.get("code_smells", []),
        "best_practices": record.get("best_practices", []),
        "performance": record.get("performance", []),
        "engines": record.get("engines", {}),
    }


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------
def render_markdown(data: dict) -> str:
    lines = [
        f"# Sentinel Code Review Report",
        "",
        f"**File:** {data['filename']}  ",
        f"**Language:** {data['language']}  ",
        f"**Analysis ID:** {data['analysis_id']}  ",
        f"**Generated:** {data['generated_at']}",
        "",
        "## Executive / PR Summary",
        data["pr_summary"] or "_No summary available._",
        "",
        f"**PR Verdict:** {data['pr_verdict'] or '-'}",
        "",
        "## Overall Code Health / Quality Score",
        f"**{data['overall_score']} / 100**",
        f"- Security score: {data['metrics'].get('security_score', '-')}/100",
        f"- Quality score: {data['metrics'].get('quality_score', '-')}/100",
        f"- Maintainability score: {data['metrics'].get('maintainability_score', '-')}/100",
        f"- Complexity: {data['metrics'].get('complexity', '-')}",
        "",
        "## Severity Breakdown",
    ]
    for sev in ("Critical", "High", "Medium", "Low", "Info"):
        lines.append(f"- {sev}: {data['severity_breakdown'].get(sev, 0)}")
    lines += ["", "## Findings"]
    if not data["findings"]:
        lines.append("No findings were detected.")
    for f in data["findings"]:
        rem = f["remediation"]
        lines += [
            f"### [{f['severity']}] {f['title']}",
            f"- **Category:** {f['category']}",
            f"- **Type:** {f['type']}",
            f"- **Location:** {f['location']}",
            f"- **Explanation:** {f['explanation']}",
            f"- **Root cause:** {rem['root_cause']}",
            f"- **Recommended fix:** {rem['recommended_fix']}",
            f"- **Best practice:** {rem['best_practice']}",
            "",
            "```",
            rem["corrected_code_example"],
            "```",
            "",
        ]
    lines += ["## Prioritized Remediation Roadmap"]
    if not data["roadmap"]:
        lines.append("No prioritized items.")
    for item in data["roadmap"]:
        lines.append(f"{item['priority']}. **[{item['severity']}] {item['title']}** — {item['action']}")
    lines += [
        "",
        "## Code Smells",
    ]
    lines += [f"- {s}" for s in data["code_smells"]] or ["None."]
    lines += ["", "## Overall Assessment / Best Practices"]
    lines += [f"- {s}" for s in data["best_practices"]] or ["None."]
    lines += ["", "## Performance Suggestions"]
    lines += [f"- {s}" for s in data["performance"]] or ["None."]
    lines += [
        "",
        "---",
        f"_Analysis engines used — code analysis: {data['engines'].get('code_analysis', 'unknown')}, "
        f"security scan: {data['engines'].get('security_scan', 'unknown')}._",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------
def render_json(data: dict) -> str:
    return json.dumps(data, indent=2)


# --------------------------------------------------------------------------
# PDF (reportlab Platypus)
# --------------------------------------------------------------------------
def render_pdf(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    SEV_HEX = {
        "Critical": "#b91c1c",
        "High": "#c2410c",
        "Medium": "#a16207",
        "Low": "#15803d",
        "Info": "#1d4ed8",
    }

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", fontSize=9, leading=13, textColor=colors.HexColor("#444444")))
    styles.add(ParagraphStyle(name="CodeBlock", fontName="Courier", fontSize=8, leading=11,
                               backColor=colors.HexColor("#f4f4f4"), borderPadding=6))
    styles.add(ParagraphStyle(name="FindingTitle", fontSize=12, leading=15, spaceBefore=10, spaceAfter=2,
                               fontName="Helvetica-Bold"))

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    story = []

    story.append(Paragraph("Sentinel Code Review Report", styles["Title"]))
    story.append(Paragraph(
        f"File: {esc(data['filename'])} &nbsp;|&nbsp; Language: {esc(data['language'])} &nbsp;|&nbsp; "
        f"Analysis ID: {esc(data['analysis_id'])}", styles["Small"]))
    story.append(Paragraph(f"Report generated: {esc(data['generated_at'])}", styles["Small"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd")))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive / PR Summary", styles["Heading2"]))
    story.append(Paragraph(esc(data["pr_summary"]) or "No summary available.", styles["BodyText"]))
    story.append(Paragraph(f"<b>PR Verdict:</b> {esc(data['pr_verdict'])}", styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Overall Code Health / Quality Score", styles["Heading2"]))
    m = data["metrics"]
    score_table = Table([
        ["Overall Score", "Security", "Quality", "Maintainability", "Complexity"],
        [f"{data['overall_score']}/100", f"{m.get('security_score','-')}/100", f"{m.get('quality_score','-')}/100",
         f"{m.get('maintainability_score','-')}/100", str(m.get("complexity", "-"))],
    ], colWidths=[1.1 * inch] * 5)
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Severity Breakdown", styles["Heading2"]))
    sev_rows = [["Critical", "High", "Medium", "Low", "Info"],
                [str(data["severity_breakdown"].get(s, 0)) for s in ("Critical", "High", "Medium", "Low", "Info")]]
    sev_table = Table(sev_rows, colWidths=[1.1 * inch] * 5)
    sev_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sev_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Findings", styles["Heading2"]))
    if not data["findings"]:
        story.append(Paragraph("No findings were detected.", styles["BodyText"]))
    for f in data["findings"]:
        hexcolor = SEV_HEX.get(f["severity"], "#000000")
        story.append(Paragraph(
            f'<font color="{hexcolor}">&#9632;</font> '
            f"[{esc(f['severity'])}] {esc(f['title'])}", styles["FindingTitle"]))
        story.append(Paragraph(f"<b>Category:</b> {esc(f['category'])} &nbsp; "
                                f"<b>Type:</b> {esc(f['type'])} &nbsp; "
                                f"<b>Location:</b> {esc(f['location'])}", styles["Small"]))
        story.append(Paragraph(f"<b>Explanation:</b> {esc(f['explanation'])}", styles["BodyText"]))
        rem = f["remediation"]
        story.append(Paragraph(f"<b>Root cause:</b> {esc(rem['root_cause'])}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Recommended fix:</b> {esc(rem['recommended_fix'])}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Best practice:</b> {esc(rem['best_practice'])}", styles["BodyText"]))
        code_text = esc(rem["corrected_code_example"]).replace("\n", "<br/>") or "N/A"
        story.append(Paragraph(code_text, styles["CodeBlock"]))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Prioritized Remediation Roadmap", styles["Heading2"]))
    if not data["roadmap"]:
        story.append(Paragraph("No prioritized items.", styles["BodyText"]))
    for item in data["roadmap"]:
        story.append(Paragraph(
            f"{item['priority']}. <b>[{esc(item['severity'])}] {esc(item['title'])}</b> — {esc(item['action'])}",
            styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Overall Code Quality / Security Assessment", styles["Heading2"]))
    story.append(Paragraph(
        f"Overall score {data['overall_score']}/100. PR verdict: <b>{esc(data['pr_verdict'])}</b>. "
        f"{len(data['findings'])} total finding(s) "
        f"({data['severity_breakdown'].get('Critical', 0)} critical, "
        f"{data['severity_breakdown'].get('High', 0)} high, "
        f"{data['severity_breakdown'].get('Medium', 0)} medium, "
        f"{data['severity_breakdown'].get('Low', 0)} low).", styles["BodyText"]))
    if data["best_practices"]:
        story.append(Paragraph("Best practice suggestions:", styles["BodyText"]))
        for s in data["best_practices"]:
            story.append(Paragraph(f"&bull; {esc(s)}", styles["Small"]))
    if data["performance"]:
        story.append(Paragraph("Performance suggestions:", styles["BodyText"]))
        for s in data["performance"]:
            story.append(Paragraph(f"&bull; {esc(s)}", styles["Small"]))
    if data["code_smells"]:
        story.append(Paragraph("Code smells: " + esc(", ".join(data["code_smells"])), styles["Small"]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd")))
    story.append(Paragraph(
        f"Generated by Sentinel Smart Code Inspection Platform &middot; {esc(data['generated_at'])} &middot; "
        f"engines: {esc(data['engines'].get('code_analysis', 'unknown'))} / "
        f"{esc(data['engines'].get('security_scan', 'unknown'))}", styles["Small"]))

    doc.build(story)
    return buf.getvalue()
