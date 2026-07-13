"""
Code Analysis Agent — Module 2 (strengthened).

A fully independent agent. Given a Submission, it:
  1. Runs deterministic static analysis (Python ast / Java heuristics — see
     static_analyzers.py): long methods, cyclomatic + cognitive complexity,
     naming, unused imports/variables, duplicates (exact + renamed-variable),
     magic numbers, long parameter lists, and SOLID heuristics for SRP, ISP,
     and DIP (these three are computable from structure alone).
  2. Makes ONE separate LLM call purely for what static analysis can't do:
     Open/Closed and Liskov Substitution violations (both require reasoning
     about behavior/extensibility, not just structure) plus general design
     anti-patterns and maintainability judgment. The prompt explicitly lists
     what static analysis already covers so the LLM doesn't repeat it, and
     asks the model to self-report a confidence score per finding.
  3. Combines both into a CodeAnalysisResult with quality/maintainability/
     complexity scores plus a computed Maintainability Index.

This agent never calls or imports the Security, Remediation, or PR Summary
agents — those are separate, independently-invoked modules (Modules 3-5).
"""

from datetime import datetime
from typing import List

from app.agents.base import BaseAgent
from app.agents.llm_client import call_llm, parse_json_safely
from app.agents.static_analyzers import (
    JavaStaticAnalyzer,
    PythonStaticAnalyzer,
    StaticAnalysisResult,
    StaticFinding,
)
from app.models.analysis import CodeAnalysisResult, CodeFinding, FindingSource, Severity
from app.models.submission import Language, Submission

# Points subtracted from the maintainability score per finding, by severity.
SEVERITY_PENALTY = {"Low": 2, "Medium": 5, "High": 10, "Critical": 15}


class CodeAnalysisAgent(BaseAgent):
    name = "code_analysis_agent"

    def __init__(self):
        self._python_analyzer = PythonStaticAnalyzer()
        self._java_analyzer = JavaStaticAnalyzer()

    def run(self, submission: Submission) -> CodeAnalysisResult:
        """Execute this agent end-to-end for a single submission."""
        static_result = self._run_static_analysis(submission)
        semantic_findings = self._run_llm_semantic_analysis(submission)

        all_findings: List[CodeFinding] = (
            self._convert_static_findings(static_result.findings, submission.filename) + semantic_findings
        )

        complexity_score = self._score_from_complexity(static_result.function_complexities)
        maintainability_score = self._score_from_findings(all_findings)
        quality_score = round((complexity_score + maintainability_score) / 2)

        avg_complexity = self._average(static_result.function_complexities)
        avg_cognitive = self._average(static_result.function_cognitive_complexities)

        return CodeAnalysisResult(
            submission_id=submission.id,
            filename=submission.filename,
            language=submission.language,
            quality_score=quality_score,
            maintainability_score=maintainability_score,
            complexity_score=complexity_score,
            maintainability_index=static_result.maintainability_index,
            average_cyclomatic_complexity=avg_complexity,
            average_cognitive_complexity=avg_cognitive,
            findings=all_findings,
            analyzed_at=datetime.utcnow(),
        )

    @staticmethod
    def _average(values: List[float]):
        return round(sum(values) / len(values), 1) if values else None

    # ---------------------------------------------------------------
    # Static analysis dispatch
    # ---------------------------------------------------------------
    def _run_static_analysis(self, submission: Submission) -> StaticAnalysisResult:
        if submission.language == Language.PYTHON:
            return self._python_analyzer.analyze(submission.code)
        return self._java_analyzer.analyze(submission.code)

    @staticmethod
    def _convert_static_findings(static_findings: List[StaticFinding], filename: str) -> List[CodeFinding]:
        converted = []
        for f in static_findings:
            try:
                converted.append(CodeFinding(
                    title=f.title,
                    description=f.description,
                    severity=Severity(f.severity),
                    category=f.category,
                    filename=filename,
                    line_number=f.line_number,
                    recommendation=f.recommendation,
                    confidence_score=f.confidence,
                    source=FindingSource.STATIC,
                ))
            except ValueError:
                continue  # skip a malformed static finding rather than fail the whole agent
        return converted

    # ---------------------------------------------------------------
    # LLM semantic pass — OCP + LSP (static analysis can't detect these
    # without behavioral/type reasoning) plus general design anti-patterns
    # ---------------------------------------------------------------
    def _run_llm_semantic_analysis(self, submission: Submission) -> List[CodeFinding]:
        system = (
            "You are a senior software design reviewer. The code below has ALREADY been checked by a "
            "separate static analyzer for: long methods, cyclomatic/cognitive complexity, naming "
            "conventions, unused imports/variables, duplicate code, magic numbers, long parameter lists, "
            "and God Object / Interface Segregation / Dependency Inversion heuristics — do NOT repeat any "
            "of those. Focus ONLY on what requires judgment a static tool can't make:\n"
            "- Open/Closed Principle violations (code that requires modifying existing logic to add new "
            "behavior, instead of extending it)\n"
            "- Liskov Substitution Principle violations (subclasses that break the behavioral contract of "
            "their base class/interface)\n"
            "- General design anti-patterns not already covered (e.g. Spaghetti Code, Shotgun Surgery, "
            "tight coupling, leaky abstractions)\n"
            "- Higher-level maintainability concerns (unclear separation of concerns, missing abstraction)\n"
            "For each finding, self-assess how confident you are (0.0-1.0) — lower confidence for "
            "subjective design judgment calls, higher for clear-cut violations. Return ONLY minified JSON: "
            '{"findings":[{"title":str,"description":str,"severity":"Low|Medium|High",'
            '"category":"SOLID: Open/Closed Principle|SOLID: Liskov Substitution Principle|'
            'Design Anti-pattern|Maintainability|Performance","line_number":int_or_null,'
            '"recommendation":str,"confidence":number}]}. Max 4 findings, description under 25 words.'
        )
        user = f"Language: {submission.language.value}\n\nCode:\n```\n{submission.code}\n```"

        try:
            raw = call_llm(system, user, max_tokens=900)
        except Exception:
            # Graceful degradation: if the LLM call fails (missing/invalid API key,
            # network issue, rate limit), the agent still returns real static
            # analysis findings rather than failing the whole request.
            return []

        parsed = parse_json_safely(raw, {"findings": []})
        findings: List[CodeFinding] = []
        for f in parsed.get("findings", []):
            try:
                description = str(f["description"]).strip()
                recommendation = str(f.get("recommendation", "")).strip()
                if not description or not recommendation:
                    continue  # every finding must have both — skip incomplete ones
                confidence = f.get("confidence", 0.6)
                confidence = min(1.0, max(0.0, float(confidence))) if isinstance(confidence, (int, float)) else 0.6

                findings.append(CodeFinding(
                    title=f["title"],
                    description=description,
                    severity=Severity(f.get("severity", "Medium")),
                    category=f.get("category", "Maintainability"),
                    filename=submission.filename,
                    line_number=f.get("line_number"),
                    recommendation=recommendation,
                    confidence_score=confidence,
                    source=FindingSource.LLM,
                ))
            except (KeyError, ValueError, TypeError):
                continue  # skip a malformed entry rather than fail the whole agent
        return findings

    # ---------------------------------------------------------------
    # Scoring
    # ---------------------------------------------------------------
    @staticmethod
    def _score_from_complexity(complexities: List[float]) -> int:
        if not complexities:
            return 90  # no functions/methods detected — treat as simple script-style code
        avg = sum(complexities) / len(complexities)
        # Average cyclomatic complexity of 1 -> 100; each point above that costs 5, floor 10.
        score = max(10, 100 - (avg - 1) * 5)
        return round(min(score, 100))

    @staticmethod
    def _score_from_findings(findings: List[CodeFinding]) -> int:
        score = 100
        for f in findings:
            score -= SEVERITY_PENALTY.get(f.severity.value, 3)
        return max(0, round(score))
