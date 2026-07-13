"""
Submission Service — Module 1.

Owns submission storage and creation logic, isolated from the API layer so
that swapping in-memory storage for a real database later (Module 10+) only
requires changes here — the API routes and the future agent pipeline both
depend only on this service's interface, not its storage mechanism.

Also runs the Submission Module's two pieces of immediate feedback at
creation time — language auto-detection (for pasted code with no filename)
and a basic syntax check — rather than deferring both to the Code Analysis
Agent, so a caller finds out about a syntax error right away, without
having to run a full agent pipeline first.
"""

from typing import Dict, List, Optional

from app.config import MAX_CODE_CHARS
from app.models.submission import Language, Submission, SubmissionCreate
from app.services.syntax_check import check_syntax, detect_language_from_content


class SubmissionValidationError(Exception):
    """Raised when a submission can't be created — e.g. language wasn't
    given and couldn't be auto-detected from the content."""


class SubmissionService:
    def __init__(self):
        self._store: Dict[str, Submission] = {}

    def create(self, payload: SubmissionCreate) -> Submission:
        """Create a submission from pasted code. If `language` wasn't
        supplied, attempts content-based detection; raises
        SubmissionValidationError if detection is inconclusive rather than
        silently guessing."""
        code = payload.code[:MAX_CODE_CHARS]
        auto_detected = False

        language = payload.language
        if language is None:
            detected = detect_language_from_content(code)
            if detected is None:
                raise SubmissionValidationError(
                    "Could not auto-detect the language from this snippet — please specify 'language' explicitly."
                )
            language = detected
            auto_detected = True

        is_valid, error, error_line = check_syntax(code, language)

        submission = Submission(
            filename=payload.filename or "pasted-snippet",
            language=language,
            code=code,
            language_auto_detected=auto_detected,
            syntax_valid=is_valid,
            syntax_error=error,
            syntax_error_line=error_line,
        )
        self._store[submission.id] = submission
        return submission

    def create_from_file(self, filename: str, content: str, language: Optional[Language] = None) -> Submission:
        """Create a submission from an uploaded file, auto-detecting language from extension if not given."""
        code = content[:MAX_CODE_CHARS]
        auto_detected = language is None
        lang = language or self._detect_language(filename)

        is_valid, error, error_line = check_syntax(code, lang)

        submission = Submission(
            filename=filename,
            language=lang,
            code=code,
            language_auto_detected=auto_detected,
            syntax_valid=is_valid,
            syntax_error=error,
            syntax_error_line=error_line,
        )
        self._store[submission.id] = submission
        return submission

    def get(self, submission_id: str) -> Optional[Submission]:
        return self._store.get(submission_id)

    def all(self) -> List[Submission]:
        return list(self._store.values())

    @staticmethod
    def _detect_language(filename: str) -> Language:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return Language.JAVA if ext == "java" else Language.PYTHON


# Single shared instance for the app's lifetime (in-memory store, reset on restart).
# A later module can replace this with a dependency-injected, DB-backed service
# without changing anything in app/api/submission_routes.py.
submission_service = SubmissionService()

