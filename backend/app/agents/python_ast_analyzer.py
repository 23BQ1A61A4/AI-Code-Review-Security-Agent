"""
Python structural analysis — real AST parsing, not regex.

Uses the standard library `ast` module to walk the actual parse tree for
bare excepts, mutable default arguments, global usage, parameter counts,
nesting depth, and function length. Where `radon` is installed, cyclomatic
complexity and the Maintainability Index are computed with radon's
published formulas instead of an invented scoring rule — see
https://radon.readthedocs.io/en/latest/intro.html for the formulas used.
"""
from __future__ import annotations

import ast


class _NestingVisitor(ast.NodeVisitor):
    """Tracks the deepest nesting of If/For/While/Try/With blocks."""

    def __init__(self) -> None:
        self.depth = 0
        self.max_depth = 0

    def _visit_block(self, node: ast.AST) -> None:
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    def visit_If(self, node): self._visit_block(node)
    def visit_For(self, node): self._visit_block(node)
    def visit_AsyncFor(self, node): self._visit_block(node)
    def visit_While(self, node): self._visit_block(node)
    def visit_Try(self, node): self._visit_block(node)
    def visit_With(self, node): self._visit_block(node)
    def visit_AsyncWith(self, node): self._visit_block(node)


def analyze_python_ast(code: str) -> dict:
    """Returns {bugs, code_smells, radon: {...}|None} or raises SyntaxError."""
    tree = ast.parse(code)
    bugs: list[dict] = []
    smells: list[str] = []

    func_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            bugs.append({
                "title": "Bare except clause", "severity": "Medium",
                "detail": f"A bare `except:` at line {node.lineno} silently swallows every exception, hiding real bugs.",
            })
        if isinstance(node, ast.Global):
            smells.append(f"Global state used at line {node.lineno} ({', '.join(node.names)})")

    for fn in func_nodes:
        args = fn.args
        named = [a for a in args.args if a.arg not in ("self", "cls")]
        if len(named) > 5:
            bugs.append({
                "title": "Function with too many parameters", "severity": "Low",
                "detail": f"`{fn.name}` (line {fn.lineno}) takes {len(named)} parameters — consider grouping them into an object.",
            })
        for default in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                bugs.append({
                    "title": "Mutable default argument", "severity": "Medium",
                    "detail": f"`{fn.name}` (line {fn.lineno}) uses a mutable default argument — it is shared across every call.",
                })
                break
        end_line = getattr(fn, "end_lineno", fn.lineno)
        length = end_line - fn.lineno
        if length > 45:
            bugs.append({
                "title": "Long function", "severity": "Low",
                "detail": f"`{fn.name}` (line {fn.lineno}) is ~{length} lines long — consider splitting responsibilities.",
            })
            smells.append(f"Long method: `{fn.name}`")

    nv = _NestingVisitor()
    nv.visit(tree)
    if nv.max_depth > 4:
        bugs.append({
            "title": "Deep nesting", "severity": "Medium",
            "detail": f"Code nests {nv.max_depth} block levels deep — consider guard clauses or extracting helper functions.",
        })
        smells.append("Deep nesting")

    if not func_nodes and len([l for l in code.splitlines() if l.strip()]) > 15:
        smells.append("No functions defined — logic is not decomposed")

    radon_data = _radon_metrics(code)

    return {"bugs": bugs, "code_smells": smells or ["No significant code smells detected."],
            "radon": radon_data, "max_nesting_depth": nv.max_depth}


def _radon_metrics(code: str) -> dict | None:
    """Cyclomatic complexity + Maintainability Index via radon, if installed."""
    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit
    except ImportError:
        return None
    try:
        blocks = cc_visit(code)
        complexities = [b.complexity for b in blocks]
        avg_cc = sum(complexities) / len(complexities) if complexities else 1.0
        mi = mi_visit(code, multi=True)
        return {
            "avg_cyclomatic_complexity": round(avg_cc, 2),
            "max_cyclomatic_complexity": max(complexities) if complexities else 1,
            "maintainability_index": round(mi, 2),
            "functions": [{"name": b.name, "complexity": b.complexity, "rank": _cc_rank(b.complexity)} for b in blocks],
        }
    except Exception:
        return None


def _cc_rank(cc: int) -> str:
    """Radon's own A–F cyclomatic-complexity ranking bands."""
    if cc <= 5: return "A"
    if cc <= 10: return "B"
    if cc <= 20: return "C"
    if cc <= 30: return "D"
    if cc <= 40: return "E"
    return "F"
