"""
Code Submission Module — data models.

Defines the request/response contracts and the internal Submission entity.
Kept independent of any storage mechanism (see services/submission_service.py)
so the pipeline agents built in later modules only ever depend on this shape,
never on how a submission happens to be stored.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    PYTHON = "Python"
    JAVA = "Java"


class SubmissionStatus(str, Enum):
    RECEIVED = "received"      # submitted, not yet picked up by the agent pipeline
    QUEUED = "queued"          # Module 2+: waiting for the Code Analysis Agent
    ANALYZING = "analyzing"    # Module 2+: pipeline currently running
    COMPLETED = "completed"    # Module 2+: all agents finished
    FAILED = "failed"          # Module 2+: pipeline errored


class SubmissionCreate(BaseModel):
    """Request body for pasting code directly. `language` is optional — if
    omitted, it's auto-detected from the pasted content (best-effort; see
    app/services/syntax_check.py). Detection can fail on very short or
    ambiguous snippets, so callers that know the language should still send
    it explicitly rather than relying on detection."""
    language: Optional[Language] = None
    code: str = Field(..., min_length=1, max_length=20000)
    filename: Optional[str] = None

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("code must not be blank")
        return v


class Submission(BaseModel):
    """Internal entity — what actually gets stored."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    language: Language
    code: str
    status: SubmissionStatus = SubmissionStatus.RECEIVED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    language_auto_detected: bool = False
    syntax_valid: bool = True
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None


class SubmissionResponse(BaseModel):
    """What the API returns — deliberately omits full code to keep responses light."""
    id: str
    filename: str
    language: Language
    language_auto_detected: bool
    status: SubmissionStatus
    created_at: datetime
    code_length: int
    syntax_valid: bool
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None


class SubmissionListResponse(BaseModel):
    submissions: List[SubmissionResponse]
    total: int
