"""
Security Vulnerability Module — data models.

Deliberately a richer shape than app.models.analysis.CodeFinding: the spec
requires a CVSS-style risk score, a CWE ID, and raw evidence per finding,
none of which the Code Analysis Agent's findings need. Severity is reused
from app.models.analysis to keep one shared vocabulary across agents.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.analysis import Severity
from app.models.submission import Language


class SecurityFindingSource(str, Enum):
    """Where a finding came from. EXTERNAL_TOOL is reserved for when a real
    tool (Bandit, Semgrep, SpotBugs, Checkstyle) is plugged in later — the
    agent already knows how to merge findings tagged with this source, it
    just has none to merge yet. MERGED marks a finding that combined
    matching reports from 2+ sources into one (see agents/security/merge.py)."""
    STATIC_RULES = "static_rules"
    LLM = "llm_semantic"
    EXTERNAL_TOOL = "external_tool"
    MERGED = "merged"


class SecurityFinding(BaseModel):
    title: str
    description: str = Field(..., min_length=1)
    severity: Severity
    category: str  # one of the 17 spec categories, e.g. "SQL Injection"
    owasp_category: str
    cwe_id: Optional[str] = None
    risk_score: float = Field(..., ge=0.0, le=10.0)  # CVSS-style, 0-10
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: str = Field(..., min_length=1)  # matched code snippet or model's cited justification
    filename: str
    line_number: Optional[int] = None
    recommendation: str = Field(..., min_length=1)
    source: SecurityFindingSource
    merged_from: List[SecurityFindingSource] = Field(default_factory=list)  # populated only when merged


class SecurityAnalysisResult(BaseModel):
    submission_id: str
    filename: str
    language: Language
    security_score: int  # 0-100, aggregate (100 = no issues found)
    highest_risk_score: float  # 0-10, CVSS-style, max across all findings
    findings: List[SecurityFinding]
    analyzed_at: datetime
