"""
Code Analysis Agent (Milestone 2).

Analysis order, per language:
  1. LLM (Gemini), if configured and reachable.
  2. Real parser/library: Python's built-in `ast` module (+ `radon` for
     cyclomatic complexity / Maintainability Index if installed); Java via
     `javalang`'s AST if installed.
  3. Last-resort regex/heuristic fallback — only used when neither of the
     above is available (no network/API key AND the parsing library isn't
     installed), so the agent still returns a result offline.
"""
from __future__ import annotations

import json
import re

from .java_analyzer import analyze_java_ast
from .llm_client import LLMUnavailable, extract_json, generate
from .python_ast_analyzer import analyze_python_ast

# --- last-resort fallback only (used if ast/javalang parsing itself fails,
# e.g. the user pasted a code fragment rather than valid syntax) ---
BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*$", re.M)
TODO = re.compile(r"#\s*(TODO|FIXME|HACK)|//\s*(TODO|FIXME|HACK)", re.I)
MUTABLE_DEFAULT = re.compile(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})")
GLOBAL_KW = re.compile(r"^\s*global\s+\w+", re.M)
FUNC_DEF = re.compile(r"^\s*(def|public|private|protected|static)\s.*\(([^)]*)\)", re.M)


def _brace_nesting_depth(code: str) -> int:
    depth = max_depth = 0
    for ch in code:
        if ch == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    return max_depth


def _regex_fallback(code: str, language: str) -> dict:
    """Only reached when the real parser can't handle the snippet (e.g. a
    fragment without a class wrapper) and no LLM is available either."""
    bugs, smells = [], []
    if BARE_EXCEPT.search(code):
        bugs.append({"title": "Bare except clause", "severity": "Medium",
                     "detail": "A bare `except:` silently swallows every exception, hiding real bugs."})
    for m in FUNC_DEF.finditer(code):
        params = [p for p in m.group(2).split(",") if p.strip() and p.strip() not in ("self", "cls")]
        if len(params) > 5:
            bugs.append({"title": "Function with too many parameters", "severity": "Low",
                         "detail": f"A function takes {len(params)} parameters — consider grouping them into an object."})
    if MUTABLE_DEFAULT.search(code):
        bugs.append({"title": "Mutable default argument", "severity": "Medium",
                     "detail": "A mutable default argument (list/dict) is shared across every call and can leak state."})
    if GLOBAL_KW.search(code):
        smells.append("Global state / mutable global variable")
    if TODO.search(code):
        smells.append("Unresolved TODO/FIXME comment")
    depth = _brace_nesting_depth(code)
    if depth > 4:
        bugs.append({"title": "Deep nesting", "severity": "Medium",
                     "detail": f"Code nests roughly {depth} levels deep."})
        smells.append("Deep nesting")
    return {"bugs": bugs, "code_smells": smells or ["No significant code smells detected."], "engine": "regex-fallback"}


def analyze_local(code: str, language: str) -> dict:
    if language == "Python":
        try:
            result = analyze_python_ast(code)
            result["engine"] = "ast" + ("+radon" if result.get("radon") else "")
            return result
        except SyntaxError:
            pass  # fragment / invalid syntax — fall through to regex fallback
    elif language == "Java":
        result = analyze_java_ast(code)
        if result is not None:
            result["engine"] = "javalang"
            return result
    return _regex_fallback(code, language)


def analyze(code: str, language: str) -> dict:
    """Code Analysis Agent entry point — tries the LLM, falls back to real-parser analysis."""
    try:
        prompt = (
            f"Language: {language}.\n"
            f"Review the submitted code for real bugs, design anti-patterns, maintainability issues, and code smells.\n"
            f"Return a strict JSON object with this format:\n"
            f'{{"bugs": [{{"title": "string", "detail": "string with line number or context", "severity": "Low|Medium|High"}}],\n'
            f' "code_smells": ["string summary of code smell"]}}\n\n'
            f"Code to analyze:\n{code}"
        )
        raw = generate(prompt, system="You are an expert static code analysis AI agent. Return only valid JSON, without conversational prose.")
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            bugs = parsed.get("bugs") if isinstance(parsed.get("bugs"), list) else []
            smells = parsed.get("code_smells") if isinstance(parsed.get("code_smells"), list) else []
            return {
                "bugs": bugs,
                "code_smells": smells or ["No significant code smells detected."],
                "engine": "llm",
            }
        raise ValueError("Invalid JSON schema returned by LLM")
    except (LLMUnavailable, Exception):
        return analyze_local(code, language)
