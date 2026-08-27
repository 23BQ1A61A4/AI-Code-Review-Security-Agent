"""
Java structural analysis — real parsing via `javalang` (a pure-Python Java
parser), not regex over source text.

Two javalang facilities are used, chosen for how stable/well-documented
each is in javalang's own API:
  - `javalang.parse.parse(code)` + `tree.filter(javalang.tree.X)` for
    method declarations, parameter counts, and empty-catch detection —
    the canonical, documented way to query a javalang AST.
  - `javalang.tokenizer.tokenize(code)` for brace-nesting depth and a
    statement-count proxy — deliberately used instead of walking
    `then_statement`/`body`/etc. AST attributes, whose exact shape
    (single node vs. list vs. block wrapper) isn't something this
    environment can verify against the real library before the demo, so
    the token stream (a flat, unambiguous sequence) is the safer choice.

If `javalang` isn't installed, or the snippet isn't parseable (e.g. a
bare method fragment without a class wrapper), this degrades to a
brace-depth / line-count heuristic as an explicit, clearly-labelled last
resort — there's no pure-Python equivalent of bandit/radon for Java
without a JVM (PMD/SpotBugs need one), so this is the honest ceiling for
a JVM-free backend.
"""
from __future__ import annotations


def analyze_java_ast(code: str) -> dict | None:
    """Returns {bugs, code_smells, max_nesting_depth} via javalang, or None if unavailable/unparseable."""
    try:
        import javalang
    except ImportError:
        return None

    try:
        tree = javalang.parse.parse(code)
    except Exception:
        return None  # not a full compilation unit, or a genuine syntax error — let the caller fall back

    bugs: list[dict] = []
    smells: list[str] = []

    for _, method in tree.filter(javalang.tree.MethodDeclaration):
        params = list(method.parameters or [])
        if len(params) > 5:
            bugs.append({
                "title": "Method with too many parameters", "severity": "Low",
                "detail": f"`{method.name}` takes {len(params)} parameters — consider grouping them into an object.",
            })

    empty_catches = 0
    for _, catch in tree.filter(javalang.tree.CatchClause):
        # An empty catch block (no statements) is the Java analogue of Python's bare `except: pass`.
        block = getattr(catch, "block", None)
        if block is not None and len(block) == 0:
            empty_catches += 1
    if empty_catches:
        smells.append(f"Empty catch block — exception silently swallowed ({empty_catches}x)")

    # Brace-depth nesting and a statement-count proxy from the real token
    # stream (robust regardless of how javalang shapes nested statement
    # attributes on individual node types).
    max_depth, brace_tokens = _brace_depth_from_tokens(code, javalang)
    if max_depth > 4:
        bugs.append({
            "title": "Deep nesting", "severity": "Medium",
            "detail": f"Code nests {max_depth} block levels deep — consider guard clauses or extracting helper methods.",
        })
        smells.append("Deep nesting")

    method_count = sum(1 for _ in tree.filter(javalang.tree.MethodDeclaration))
    line_count = len([l for l in code.splitlines() if l.strip()])
    if method_count and (line_count / method_count) > 45:
        smells.append("Long method(s) — average method length is high")
        bugs.append({
            "title": "Long method(s)", "severity": "Low",
            "detail": f"Average method length is ~{line_count // method_count} lines — consider splitting responsibilities.",
        })

    return {
        "bugs": bugs,
        "code_smells": smells or ["No significant code smells detected."],
        "max_nesting_depth": max_depth,
    }


def _brace_depth_from_tokens(code: str, javalang) -> tuple[int, int]:
    """Nesting depth counted from javalang's own tokenizer (so it's still
    library-derived, not a raw string scan) — counts `{`/`}` separator
    tokens rather than scanning characters directly, which correctly
    ignores braces that appear inside string/char literals or comments,
    unlike a plain character scan."""
    depth = max_depth = 0
    brace_count = 0
    try:
        for tok in javalang.tokenizer.tokenize(code):
            if isinstance(tok, javalang.tokenizer.Separator):
                if tok.value == "{":
                    depth += 1
                    brace_count += 1
                    max_depth = max(max_depth, depth)
                elif tok.value == "}":
                    depth = max(0, depth - 1)
    except Exception:
        return 0, 0
    return max_depth, brace_count


def _char_brace_depth(code: str) -> int:
    depth = max_depth = 0
    for ch in code:
        if ch == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    return max_depth
