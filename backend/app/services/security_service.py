"""
Security Analysis Service — Module 3.

Mirrors CodeAnalysisService's shape exactly (Module 2) but is a fully
separate class/instance, per the requirement that this agent not share
logic with the Code Analysis Agent. Fetches a submission, runs only the
Security Vulnerability Agent, stores/returns the result, and updates
submission status.
"""

from typing import Dict, Optional

from app.agents.security_vulnerability_agent import SecurityVulnerabilityAgent
from app.models.security import SecurityAnalysisResult
from app.models.submission import SubmissionStatus
from app.services.submission_service import submission_service


class SecurityAnalysisServiceError(Exception):
    """Raised for any failure in running or retrieving a security analysis."""


class SecurityAnalysisService:
    def __init__(self):
        self._agent = SecurityVulnerabilityAgent()
        self._results: Dict[str, SecurityAnalysisResult] = {}

    def run_security_analysis(self, submission_id: str) -> SecurityAnalysisResult:
        submission = submission_service.get(submission_id)
        if submission is None:
            raise SecurityAnalysisServiceError("Submission not found.")

        try:
            result = self._agent.run(submission)
        except Exception as exc:
            submission.status = SubmissionStatus.FAILED
            raise SecurityAnalysisServiceError(f"Security Vulnerability Agent failed: {exc}") from exc

        self._results[submission_id] = result
        # Note: doesn't overwrite status to COMPLETED unconditionally — the
        # Code Analysis Agent (Module 2) may still be running independently
        # against the same submission. Status reflects "at least one agent
        # has finished" rather than "the whole pipeline is done" until an
        # orchestrator (a later module) coordinates all agents together.
        if submission.status != SubmissionStatus.COMPLETED:
            submission.status = SubmissionStatus.COMPLETED
        return result

    def get_result(self, submission_id: str) -> Optional[SecurityAnalysisResult]:
        return self._results.get(submission_id)


# Single shared instance for the app's lifetime, mirroring code_analysis_service.
security_analysis_service = SecurityAnalysisService()
