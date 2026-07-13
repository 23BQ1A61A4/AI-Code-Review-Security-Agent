"""
Finding merge logic — Module 3.

When multiple scanners (static rules, LLM, and later Bandit/Semgrep/etc.)
report what's really the same underlying vulnerability, we don't want
duplicate entries in the findings list — but we also must not lose evidence
from either source. This module groups findings that look like the same
issue (same category, nearby line number) and merges each group into one
finding that:
  - keeps the higher-severity/higher-confidence finding as the base
  - concatenates evidence from every finding in the group (deduplicated)
  - raises confidence slightly, since independent sources agreeing is
    itself a signal
  - records every contributing source in `merged_from`

Findings that don't match anything else pass through unchanged — this is
purely additive; nothing is dropped, including the "no line number" case
(two findings with no line number in the same category are still merged
if that's the best available match).
"""

from typing import List, Optional

from app.models.security import SecurityFinding, SecurityFindingSource

_SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
_LINE_PROXIMITY_TOLERANCE = 3  # lines


def _lines_close(a: Optional[int], b: Optional[int]) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= _LINE_PROXIMITY_TOLERANCE


def merge_findings(findings: List[SecurityFinding]) -> List[SecurityFinding]:
    """Group by (category, nearby line number) and merge each group."""
    groups: List[List[SecurityFinding]] = []

    for finding in findings:
        placed = False
        for group in groups:
            representative = group[0]
            if representative.category == finding.category and _lines_close(representative.line_number, finding.line_number):
                group.append(finding)
                placed = True
                break
        if not placed:
            groups.append([finding])

    merged: List[SecurityFinding] = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        primary = max(group, key=lambda f: (_SEVERITY_RANK.get(f.severity.value, 0), f.confidence_score))
        evidence_parts = []
        for f in group:
            if f.evidence and f.evidence not in evidence_parts:
                evidence_parts.append(f.evidence)
        sources = []
        for f in group:
            if f.source not in sources:
                sources.append(f.source)

        merged.append(primary.model_copy(update={
            "evidence": " | ".join(evidence_parts),
            "confidence_score": min(1.0, primary.confidence_score + 0.15),
            "source": SecurityFindingSource.MERGED,
            "merged_from": sources,
        }))

    return merged
