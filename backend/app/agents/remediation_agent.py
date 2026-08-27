"""
Remediation Agent (Milestone 3).

Generates a specific fix recommendation with a short corrected-code example
for each finding from the Code Analysis and Security Vulnerability agents.
Tries the LLM first; falls back to a template library keyed by the finding
"kind" tagged by the security agent (or by keyword match against the bug
title for code-analysis findings) so every finding always gets a concrete
fix, even fully offline.
"""
from __future__ import annotations

import json

from ..rules import load_remediation_data
from .llm_client import LLMUnavailable, extract_json, generate

# Dynamically loaded templates (no hardcoded dictionaries/lists in code)
SECURITY_TEMPLATES, BUG_KEYWORD_TEMPLATES, BANDIT_TEMPLATE_KEY = load_remediation_data()


def _local_fix_for_security(issue: dict) -> dict:
    kind = issue.get("kind", "")
    if kind.startswith("bandit_"):
        kind = BANDIT_TEMPLATE_KEY.get(kind.removeprefix("bandit_"), "")
    if not kind:
        title_l = issue.get("title", "").lower()
        for k in SECURITY_TEMPLATES:
            if k.replace("_", " ") in title_l or k in title_l:
                kind = k
                break
    rec, code = SECURITY_TEMPLATES.get(kind, (
        "Review this finding against secure coding guidelines and apply input validation / least privilege.",
        "// See the Secure Coding Knowledge Base for a pattern-specific fix.",
    ))
    return {"title": f"Fix: {issue['title']}", "recommendation": rec, "corrected_code": code}


def _local_fix_for_bug(bug: dict) -> dict:
    title_l = bug.get("title", "").lower()
    for keyword, rec, code in BUG_KEYWORD_TEMPLATES:
        if keyword in title_l:
            return {"title": f"Fix: {bug['title']}", "recommendation": rec, "corrected_code": code}
    return {"title": f"Fix: {bug['title']}", "recommendation": "Refactor per the code review comment above.",
            "corrected_code": "// Apply the recommended structural change."}


def generate_fixes_local(bugs: list[dict], security_issues: list[dict]) -> list[dict]:
    fixes = [_local_fix_for_security(i) for i in security_issues]
    fixes += [_local_fix_for_bug(b) for b in bugs]
    return fixes


def generate_fixes(code: str, language: str, bugs: list[dict], security_issues: list[dict]) -> list[dict]:
    findings = security_issues + bugs
    if not findings:
        return []
    try:
        findings_summary = json.dumps([
            {"title": f["title"], "severity": f.get("severity", "Medium"), "detail": f.get("detail", "")}
            for f in findings
        ])
        prompt = (
            f"Language: {language}.\n"
            f"Given these detected bugs and security vulnerabilities, provide actionable fix recommendations "
            f"and concise corrected code snippets for each issue.\n\n"
            f"Findings:\n{findings_summary}\n\n"
            f"Original code context:\n{code}\n\n"
            f"Return a strict JSON object with this structure:\n"
            f'{{"fixes": [{{"title": "Fix: <Issue Title>", "recommendation": "Explanation of fix", "corrected_code": "corrected snippet"}}]}}'
        )
        raw = generate(prompt, system="You are a senior software remediation specialist. Return only valid JSON, without conversational prose.")
        parsed = extract_json(raw)
        if isinstance(parsed, dict) and "fixes" in parsed and isinstance(parsed["fixes"], list):
            return parsed["fixes"]
        raise ValueError("Invalid fixes payload from LLM")
    except (LLMUnavailable, Exception):
        return generate_fixes_local(bugs, security_issues)
