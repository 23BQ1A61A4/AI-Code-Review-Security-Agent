"""
Code Submission Module — API routes.

Two ways in, matching the existing HTML frontend's "paste code" and
"upload file" flows:

    POST /api/submissions/text   JSON body: {language?, code, filename?}
                                  language is optional — auto-detected from
                                  content if omitted (see syntax_check.py)
    POST /api/submissions/file   multipart file upload (.py or .java)

    GET  /api/submissions/{id}   fetch a single submission
    GET  /api/submissions        list all submissions (debug/testing use)

Every submission response includes syntax_valid/syntax_error (a basic check
run immediately at submission time — see app/services/syntax_check.py) and
language_auto_detected. No agent logic lives here — this module only
accepts, validates, and stores code. Module 2+ picks up a submission by id
and runs the Code Analysis -> Security -> Remediation -> PR Summary agents.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import SUPPORTED_EXTENSIONS
from app.models.submission import (
    Language,
    Submission,
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
)
from app.services.submission_service import SubmissionValidationError, submission_service

router = APIRouter(tags=["submissions"])


def _to_response(submission: Submission) -> SubmissionResponse:
    return SubmissionResponse(
        id=submission.id,
        filename=submission.filename,
        language=submission.language,
        language_auto_detected=submission.language_auto_detected,
        status=submission.status,
        created_at=submission.created_at,
        code_length=len(submission.code),
        syntax_valid=submission.syntax_valid,
        syntax_error=submission.syntax_error,
        syntax_error_line=submission.syntax_error_line,
    )


@router.post("/submissions/text", response_model=SubmissionResponse)
def submit_text(payload: SubmissionCreate):
    try:
        submission = submission_service.create(payload)
    except SubmissionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(submission)


@router.post("/submissions/file", response_model=SubmissionResponse)
async def submit_file(file: UploadFile = File(...), language: Optional[Language] = Form(None)):
    if not file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only .py and .java files are supported.")

    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")

    submission = submission_service.create_from_file(file.filename, content, language)
    return _to_response(submission)


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(submission_id: str):
    submission = submission_service.get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return _to_response(submission)


@router.get("/submissions", response_model=SubmissionListResponse)
def list_submissions():
    items = [_to_response(s) for s in submission_service.all()]
    return SubmissionListResponse(submissions=items, total=len(items))



@router.post("/submissions/file", response_model=SubmissionResponse)
async def submit_file(file: UploadFile = File(...), language: Optional[Language] = Form(None)):
    if not file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only .py and .java files are supported.")

    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")

    submission = submission_service.create_from_file(file.filename, content, language)
    return _to_response(submission)


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(submission_id: str):
    submission = submission_service.get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return _to_response(submission)


@router.get("/submissions", response_model=SubmissionListResponse)
def list_submissions():
    items = [_to_response(s) for s in submission_service.all()]
    return SubmissionListResponse(submissions=items, total=len(items))
