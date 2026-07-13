"""
Analysis API routes — Module 2.

Exposes endpoints that run ONLY the Code Analysis Agent against a stored
submission. Security Vulnerability, Remediation, and PR Summary agents get
their own equivalent endpoints in later modules (e.g. /api/analysis/security/{id})
— never combined into this one.
"""

from fastapi import APIRouter, HTTPException

from app.models.analysis import CodeAnalysisResult
from app.services.analysis_service import AnalysisServiceError, code_analysis_service

router = APIRouter(tags=["analysis"])


@router.post("/analysis/code/{submission_id}", response_model=CodeAnalysisResult)
def run_code_analysis(submission_id: str):
    """Run the Code Analysis Agent (only) against a previously submitted file/snippet."""
    try:
        return code_analysis_service.run_code_analysis(submission_id)
    except AnalysisServiceError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 500
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.get("/analysis/code/{submission_id}", response_model=CodeAnalysisResult)
def get_code_analysis(submission_id: str):
    """Fetch a previously computed Code Analysis result without re-running the agent."""
    result = code_analysis_service.get_result(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No Code Analysis result found for this submission yet.")
    return result
