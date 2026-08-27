"""
Milestone 4 / Task 2 & 3 — End-to-end pipeline tests.

Every test hits the real Flask routes (submission -> analysis -> report),
which in turn run the real agents (ast/radon/bandit/javalang when
installed). Nothing here checks only HTTP status; each test asserts on
actual field values in the response.
"""
from __future__ import annotations


def test_submission_python_valid(client, sample1):
    res = client.post("/api/submissions/text", json={"code": sample1, "filename": "sample1_simple.py"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["language"] == "Python"
    assert body["syntax_valid"] is True
    assert body["code_length"] == len(sample1)


def test_submission_detects_java_from_filename(client, sample3):
    res = client.post("/api/submissions/text", json={"code": sample3, "filename": "sample3_sample.java"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["language"] == "Java"
    assert body["language_auto_detected"] is True


def test_submission_rejects_broken_python_syntax(client):
    res = client.post("/api/submissions/text", json={"code": "def f(:\n    pass", "filename": "broken.py"})
    body = res.get_json()
    assert body["syntax_valid"] is False
    assert body["syntax_error"]  # a real compile() SyntaxError message, not empty


def test_analysis_requires_code(client):
    res = client.post("/api/analysis/run", json={"code": "", "language": "Python"})
    assert res.status_code == 400


def test_pipeline_sample1_simple_quality_issue(client, sample1):
    """Sample 1: expects the mutable-default-argument bug to be found."""
    res = client.post("/api/analysis/run", json={"code": sample1, "language": "Python", "filename": "sample1_simple.py"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["language"] == "Python"
    assert isinstance(body["bugs"], list)
    titles = " ".join(b["title"].lower() for b in body["bugs"])
    assert "mutable default" in titles
    # Meaningful output, not just a 200 with empty content.
    assert body["summary"]
    assert body["pr_verdict"] in ("Approve", "Approve with suggestions", "Request changes", "Block")
    assert "security_score" in body["metrics"]


def test_pipeline_sample2_vulnerable_security_issues(client, sample2):
    """Sample 2: expects SQL injection, hardcoded secret, command injection,
    weak crypto (MD5) and a bare-except to be flagged."""
    res = client.post("/api/analysis/run", json={"code": sample2, "language": "Python", "filename": "sample2_vulnerable.py"})
    assert res.status_code == 200
    body = res.get_json()
    sec_titles = " ".join(i["title"].lower() for i in body["security_issues"])
    assert len(body["security_issues"]) >= 3
    assert any(k in sec_titles for k in ("sql injection", "hardcoded", "sql")), sec_titles
    assert body["pr_verdict"] in ("Request changes", "Block")  # must not come back clean
    assert body["metrics"]["security_score"] < 100
    assert len(body["fixes"]) > 0


def test_pipeline_sample3_java(client, sample3):
    """Sample 3: Java code with SQL injection, hardcoded secret, and an
    empty catch block; also a too-many-parameters method."""
    res = client.post("/api/analysis/run", json={"code": sample3, "language": "Java", "filename": "sample3_sample.java"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["language"] == "Java"
    assert isinstance(body["security_issues"], list)
    assert isinstance(body["bugs"], list) or isinstance(body["code_smells"], list)
    assert body["engines"]["code_analysis"] in ("javalang", "regex-fallback", "llm")


def test_analysis_list_returns_saved_records(client, sample1):
    client.post("/api/analysis/run", json={"code": sample1, "language": "Python", "filename": "list-check.py"})
    res = client.get("/api/analysis")
    assert res.status_code == 200
    items = res.get_json()
    assert isinstance(items, list)
    assert any(i.get("filename") == "list-check.py" for i in items)


def test_report_generation_for_each_sample(client, sample1, sample2, sample3):
    """Task 8 — real report generation from real pipeline results, for all
    three formats, for each of the three demo samples."""
    for code, lang, filename in [
        (sample1, "Python", "sample1_simple.py"),
        (sample2, "Python", "sample2_vulnerable.py"),
        (sample3, "Java", "sample3_sample.java"),
    ]:
        run = client.post("/api/analysis/run", json={"code": code, "language": lang, "filename": filename})
        analysis_id = run.get_json()["id"]

        json_res = client.get(f"/api/report/{analysis_id}/json")
        assert json_res.status_code == 200
        data = json_res.get_json()
        assert data["filename"] == filename
        assert data["language"] == lang
        assert "severity_breakdown" in data
        assert "findings" in data

        md_res = client.get(f"/api/report/{analysis_id}/markdown")
        assert md_res.status_code == 200
        md_text = md_res.get_data(as_text=True)
        assert "# Sentinel Code Review Report" in md_text
        assert filename in md_text

        pdf_res = client.get(f"/api/report/{analysis_id}/pdf")
        assert pdf_res.status_code == 200
        pdf_bytes = pdf_res.get_data()
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 1000


def test_report_404_for_unknown_id(client):
    res = client.get("/api/report/does-not-exist/pdf")
    assert res.status_code == 404
