"""
Code Analysis Module — data models.

Severity and FindingSource are defined here (not in submission.py) because
later agents (Security Vulnerability, Remediation — Modules 3-4) will also
produce findings with severities, and this keeps that shared vocabulary in
one place instead of duplicating the enum per agent.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.submission import Language


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class FindingSource(str, Enum):
    """Where a finding came from — lets the frontend/report distinguish
    deterministic static-analysis findings from LLM semantic judgments."""
    STATIC = "static_analysis"
    LLM = "llm_semantic"


class CodeFinding(BaseModel):
    title: str
    description: str = Field(..., min_length=1)
    severity: Severity
    category: str  # e.g. "Long Method", "SOLID: Single Responsibility Principle", "Design Anti-pattern"
    filename: str
    line_number: Optional[int] = None
    recommendation: str = Field(..., min_length=1)
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    source: FindingSource


class CodeAnalysisResult(BaseModel):
    submission_id: str
    filename: str
    language: Language
    quality_score: int
    maintainability_score: int
    complexity_score: int
    maintainability_index: Optional[float] = None  # classic SEI/Microsoft MI formula, 0-100
    average_cyclomatic_complexity: Optional[float] = None
    average_cognitive_complexity: Optional[float] = None
    findings: List[CodeFinding]
    analyzed_at: datetime

