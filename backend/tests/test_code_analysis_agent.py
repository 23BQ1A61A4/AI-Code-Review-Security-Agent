"""
Unit tests for app/agents/code_analysis_agent.py.

Run with:
    pytest tests/test_code_analysis_agent.py -v

The LLM call is monkeypatched throughout, so these tests need no
ANTHROPIC_API_KEY and no network access — they're fully deterministic.
"""

import json

import pytest

from app.agents.code_analysis_agent import CodeAnalysisAgent
from app.models.submission import Language, Submission

SAMPLE_PYTHON_CODE = (
    "import os\n"
    "def BadlyNamedFunction(a, b, c, d, e, f, g):\n"
    "    unused_var = 1\n"
    "    if a > 999:\n"
    "        return a\n"
    "    return b\n"
)

FAKE_LLM_RESPONSE = json.dumps({
    "findings": [
        {
            "title": "Open/Closed Principle violation",
            "description": "Adding a new type requires editing this function's if/elif chain.",
            "severity": "Medium",
            "category": "SOLID: Open/Closed Principle",
            "line_number": 3,
            "recommendation": "Use polymorphism or a strategy pattern instead of branching on type.",
            "confidence": 0.65,
        }
    ]
})


def make_submission(code=SAMPLE_PYTHON_CODE, language=Language.PYTHON, filename="demo.py"):
    return Submission(filename=filename, language=language, code=code)


@pytest.fixture
def agent():
    return CodeAnalysisAgent()


class TestCodeAnalysisAgent:
    def test_run_combines_static_and_llm_findings(self, agent, monkeypatch):
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: FAKE_LLM_RESPONSE,
        )
        result = agent.run(make_submission())

        sources = {f.source.value for f in result.findings}
        assert "static_analysis" in sources
        assert "llm_semantic" in sources
        assert any(f.category == "SOLID: Open/Closed Principle" for f in result.findings)

    def test_graceful_degradation_when_llm_fails(self, agent, monkeypatch):
        def raise_error(*args, **kwargs):
            raise RuntimeError("simulated API failure")

        monkeypatch.setattr("app.agents.code_analysis_agent.call_llm", raise_error)
        result = agent.run(make_submission())

        # Static findings should still be present even though the LLM call failed.
        assert len(result.findings) > 0
        assert all(f.source.value == "static_analysis" for f in result.findings)

    def test_scores_are_within_valid_range(self, agent, monkeypatch):
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: FAKE_LLM_RESPONSE,
        )
        result = agent.run(make_submission())

        assert 0 <= result.quality_score <= 100
        assert 0 <= result.maintainability_score <= 100
        assert 0 <= result.complexity_score <= 100
        assert result.maintainability_index is None or 0 <= result.maintainability_index <= 100

    def test_every_finding_has_all_required_fields(self, agent, monkeypatch):
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: FAKE_LLM_RESPONSE,
        )
        result = agent.run(make_submission())

        assert len(result.findings) > 0
        for f in result.findings:
            assert f.severity is not None
            assert f.category
            assert f.description
            assert f.recommendation
            assert 0.0 <= f.confidence_score <= 1.0
            assert f.source is not None

    def test_malformed_llm_json_is_ignored_not_fatal(self, agent, monkeypatch):
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: "not valid json at all {{{",
        )
        result = agent.run(make_submission())
        # Should fall back to static-only findings without raising.
        assert len(result.findings) > 0
        assert all(f.source.value == "static_analysis" for f in result.findings)

    def test_llm_finding_missing_recommendation_is_skipped(self, agent, monkeypatch):
        bad_response = json.dumps({
            "findings": [
                {
                    "title": "Incomplete finding",
                    "description": "This finding has no recommendation field.",
                    "severity": "Low",
                    "category": "Maintainability",
                    "line_number": None,
                    "recommendation": "",  # empty — must be rejected
                    "confidence": 0.5,
                }
            ]
        })
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: bad_response,
        )
        result = agent.run(make_submission())
        assert not any(f.title == "Incomplete finding" for f in result.findings)

    def test_java_submission_uses_java_analyzer(self, agent, monkeypatch):
        monkeypatch.setattr(
            "app.agents.code_analysis_agent.call_llm",
            lambda system, user, max_tokens=900: json.dumps({"findings": []}),
        )
        java_code = (
            "public class badClassName {\n"
            "    public void run() {\n"
            "        int x = 1;\n"
            "    }\n"
            "}\n"
        )
        result = agent.run(make_submission(code=java_code, language=Language.JAVA, filename="Demo.java"))
        assert any(f.category == "Naming Convention" for f in result.findings)
