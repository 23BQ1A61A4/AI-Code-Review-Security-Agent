"""
Placeholder external-tool scanners — Module 3.

These exist to prove the architecture, not to run real scans yet: each
implements SecurityScanner exactly like StaticSecurityRuleEngine does, and
each currently returns an empty list. Wiring in the real tool later means
replacing the body of `scan()` with a subprocess call and a parser for that
tool's output format — the class signature, and everything that calls it,
stays the same.

Example of what BanditScanner.scan() becomes once wired in for real:
    result = subprocess.run(["bandit", "-f", "json", filepath], capture_output=True)
    return [self._to_security_finding(issue) for issue in json.loads(result.stdout)["results"]]
"""

from typing import List

from app.agents.security.scanner_base import SecurityScanner
from app.models.security import SecurityFinding
from app.models.submission import Language


class BanditScanner(SecurityScanner):
    """Python-only. Bandit is a mature static security linter for Python —
    plugging it in for real would replace scan() with a subprocess call to
    `bandit -f json` and a small adapter mapping Bandit's test IDs (e.g.
    B608 = SQL injection) to our SecurityFinding shape / CWE IDs."""
    source_name = "bandit"

    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        if language != Language.PYTHON:
            return []
        return []  # not yet implemented — see module docstring


class SemgrepScanner(SecurityScanner):
    """Python and Java. Semgrep runs rule-based pattern matching similar in
    spirit to our StaticSecurityRuleEngine but far more robust (real AST
    matching, community rule packs for OWASP categories). Wiring it in
    replaces scan() with a subprocess call to `semgrep --json --config=auto`."""
    source_name = "semgrep"

    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        return []  # not yet implemented — see module docstring


class SpotBugsScanner(SecurityScanner):
    """Java-only, and notably needs COMPILED .class files, not source — so
    wiring this in for real also means adding a compile step before scanning
    (e.g. via a temporary javac invocation) ahead of running SpotBugs with
    the FindSecBugs plugin for security-specific rules."""
    source_name = "spotbugs"

    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        if language != Language.JAVA:
            return []
        return []  # not yet implemented — see module docstring


class CheckstyleScanner(SecurityScanner):
    """Java-only. Checkstyle is primarily a style/convention tool rather
    than a security scanner, but some of its rules (e.g. flagging
    System.out/System.err usage that could leak sensitive data, or missing
    final on fields that should be immutable) have security relevance.
    Wiring it in means a subprocess call to the Checkstyle jar with a
    security-relevant subset of rules configured."""
    source_name = "checkstyle"

    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        if language != Language.JAVA:
            return []
        return []  # not yet implemented — see module docstring
