"""
Python security scanning via `bandit` (https://bandit.readthedocs.io) —
the industry-standard Python SAST tool. Run as a subprocess against a
temp file and its JSON report is parsed and mapped to our schema; the
severity and vulnerability classification come entirely from bandit's own
rule engine, not anything invented here. Returns None if bandit isn't
installed or the run fails, so the caller can fall back to the regex
scanner.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

# Bandit test ID -> OWASP Top 10 (2021) category. Bandit documents each
# test ID at https://bandit.readthedocs.io/en/latest/plugins/index.html —
# this table only maps bandit's own classification onto our reporting
# schema, it does not invent new detections.
BANDIT_OWASP_MAP = {
    "B102": "A03: Injection", "B307": "A03: Injection", "B608": "A03: Injection",
    "B609": "A03: Injection", "B610": "A03: Injection", "B611": "A03: Injection",
    "B601": "A03: Injection", "B602": "A03: Injection", "B603": "A03: Injection",
    "B604": "A03: Injection", "B605": "A03: Injection", "B606": "A03: Injection",
    "B607": "A03: Injection",
    "B105": "A02: Cryptographic Failures", "B106": "A02: Cryptographic Failures",
    "B107": "A02: Cryptographic Failures", "B303": "A02: Cryptographic Failures",
    "B304": "A02: Cryptographic Failures", "B305": "A02: Cryptographic Failures",
    "B324": "A02: Cryptographic Failures", "B505": "A02: Cryptographic Failures",
    "B502": "A02: Cryptographic Failures", "B503": "A02: Cryptographic Failures",
    "B504": "A02: Cryptographic Failures", "B501": "A02: Cryptographic Failures",
    "B301": "A08: Software and Data Integrity Failures",
    "B302": "A08: Software and Data Integrity Failures",
    "B506": "A08: Software and Data Integrity Failures",
    "B403": "A08: Software and Data Integrity Failures",
    "B201": "A05: Security Misconfiguration",
    "B104": "A05: Security Misconfiguration",
    "B108": "A05: Security Misconfiguration",
    "B701": "A03: Injection", "B702": "A03: Injection", "B703": "A03: Injection",
    "B310": "A10: Server-Side Request Forgery (SSRF)",
    "B410": "A03: Injection", "B411": "A03: Injection",
}
DEFAULT_OWASP = "A05: Security Misconfiguration"

SEVERITY_MAP = {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"}


def bandit_available() -> bool:
    return shutil.which("bandit") is not None


def scan_with_bandit(code: str) -> list[dict] | None:
    if not bandit_available():
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "submission.py"
            path.write_text(code, encoding="utf-8")
            proc = subprocess.run(
                ["bandit", "-f", "json", "-q", str(path)],
                capture_output=True, text=True, timeout=20,
            )
            if not proc.stdout.strip():
                return None
            report = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None

    issues = []
    for r in report.get("results", []):
        test_id = r.get("test_id", "")
        severity = SEVERITY_MAP.get(r.get("issue_severity", "MEDIUM"), "Medium")
        confidence = r.get("issue_confidence", "MEDIUM")
        # a HIGH-severity, HIGH-confidence bandit finding is what we surface as Critical
        if severity == "High" and confidence == "HIGH":
            severity = "Critical"
        issues.append({
            "title": r.get("test_name", test_id).replace("_", " ").title(),
            "severity": severity,
            "owasp_category": BANDIT_OWASP_MAP.get(test_id, DEFAULT_OWASP),
            "detail": f"{r.get('issue_text', '').strip()} (line {r.get('line_number', '?')}, bandit {test_id}, confidence {confidence.title()})",
            "kind": f"bandit_{test_id}",
        })
    return issues
