"""
Security Vulnerability Agent (Milestone 2).

Scan order:
  1. LLM (Gemini), if configured and reachable.
  2. `bandit` (Python only) — the industry-standard Python SAST tool. Its
     own rule engine drives the classification and severity; we only map
     its test IDs onto OWASP categories for the report (see
     bandit_scanner.BANDIT_OWASP_MAP).
  3. Regex/pattern scanner — the fallback for Java (no JVM-free equivalent
     of bandit/PMD exists) and for Python when bandit isn't installed.
"""
from __future__ import annotations

import json
import re

from ..rules import load_security_rules
from .bandit_scanner import scan_with_bandit
from .llm_client import LLMUnavailable, extract_json, generate

# Dynamically loaded security rules (no hardcoded static tuples in code)
RULES = load_security_rules()


def _line_of(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


def scan_regex(code: str) -> list[dict]:
    issues = []
    seen_kinds: set[str] = set()
    for kind, title, pattern, severity, owasp, detail in RULES:
        m = pattern.search(code)
        if m and kind not in seen_kinds:
            seen_kinds.add(kind)
            line = _line_of(code, m.start())
            issues.append({
                "title": title, "severity": severity, "owasp_category": owasp,
                "detail": f"{detail} (line {line})", "kind": kind,
            })
    return issues


def scan_local(code: str, language: str) -> dict:
    if language == "Python":
        bandit_issues = scan_with_bandit(code)
        if bandit_issues is not None:
            return {"security_issues": bandit_issues, "engine": "bandit"}
    issues = scan_regex(code)
    return {"security_issues": issues, "engine": "regex-fallback"}


def scan(code: str, language: str) -> dict:
    """Security Vulnerability Agent entry point — tries the LLM, then bandit (Python), then regex."""
    try:
        prompt = (
            f"Language: {language}.\n"
            f"Perform a thorough application security audit of this code against OWASP Top 10 vulnerabilities "
            f"(including SQL Injection, Command Injection, XSS, CSRF, Hardcoded Secrets/Credentials, Broken Access Control, "
            f"Insecure Deserialization, Weak Cryptography/Hashing, SSRF, and Security Misconfigurations).\n"
            f"Return a strict JSON object with this format:\n"
            f'{{"security_issues": [{{"title": "string", "detail": "string with line number and specific vulnerability explanation", '
            f'"severity": "Low|Medium|High|Critical", "owasp_category": "string (e.g. A03: Injection)"}}]}}\n\n'
            f"Code to audit:\n{code}"
        )
        raw = generate(prompt, system="You are an expert Application Security (AppSec) auditor AI agent. Return only valid JSON, without conversational prose.")
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            issues = parsed.get("security_issues") if isinstance(parsed.get("security_issues"), list) else []
            return {
                "security_issues": issues,
                "engine": "llm",
            }
        raise ValueError("Invalid JSON schema returned by LLM")
    except (LLMUnavailable, Exception):
        return scan_local(code, language)
