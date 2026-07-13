"""
Basic syntax checking and content-based language detection — Submission Module.

Deliberately "basic," per the milestone's scope:
  - Python: real syntax validation via the standard library `ast.parse()` —
    this genuinely catches any Python syntax error, with an accurate line number.
  - Java: no compiler is available/wired in here, so this is a heuristic
    balanced-delimiter check (braces/parens/brackets), not full grammar
    validation. It catches the most common paste/upload mistakes (a missing
    closing brace, an unbalanced paren) but will not catch most semantic or
    finer-grained syntax errors — that's explicitly deferred to a real
    compiler/parser integration, out of scope for Milestone 1.

Language detection from pasted content (no filename to go by) is similarly
a lightweight heuristic — keyword/pattern scoring, not a real parser.
"""

import ast
import re
from typing import Optional, Tuple

from app.models.submission import Language


def check_python_syntax(code: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """Returns (is_valid, error_message, line_number)."""
    try:
        ast.parse(code)
        return True, None, None
    except SyntaxError as e:
        return False, f"{e.msg} (line {e.lineno})", e.lineno


_STRING_OR_COMMENT = re.compile(
    r'//.*?$|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
    re.MULTILINE | re.DOTALL,
)


def check_java_syntax_basic(code: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """Balanced-delimiter check only — see module docstring for what this
    does and doesn't catch. Strings/comments are stripped first so braces
    inside them don't produce false imbalance reports."""
    stripped = _STRING_OR_COMMENT.sub("", code)
    pairs = {'{': '}', '(': ')', '[': ']'}
    closing_to_opening = {v: k for k, v in pairs.items()}
    stack = []

    for i, ch in enumerate(stripped):
        if ch in pairs:
            stack.append((ch, i))
        elif ch in closing_to_opening:
            if not stack or stack[-1][0] != closing_to_opening[ch]:
                line_number = stripped[:i].count("\n") + 1
                expected = pairs[stack[-1][0]] if stack else "nothing"
                return False, f"Unexpected '{ch}' — expected '{expected}' (line {line_number})", line_number
            stack.pop()

    if stack:
        open_char, pos = stack[-1]
        line_number = stripped[:pos].count("\n") + 1
        return False, f"Unclosed '{open_char}' (line {line_number})", line_number

    return True, None, None


def check_syntax(code: str, language: Language) -> Tuple[bool, Optional[str], Optional[int]]:
    if language == Language.PYTHON:
        return check_python_syntax(code)
    return check_java_syntax_basic(code)


_PYTHON_SIGNALS = re.compile(r"^\s*(def |class \w+.*:|import |from \w+ import|print\()", re.MULTILINE)
_JAVA_SIGNALS = re.compile(r"\b(public|private|protected)\s+(class|static|void|interface)\b|System\.out\.println")


def detect_language_from_content(code: str) -> Optional[Language]:
    """Best-effort heuristic for pasted code with no filename to detect
    from. Returns None (rather than guessing) if there's no clear signal
    either way — callers should treat that as "detection failed," not as
    a default."""
    python_score = len(_PYTHON_SIGNALS.findall(code))
    java_score = len(_JAVA_SIGNALS.findall(code))

    if python_score == 0 and java_score == 0:
        return None
    return Language.PYTHON if python_score >= java_score else Language.JAVA
