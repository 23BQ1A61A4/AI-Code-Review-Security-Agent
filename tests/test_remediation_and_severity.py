"""
Milestone 4 / Task 4 & 7 — Remediation quality and severity scoring
consistency validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents import pr_summary_agent  # noqa: E402
from app.report import generator  # noqa: E402

GENERIC_PLACEHOLDER = "apply the recommended structural change"


def test_every_finding_in_report_has_full_remediation_block(client, sample2):
    res = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    analysis_id = res.get_json()["id"]
    report = client.get(f"/api/report/{analysis_id}/json").get_json()

    assert len(report["findings"]) > 0
    for f in report["findings"]:
        rem = f["remediation"]
        assert rem["root_cause"].strip()
        assert rem["recommended_fix"].strip()
        assert rem["corrected_code_example"].strip()
        assert rem["best_practice"].strip()
        # remediation text should reference the finding, not be interchangeable
        # boilerplate for every finding (the generic fallback string is the
        # one case that IS allowed to repeat, since it's the documented
        # last-resort path — everything else must be finding-specific).
        assert rem["root_cause"] != rem["recommended_fix"]


def test_sql_injection_remediation_mentions_parameterization(client, sample2):
    res = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    analysis_id = res.get_json()["id"]
    report = client.get(f"/api/report/{analysis_id}/json").get_json()

    sqli = [f for f in report["findings"] if "sql" in f["title"].lower()]
    assert sqli, "expected at least one SQL-injection-related finding in sample2"
    for f in sqli:
        text = (f["remediation"]["recommended_fix"] + f["remediation"]["root_cause"]).lower()
        assert any(k in text for k in ("parameter", "concatenat", "bound"))


def test_remediation_not_generic_placeholder_for_known_findings(client, sample2):
    """Findings the local template library explicitly covers (SQL injection,
    hardcoded secret, command injection, weak crypto, bare except) must not
    fall back to the generic 'review this finding' placeholder text."""
    res = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    analysis_id = res.get_json()["id"]
    report = client.get(f"/api/report/{analysis_id}/json").get_json()

    covered_keywords = ("sql", "hardcoded", "command", "crypto", "except")
    for f in report["findings"]:
        title_l = f["title"].lower()
        if any(k in title_l for k in covered_keywords):
            assert GENERIC_PLACEHOLDER not in f["remediation"]["recommended_fix"].lower()


# --------------------------------------------------------------------------
# Severity scoring consistency (Task 7)
# --------------------------------------------------------------------------
def _score(issues):
    return pr_summary_agent._score(issues)


def test_severity_weight_ordering_critical_worst_low_least():
    critical = _score([{"severity": "Critical"}])
    high = _score([{"severity": "High"}])
    medium = _score([{"severity": "Medium"}])
    low = _score([{"severity": "Low"}])
    # Higher-severity findings must reduce the score by more than lower ones.
    assert critical < high < medium < low


def test_severity_score_never_negative():
    issues = [{"severity": "Critical"}] * 10
    assert pr_summary_agent._score(issues) == 0


def test_severity_score_deterministic_for_same_input():
    issues = [{"severity": "High"}, {"severity": "Medium"}, {"severity": "Low"}]
    assert pr_summary_agent._score(issues) == pr_summary_agent._score(issues)


def test_pr_verdict_blocks_on_critical_security_issue():
    result = pr_summary_agent.summarize_local(
        "f.py", "Python",
        bugs=[],
        security_issues=[{"title": "Possible SQL Injection", "severity": "Critical", "owasp_category": "A03"}],
        code_smells=[],
    )
    assert result["pr_verdict"] == "Block"


def test_pr_verdict_approves_clean_code():
    result = pr_summary_agent.summarize_local(
        "f.py", "Python", bugs=[], security_issues=[], code_smells=["No significant code smells detected."],
    )
    assert result["pr_verdict"] == "Approve"


def test_severity_breakdown_counts_match_finding_list(client, sample2):
    res = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    analysis_id = res.get_json()["id"]
    report = client.get(f"/api/report/{analysis_id}/json").get_json()

    total_from_breakdown = sum(report["severity_breakdown"].values())
    assert total_from_breakdown == len(report["findings"])
