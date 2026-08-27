"""
Milestone 1 — Code Submission Module.

Given raw code (+ optional filename / declared language), detects the
language and runs a basic syntax check:
  - Python: compiled with the built-in `compile()` — a real parse, not a
    heuristic, so it catches genuine `SyntaxError`s.
  - Java / others: no full compiler available offline, so we run a
    lightweight structural check (balanced braces/parens/brackets and
    balanced quotes) as a best-effort validity signal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

EXT_TO_LANG = {
    "py": "Python", "java": "Java", "js": "JavaScript", "ts": "TypeScript",
    "c": "C", "cpp": "C++", "cc": "C++", "h": "C", "hpp": "C++",
}

LANG_SIGNATURES = [
    ("Python", re.compile(r"^\s*(def |import |from \S+ import|class \w+.*:|print\()", re.M)),
    ("Java", re.compile(r"\b(public|private|protected)\s+(static\s+)?(class|void|int|String)\b")),
    ("JavaScript", re.compile(r"\b(function\s+\w*\s*\(|const |let |=>|console\.log)")),
]


@dataclass
class DetectionResult:
    language: str
    auto_detected: bool
    syntax_valid: bool
    syntax_error: str | None


def detect_language(code: str, filename: str | None, declared: str | None) -> tuple[str, bool]:
    if declared and declared != "Auto-detect":
        return declared, False
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in EXT_TO_LANG:
            return EXT_TO_LANG[ext], True
    for lang, pattern in LANG_SIGNATURES:
        if pattern.search(code):
            return lang, True
    return "Unknown", True


def _check_balanced(code: str) -> str | None:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    in_str: str | None = None
    i = 0
    while i < len(code):
        ch = code[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
        elif ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack[-1] != pairs[ch]:
                return f"Unbalanced '{ch}' near character {i}"
            stack.pop()
        i += 1
    if stack:
        return f"Unclosed '{stack[-1]}'"
    if in_str:
        return f"Unterminated string starting with {in_str}"
    return None


def validate_syntax(code: str, language: str) -> tuple[bool, str | None]:
    if language == "Python":
        try:
            compile(code, "<submission>", "exec")
            return True, None
        except SyntaxError as e:
            return False, f"{e.msg} (line {e.lineno})"
    # Java / JS / TS / C / C++: best-effort structural check.
    err = _check_balanced(code)
    return (err is None), err


def process_submission(code: str, filename: str | None, declared_language: str | None) -> DetectionResult:
    language, auto = detect_language(code, filename, declared_language)
    valid, error = validate_syntax(code, language)
    return DetectionResult(language=language, auto_detected=auto, syntax_valid=valid, syntax_error=error)
