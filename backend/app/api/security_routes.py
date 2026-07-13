"""
Security Analysis API routes — Module 3.

Exposes endpoints that run ONLY the Security Vulnerability Agent against a
stored submission — entirely separate from /api/analysis/code/* (Module 2).
Remediation and PR Summary (Modules 4-5) will get their own equivalent
routes, never combined into this one.
"""

from fastapi import APIRouter, HTTPException

from app.models.security import SecurityAnalysisResult
from app.services.security_service import SecurityAnalysisServiceError, security_analysis_service

router = APIRouter(tags=["security"])


@router.post("/analysis/security/{submission_id}", response_model=SecurityAnalysisResult)
def run_security_analysis(submission_id: str):
    """Run the Security Vulnerability Agent (only) against a previously submitted file/snippet."""
    try:
        return security_analysis_service.run_security_analysis(submission_id)
    except SecurityAnalysisServiceError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 500
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.get("/analysis/security/{submission_id}", response_model=SecurityAnalysisResult)
def get_security_analysis(submission_id: str):
    """Fetch a previously computed Security Analysis result without re-running the agent."""
    result = security_analysis_service.get_result(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No Security Analysis result found for this submission yet.")
    return result
