"""
Analysis Service — Module 2.

Orchestrates running the Code Analysis Agent against a stored submission:
fetches it from the Submission Service, updates its status, invokes the
agent, stores the result, and handles failure. This is the only place that
knows both the Submission Service and the Code Analysis Agent exist — the
API layer and the agent itself stay decoupled from each other, and this
service will get sibling methods (run_security_analysis, etc.) in later
modules without needing to change how this one works.
"""

from typing import Dict, Optional

from app.agents.code_analysis_agent import CodeAnalysisAgent
from app.models.analysis import CodeAnalysisResult
from app.models.submission import SubmissionStatus
from app.services.submission_service import submission_service


class AnalysisServiceError(Exception):
    """Raised for any failure in running or retrieving an analysis."""


class CodeAnalysisService:
    def __init__(self):
        self._agent = CodeAnalysisAgent()
        self._results: Dict[str, CodeAnalysisResult] = {}

    def run_code_analysis(self, submission_id: str) -> CodeAnalysisResult:
        submission = submission_service.get(submission_id)
        if submission is None:
            raise AnalysisServiceError("Submission not found.")

        submission.status = SubmissionStatus.ANALYZING
        try:
            result = self._agent.run(submission)
        except Exception as exc:
            submission.status = SubmissionStatus.FAILED
            raise AnalysisServiceError(f"Code Analysis Agent failed: {exc}") from exc

        self._results[submission_id] = result
        submission.status = SubmissionStatus.COMPLETED
        return result

    def get_result(self, submission_id: str) -> Optional[CodeAnalysisResult]:
        return self._results.get(submission_id)


# Single shared instance for the app's lifetime, mirroring submission_service.
code_analysis_service = CodeAnalysisService()
