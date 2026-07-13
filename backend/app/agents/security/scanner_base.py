"""
SecurityScanner interface — Module 3.

Every source of security findings (our own static rule engine now; Bandit,
Semgrep, SpotBugs, Checkstyle later) implements this exact interface. The
SecurityVulnerabilityAgent holds a list of SecurityScanner instances and
calls `.scan()` on each uniformly — it doesn't know or care whether a given
scanner is a regex engine or a subprocess wrapping a real external tool.

This is what makes "plug in Bandit/Semgrep/SpotBugs/Checkstyle later without
changing the Security Agent API" true: adding a real tool means writing one
new class that implements `scan()` and appending an instance of it to the
agent's scanner list — nothing about SecurityVulnerabilityAgent.run(),
SecurityAnalysisService, or the API routes needs to change.
"""

from abc import ABC, abstractmethod
from typing import List

from app.models.security import SecurityFinding
from app.models.submission import Language


class SecurityScanner(ABC):
    source_name: str = "unknown_scanner"

    @abstractmethod
    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        """Return a list of SecurityFinding objects for the given code.
        Must never raise for "no findings" — return an empty list instead.
        May raise for genuine failures (e.g. a subprocess tool crashing);
        the agent is responsible for catching that per-scanner so one
        scanner failing doesn't take down the others."""
        raise NotImplementedError
