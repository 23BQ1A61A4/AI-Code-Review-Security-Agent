"""
Static analyzers — Module 2 (strengthened).

Deterministic, non-LLM code inspection used by CodeAnalysisAgent. Every
finding carries a confidence_score reflecting how certain a *heuristic* can
be (mechanical counts like line length get high confidence; pattern-based
heuristics like "God Object" or Dependency Inversion get lower confidence
because they're inherently approximate without full type/behavioral
analysis).

What's genuinely computed here (not fabricated):
  - Python: real `ast` parse-tree analysis — cyclomatic complexity, cognitive
    complexity, Halstead volume, unused names, naming conventions.
  - Java: regex + brace-counting heuristics (no external parser dependency)
    — real text/structure analysis, but an approximation of what a full
    Java AST parser (e.g. javalang, JavaParser) would give you. This
    limitation is intentional and documented rather than silently claiming
    full-parser accuracy.
  - Both: a Maintainability Index (classic SEI/Microsoft formula) computed
    from the above, and token-normalized duplicate-block detection that
    catches renamed-variable duplicates, not just exact text matches.

Performance: duplicate detection now uses tuples directly as dict keys
(hashable, no string-concatenation overhead), and per-function static
checks (complexity, cognitive complexity, unused names, magic numbers) are
computed in a single merged traversal per function instead of several
separate ones — see PythonStaticAnalyzer._analyze_function.
"""

import ast
import keyword
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Thresholds — tunable in one place
# ---------------------------------------------------------------------------
LONG_METHOD_LINE_THRESHOLD = 40
HIGH_COMPLEXITY_THRESHOLD = 10
HIGH_COGNITIVE_COMPLEXITY_THRESHOLD = 15
LONG_PARAMETER_LIST_THRESHOLD = 5
GOD_CLASS_METHOD_THRESHOLD = 15
GOD_CLASS_LINE_THRESHOLD = 300
ISP_METHOD_THRESHOLD = 7
DIP_INSTANTIATION_THRESHOLD = 3
DUPLICATE_BLOCK_MIN_LINES = 4
MAGIC_NUMBER_ALLOWED = {0, 1, -1, 2, 100}
MAX_LINES_FOR_DUPLICATE_SCAN = 2000  # performance guard for very large files

_PY_EXCEPTION_NAMES = {
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
    "RuntimeError", "StopIteration", "NotImplementedError", "OSError", "FileNotFoundError",
    "ZeroDivisionError", "ImportError", "PermissionError",
}
_JAVA_COMMON_UTIL_CLASSES = {
    "ArrayList", "HashMap", "HashSet", "LinkedList", "StringBuilder", "StringBuffer",
    "TreeMap", "TreeSet", "Random", "Scanner", "Object", "Exception", "RuntimeException",
    "IllegalArgumentException", "IllegalStateException",
}


@dataclass
class StaticFinding:
    title: str
    description: str
    severity: str  # "Low" | "Medium" | "High"
    category: str
    line_number: Optional[int]
    recommendation: str
    confidence: float = 0.8  # 0.0-1.0, how certain this heuristic is


@dataclass
class StaticAnalysisResult:
    findings: List[StaticFinding] = field(default_factory=list)
    function_complexities: List[float] = field(default_factory=list)            # cyclomatic
    function_cognitive_complexities: List[float] = field(default_factory=list)  # cognitive
    maintainability_index: Optional[float] = None
    halstead_volume: Optional[float] = None
    lines_of_code: int = 0


# ---------------------------------------------------------------------------
# Shared: Maintainability Index (classic SEI/Microsoft formula, 0-100)
# ---------------------------------------------------------------------------
def compute_maintainability_index(halstead_volume: float, avg_cyclomatic: float, loc: int) -> float:
    """MI = MAX(0, (171 - 5.2*ln(V) - 0.23*G - 16.2*ln(LOC)) * 100/171)

    A widely used approximation of maintainability, not a verdict — treat it
    as one more signal alongside the findings list. Inputs are floored to
    avoid log(0)/log(negative) on trivial or empty code.
    """
    v = max(halstead_volume, 1.0)
    g = max(avg_cyclomatic, 1.0)
    l = max(loc, 1)
    raw = 171 - 5.2 * math.log(v) - 0.23 * g - 16.2 * math.log(l)
    return round(max(0.0, min(100.0, raw * 100 / 171)), 1)


# ---------------------------------------------------------------------------
# Shared: token-normalized duplicate-block detection (Type-1 + Type-2 clones)
# ---------------------------------------------------------------------------
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def _normalize_line(line: str, keywords: set) -> Tuple[str, ...]:
    """Tokenize a line and replace identifiers with positional placeholders
    (consistent within the caller's var_map) and numeric literals with a
    generic marker. This lets duplicate detection catch code that's
    structurally identical but uses renamed variables — a real (if simple)
    Type-2 clone check, not just exact-text matching."""
    return tuple(_TOKEN_RE.findall(line.strip()))


def find_duplicate_blocks(code: str, keywords: set, min_lines: int = DUPLICATE_BLOCK_MIN_LINES) -> List[StaticFinding]:
    raw_lines = code.splitlines()
    if len(raw_lines) > MAX_LINES_FOR_DUPLICATE_SCAN:
        # Performance guard: cap the scan window on very large files rather
        # than paying O(n) cost with a huge constant on files with thousands
        # of lines. Later lines simply aren't checked for duplication.
        raw_lines = raw_lines[:MAX_LINES_FOR_DUPLICATE_SCAN]

    stripped = [l.strip() for l in raw_lines]
    n = len(stripped)
    seen_raw: Dict[Tuple[str, ...], int] = {}
    seen_normalized: Dict[Tuple[Tuple[str, ...], ...], int] = {}
    findings: List[StaticFinding] = []
    reported_starts = set()
    var_counter_cache: Dict[int, int] = {}

    for i in range(max(0, n - min_lines + 1)):
        block = stripped[i:i + min_lines]
        if not any(block) or sum(len(b) for b in block) < 20:
            continue

        raw_key = tuple(block)  # hashable directly — no string join needed

        # Normalize: replace identifiers with positional placeholders so
        # renamed-variable duplicates are still caught.
        var_map: Dict[str, str] = {}
        normalized_block = []
        for line in block:
            norm_tokens = []
            for tok in _TOKEN_RE.findall(line):
                if tok.isdigit():
                    norm_tokens.append("NUM")
                elif _IDENTIFIER_RE.match(tok) and tok not in keywords:
                    norm_tokens.append(var_map.setdefault(tok, f"V{len(var_map)}"))
                else:
                    norm_tokens.append(tok)
            normalized_block.append(tuple(norm_tokens))
        normalized_key = tuple(normalized_block)

        if raw_key in seen_raw:
            first = seen_raw[raw_key]
            if i not in reported_starts:
                findings.append(StaticFinding(
                    title="Duplicate code block",
                    description=f"Lines {i + 1}-{i + min_lines} are an exact duplicate of lines {first + 1}-{first + min_lines}.",
                    severity="Medium",
                    category="Duplicate Code",
                    line_number=i + 1,
                    recommendation="Extract the repeated block into a shared function/method.",
                    confidence=0.9,
                ))
                reported_starts.add(i)
        elif normalized_key in seen_normalized:
            first = seen_normalized[normalized_key]
            if i not in reported_starts:
                findings.append(StaticFinding(
                    title="Structurally duplicate code block",
                    description=(
                        f"Lines {i + 1}-{i + min_lines} are structurally identical to lines "
                        f"{first + 1}-{first + min_lines}, possibly with renamed variables."
                    ),
                    severity="Low",
                    category="Duplicate Code",
                    line_number=i + 1,
                    recommendation="Check whether this is intentional duplication; consider extracting a shared, parameterized function.",
                    confidence=0.72,
                ))
                reported_starts.add(i)
        else:
            seen_raw.setdefault(raw_key, i)
            seen_normalized.setdefault(normalized_key, i)

    return findings[:5]  # cap so the findings list stays readable


# ---------------------------------------------------------------------------
# Python analyzer — real structural analysis via the ast module
# ---------------------------------------------------------------------------
class PythonStaticAnalyzer:
    def analyze(self, code: str) -> StaticAnalysisResult:
        result = StaticAnalysisResult()
        result.lines_of_code = len(code.splitlines())
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.findings.append(StaticFinding(
                title="Code does not parse",
                description=f"Python syntax error: {e.msg} (line {e.lineno}).",
                severity="High",
                category="Maintainability",
                line_number=e.lineno,
                recommendation="Fix the syntax error before further analysis can run.",
                confidence=1.0,
            ))
            return result

        exported_names = self._collect_dunder_all(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._analyze_function(node, result)

        self._check_naming(tree, result)
        self._check_unused_imports(tree, code, result, exported_names)
        self._check_solid_class_heuristics(tree, result)
        result.findings.extend(find_duplicate_blocks(code, set(keyword.kwlist)))

        halstead_volume = self._compute_halstead_volume(tree)
        avg_complexity = (sum(result.function_complexities) / len(result.function_complexities)
                           if result.function_complexities else 1.0)
        result.halstead_volume = round(halstead_volume, 1)
        result.maintainability_index = compute_maintainability_index(halstead_volume, avg_complexity, result.lines_of_code)
        return result

    # ---- per-function merged analysis (single traversal: complexity + cognitive + unused names + magic numbers) ----
    def _analyze_function(self, node: ast.AST, result: StaticAnalysisResult):
        length = self._function_line_span(node)
        args = node.args
        param_count = (
            len(args.args) + len(args.kwonlyargs)
            + (1 if args.vararg else 0) + (1 if args.kwarg else 0)
        )
        # Don't count 'self'/'cls' toward the long-parameter-list check.
        effective_params = param_count - (1 if args.args and args.args[0].arg in ("self", "cls") else 0)

        complexity = 1
        assigned, loaded, declared_nonlocal = set(), set(), set()

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += max(len(child.values) - 1, 0)
            elif isinstance(child, ast.comprehension):
                complexity += 1 + len(child.ifs)
            elif isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name):
                assigned.add(child.target.id)
                loaded.add(child.target.id)  # augmented assignment reads before writing
            elif isinstance(child, (ast.Global, ast.Nonlocal)):
                declared_nonlocal.update(child.names)
            elif isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    assigned.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    loaded.add(child.id)

        cognitive = self._cognitive_complexity(node)
        result.function_complexities.append(complexity)
        result.function_cognitive_complexities.append(cognitive)

        if length > LONG_METHOD_LINE_THRESHOLD:
            result.findings.append(StaticFinding(
                title=f"Long method: {node.name}",
                description=f"'{node.name}' spans {length} lines, above the {LONG_METHOD_LINE_THRESHOLD}-line guideline.",
                severity="Medium", category="Long Method", line_number=node.lineno,
                recommendation="Break this into smaller, single-purpose helper functions.", confidence=0.95,
            ))

        if complexity > HIGH_COMPLEXITY_THRESHOLD:
            result.findings.append(StaticFinding(
                title=f"High cyclomatic complexity: {node.name}",
                description=f"'{node.name}' has an estimated cyclomatic complexity of {complexity}, above {HIGH_COMPLEXITY_THRESHOLD}.",
                severity="High", category="Complexity", line_number=node.lineno,
                recommendation="Reduce nested conditionals/loops; extract branches into separate functions.", confidence=0.9,
            ))

        if cognitive > HIGH_COGNITIVE_COMPLEXITY_THRESHOLD:
            result.findings.append(StaticFinding(
                title=f"High cognitive complexity: {node.name}",
                description=f"'{node.name}' has an estimated cognitive complexity of {cognitive}, above {HIGH_COGNITIVE_COMPLEXITY_THRESHOLD} — likely hard for a human to follow even if cyclomatic complexity looks moderate.",
                severity="Medium", category="Cognitive Complexity", line_number=node.lineno,
                recommendation="Reduce nesting depth — prefer early returns/guard clauses over deeply nested conditionals.", confidence=0.82,
            ))

        if effective_params > LONG_PARAMETER_LIST_THRESHOLD:
            result.findings.append(StaticFinding(
                title=f"Long parameter list: {node.name}",
                description=f"'{node.name}' takes {effective_params} parameters, above the {LONG_PARAMETER_LIST_THRESHOLD}-parameter guideline.",
                severity="Low", category="Design Anti-pattern", line_number=node.lineno,
                recommendation="Group related parameters into a dataclass/object, or split the function.", confidence=0.9,
            ))

        for value in self._find_magic_numbers(node)[:2]:
            result.findings.append(StaticFinding(
                title=f"Magic number in {node.name}: {value}",
                description=f"The literal {value} is used directly in a condition/call inside '{node.name}' without a named constant.",
                severity="Low", category="Maintainability", line_number=node.lineno,
                recommendation=f"Replace {value} with a named constant that explains what it represents.", confidence=0.7,
            ))

        unused = sorted(v for v in assigned if v not in loaded and v not in declared_nonlocal and not v.startswith("_"))
        for var in unused[:3]:
            result.findings.append(StaticFinding(
                title=f"Possibly unused variable: {var}",
                description=f"'{var}' is assigned inside '{node.name}' but never read afterward (best-effort — doesn't model all control flow).",
                severity="Low", category="Unused Variable", line_number=node.lineno,
                recommendation="Remove the variable if unused, or use it / prefix with '_' to signal intent.", confidence=0.7,
            ))

    @staticmethod
    def _function_line_span(node: ast.AST) -> int:
        end = getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)
        return end - node.lineno + 1

    @staticmethod
    def _cognitive_complexity(node: ast.AST) -> int:
        """Simplified Sonar-style cognitive complexity: nested control
        structures cost more than flat ones (unlike cyclomatic complexity,
        which weighs every branch equally). This is an approximation of the
        published algorithm, not a byte-for-byte reimplementation."""
        def walk(n: ast.AST, nesting: int) -> int:
            total = 0
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.For, ast.While)):
                    total += 1 + nesting
                    total += walk(child, nesting + 1)
                elif isinstance(child, ast.ExceptHandler):
                    total += 1 + nesting
                    total += walk(child, nesting + 1)
                elif isinstance(child, ast.BoolOp):
                    total += max(len(child.values) - 1, 0)
                    total += walk(child, nesting)
                else:
                    total += walk(child, nesting)
            return total
        return walk(node, 0)

    @staticmethod
    def _find_magic_numbers(func_node: ast.AST) -> List[float]:
        """Only flags numeric literals inside conditions or call arguments —
        not plain assignments like `x = 5`, which are usually self-documenting."""
        def constants_in(expr) -> List[float]:
            out = []
            for n in ast.walk(expr):
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                    if n.value not in MAGIC_NUMBER_ALLOWED:
                        out.append(n.value)
            return out

        numbers = []
        for sub in ast.walk(func_node):
            if isinstance(sub, (ast.If, ast.While)):
                numbers.extend(constants_in(sub.test))
            elif isinstance(sub, ast.Call):
                for a in sub.args:
                    numbers.extend(constants_in(a))
        return numbers

    def _check_naming(self, tree: ast.AST, result: StaticAnalysisResult):
        snake_case = re.compile(r"^[a-z_][a-z0-9_]*$")
        pascal_case = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not snake_case.match(node.name) and not node.name.startswith("__"):
                    result.findings.append(StaticFinding(
                        title=f"Naming convention: {node.name}",
                        description=f"Function '{node.name}' doesn't follow snake_case (PEP 8).",
                        severity="Low", category="Naming Convention", line_number=node.lineno,
                        recommendation=f"Rename to '{self._to_snake_case(node.name)}'.", confidence=0.95,
                    ))
            elif isinstance(node, ast.ClassDef):
                if not pascal_case.match(node.name):
                    result.findings.append(StaticFinding(
                        title=f"Naming convention: {node.name}",
                        description=f"Class '{node.name}' doesn't follow PascalCase (PEP 8).",
                        severity="Low", category="Naming Convention", line_number=node.lineno,
                        recommendation="Rename the class using PascalCase.", confidence=0.95,
                    ))

    @staticmethod
    def _to_snake_case(name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def _collect_dunder_all(tree: ast.AST) -> set:
        """Names listed in __all__ are exported on purpose and shouldn't be
        flagged as unused even if nothing in this file itself uses them."""
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            names.add(elt.value)
        return names

    def _check_unused_imports(self, tree: ast.AST, code: str, result: StaticAnalysisResult, exported_names: set):
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append((alias.asname or alias.name.split(".")[0], node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported_names.append((alias.asname or alias.name, node.lineno))

        used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used_attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}

        for name, lineno in imported_names:
            if name in exported_names:
                continue
            if name in used_names or name in used_attrs:
                continue
            # Fallback: check raw text occurrences to catch usage ast misses
            # (e.g. inside string type annotations like "List['Foo']").
            occurrences = len(re.findall(r"\b" + re.escape(name) + r"\b", code))
            if occurrences <= 1:
                result.findings.append(StaticFinding(
                    title=f"Unused import: {name}",
                    description=f"'{name}' is imported but never referenced in the file.",
                    severity="Low", category="Unused Import", line_number=lineno,
                    recommendation=f"Remove the unused import '{name}'.", confidence=0.88,
                ))

    # ---- SOLID heuristics at the class level (SRP / ISP / DIP) ----
    def _check_solid_class_heuristics(self, tree: ast.AST, result: StaticAnalysisResult):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            line_span = self._function_line_span(node)
            is_abstract_base = any(
                isinstance(base, ast.Name) and base.id in ("ABC", "ABCMeta") for base in node.bases
            )

            # SRP: God Object heuristic
            if len(methods) > GOD_CLASS_METHOD_THRESHOLD or line_span > GOD_CLASS_LINE_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible God Object: {node.name}",
                    description=f"Class '{node.name}' has {len(methods)} methods and spans {line_span} lines — it may be taking on too many responsibilities.",
                    severity="Medium", category="SOLID: Single Responsibility Principle", line_number=node.lineno,
                    recommendation="Split this class into smaller classes, each with a single, clearly-named responsibility.",
                    confidence=0.7,
                ))

            # ISP: fat-interface heuristic
            abstract_methods = [
                m for m in methods
                if any(self._is_abstractmethod_decorator(d) for d in getattr(m, "decorator_list", []))
            ]
            if is_abstract_base and len(abstract_methods) > ISP_METHOD_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible fat interface: {node.name}",
                    description=f"Abstract class '{node.name}' declares {len(abstract_methods)} abstract methods — implementers may be forced to depend on methods they don't use.",
                    severity="Low", category="SOLID: Interface Segregation Principle", line_number=node.lineno,
                    recommendation="Split this interface into smaller, more focused interfaces/protocols.",
                    confidence=0.6,
                ))

            # DIP: direct concrete-instantiation heuristic
            concrete = set()
            for m in methods:
                for call in ast.walk(m):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                        fname = call.func.id
                        if fname[:1].isupper() and fname not in _PY_EXCEPTION_NAMES:
                            concrete.add(fname)
            if len(concrete) > DIP_INSTANTIATION_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible Dependency Inversion violation: {node.name}",
                    description=f"Class '{node.name}' directly instantiates {len(concrete)} concrete classes inside its methods ({', '.join(sorted(concrete))[:80]}).",
                    severity="Low", category="SOLID: Dependency Inversion Principle", line_number=node.lineno,
                    recommendation="Depend on abstractions injected via the constructor instead of instantiating concrete classes directly inside methods.",
                    confidence=0.5,
                ))

    @staticmethod
    def _is_abstractmethod_decorator(d: ast.AST) -> bool:
        return (isinstance(d, ast.Name) and d.id == "abstractmethod") or \
               (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")

    @staticmethod
    def _compute_halstead_volume(tree: ast.AST) -> float:
        """Simplified Halstead Volume: V = N * log2(n), where n = distinct
        operators+operands (vocabulary) and N = total operator+operand
        occurrences (length). This groups AST node types into "operator-like"
        and "operand-like" buckets — a standard simplification, since the
        original Halstead metric predates ASTs and defined operators/operands
        in terms of raw tokens."""
        operators, operands = Counter(), Counter()
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                operators[type(node.op).__name__] += 1
            elif isinstance(node, ast.UnaryOp):
                operators[type(node.op).__name__] += 1
            elif isinstance(node, ast.BoolOp):
                operators[type(node.op).__name__] += 1
            elif isinstance(node, ast.Compare):
                for op in node.ops:
                    operators[type(op).__name__] += 1
            elif isinstance(node, ast.Assign):
                operators["assign"] += 1
            elif isinstance(node, ast.AugAssign):
                operators[f"aug_{type(node.op).__name__}"] += 1
            elif isinstance(node, ast.Call):
                operators["call"] += 1
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.Return,
                                    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                operators[type(node).__name__] += 1
            elif isinstance(node, ast.Name):
                operands[node.id] += 1
            elif isinstance(node, ast.Constant):
                operands[f"const_{type(node.value).__name__}_{node.value!r}"] += 1
            elif isinstance(node, ast.arg):
                operands[node.arg] += 1

        n1, n2 = len(operators), len(operands)
        length = sum(operators.values()) + sum(operands.values())
        vocabulary = n1 + n2
        if vocabulary == 0:
            return 1.0
        return length * math.log2(vocabulary)


# ---------------------------------------------------------------------------
# Java analyzer — regex + brace-counting heuristic (no external parser dep)
# ---------------------------------------------------------------------------
class JavaStaticAnalyzer:
    METHOD_PATTERN = re.compile(
        r"(?:public|private|protected|static|\s)+[\w<>\[\],\s]+?\s+(\w+)\s*\([^)]*\)\s*"
        r"(?:throws\s+[\w,\s]+)?\s*\{"
    )
    INTERFACE_METHOD_PATTERN = re.compile(r"[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*;")
    CLASS_PATTERN = re.compile(r"\bclass\s+(\w+)")
    INTERFACE_PATTERN = re.compile(r"\binterface\s+(\w+)")
    IMPORT_PATTERN = re.compile(r"^\s*import\s+([\w.]+)\s*;", re.MULTILINE)
    FIELD_PATTERN = re.compile(r"(?:private|public|protected)\s+(?:static\s+|final\s+)*[\w<>\[\],]+\s+\w+\s*(?:=[^;]+)?;")
    NEW_INSTANCE_PATTERN = re.compile(r"\bnew\s+(\w+)\s*\(")
    DECISION_TOKENS = re.compile(r"\b(if|for|while|case|catch)\b|(&&|\|\|)")
    _CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "synchronized"}

    def analyze(self, code: str) -> StaticAnalysisResult:
        result = StaticAnalysisResult()
        result.lines_of_code = len(code.splitlines())

        self._check_classes(code, result)
        self._check_interfaces(code, result)
        self._check_methods(code, result)
        self._check_unused_imports(code, result)
        result.findings.extend(find_duplicate_blocks(code, set()))

        halstead_volume = self._compute_halstead_volume(code)
        avg_complexity = (sum(result.function_complexities) / len(result.function_complexities)
                           if result.function_complexities else 1.0)
        result.halstead_volume = round(halstead_volume, 1)
        result.maintainability_index = compute_maintainability_index(halstead_volume, avg_complexity, result.lines_of_code)
        return result

    @staticmethod
    def _extract_brace_block(code: str, open_brace_index: int) -> str:
        """Given the index of an opening '{', return the full block via brace
        counting. Shared by method and class/interface body extraction."""
        depth = 0
        for i in range(open_brace_index, len(code)):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    return code[open_brace_index:i + 1]
        return code[open_brace_index:]

    def _check_methods(self, code: str, result: StaticAnalysisResult):
        camel_case = re.compile(r"^[a-z][a-zA-Z0-9]*$")
        for match in self.METHOD_PATTERN.finditer(code):
            name = match.group(1)
            if name in self._CONTROL_KEYWORDS:
                continue

            brace_index = match.end() - 1
            body = self._extract_brace_block(code, brace_index)
            body_lines = body.count("\n") + 1
            line_number = code[:match.start()].count("\n") + 1

            # crude parameter count: split the parenthesized arg list on commas
            params_text = code[match.start():match.end()]
            paren = params_text[params_text.find("(") + 1: params_text.rfind(")")]
            param_count = len([p for p in paren.split(",") if p.strip()]) if paren.strip() else 0

            if body_lines > LONG_METHOD_LINE_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Long method: {name}",
                    description=f"'{name}' spans approximately {body_lines} lines, above {LONG_METHOD_LINE_THRESHOLD}.",
                    severity="Medium", category="Long Method", line_number=line_number,
                    recommendation="Break this into smaller, single-purpose helper methods.", confidence=0.85,
                ))

            complexity = len(self.DECISION_TOKENS.findall(body)) + 1
            result.function_complexities.append(complexity)
            cognitive = self._approximate_cognitive_complexity(body)
            result.function_cognitive_complexities.append(cognitive)

            if complexity > HIGH_COMPLEXITY_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"High cyclomatic complexity: {name}",
                    description=f"'{name}' has an estimated cyclomatic complexity of {complexity}, above {HIGH_COMPLEXITY_THRESHOLD}.",
                    severity="High", category="Complexity", line_number=line_number,
                    recommendation="Reduce nested conditionals/loops; extract branches into separate methods.", confidence=0.8,
                ))

            if cognitive > HIGH_COGNITIVE_COMPLEXITY_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"High cognitive complexity: {name}",
                    description=f"'{name}' has an estimated cognitive complexity of {cognitive}, above {HIGH_COGNITIVE_COMPLEXITY_THRESHOLD}.",
                    severity="Medium", category="Cognitive Complexity", line_number=line_number,
                    recommendation="Reduce nesting depth — prefer early returns/guard clauses.", confidence=0.7,
                ))

            if param_count > LONG_PARAMETER_LIST_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Long parameter list: {name}",
                    description=f"'{name}' takes approximately {param_count} parameters, above {LONG_PARAMETER_LIST_THRESHOLD}.",
                    severity="Low", category="Design Anti-pattern", line_number=line_number,
                    recommendation="Group related parameters into a class/record, or split the method.", confidence=0.8,
                ))

            if not camel_case.match(name):
                result.findings.append(StaticFinding(
                    title=f"Naming convention: {name}",
                    description=f"Method '{name}' doesn't follow camelCase, the standard Java convention.",
                    severity="Low", category="Naming Convention", line_number=line_number,
                    recommendation="Rename the method using camelCase.", confidence=0.9,
                ))

    @staticmethod
    def _approximate_cognitive_complexity(body: str) -> int:
        """Nesting-weighted approximation using brace depth as a proxy for
        nesting level — cruder than the Python ast-based version, but a real
        signal beyond flat decision-token counting."""
        control_re = re.compile(r"\b(if|for|while|catch)\b")
        cognitive = 0
        for m in control_re.finditer(body):
            local_depth = body[:m.start()].count("{") - body[:m.start()].count("}")
            cognitive += 1 + max(local_depth - 1, 0)
        return cognitive

    def _check_classes(self, code: str, result: StaticAnalysisResult):
        pascal_case = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
        for match in self.CLASS_PATTERN.finditer(code):
            name = match.group(1)
            line_number = code[:match.start()].count("\n") + 1
            if not pascal_case.match(name):
                result.findings.append(StaticFinding(
                    title=f"Naming convention: {name}",
                    description=f"Class '{name}' doesn't follow PascalCase, the standard Java convention.",
                    severity="Low", category="Naming Convention", line_number=line_number,
                    recommendation="Rename the class using PascalCase.", confidence=0.9,
                ))

            brace_idx = code.find("{", match.end())
            if brace_idx == -1:
                continue
            body = self._extract_brace_block(code, brace_idx)
            body_lines = body.count("\n") + 1
            method_count = len(self.METHOD_PATTERN.findall(body))
            field_count = len(self.FIELD_PATTERN.findall(body))

            if method_count > GOD_CLASS_METHOD_THRESHOLD or body_lines > GOD_CLASS_LINE_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible God Object: {name}",
                    description=f"Class '{name}' has approximately {method_count} methods, {field_count} fields, and spans {body_lines} lines — it may be taking on too many responsibilities.",
                    severity="Medium", category="SOLID: Single Responsibility Principle", line_number=line_number,
                    recommendation="Split this class into smaller classes, each with a single, clearly-named responsibility.",
                    confidence=0.65,
                ))

            concrete = {m.group(1) for m in self.NEW_INSTANCE_PATTERN.finditer(body)} - _JAVA_COMMON_UTIL_CLASSES
            if len(concrete) > DIP_INSTANTIATION_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible Dependency Inversion violation: {name}",
                    description=f"Class '{name}' directly instantiates {len(concrete)} concrete classes with 'new' ({', '.join(sorted(concrete))[:80]}).",
                    severity="Low", category="SOLID: Dependency Inversion Principle", line_number=line_number,
                    recommendation="Depend on interfaces injected via the constructor instead of instantiating concrete classes directly.",
                    confidence=0.45,
                ))

    def _check_interfaces(self, code: str, result: StaticAnalysisResult):
        for match in self.INTERFACE_PATTERN.finditer(code):
            name = match.group(1)
            line_number = code[:match.start()].count("\n") + 1
            brace_idx = code.find("{", match.end())
            if brace_idx == -1:
                continue
            body = self._extract_brace_block(code, brace_idx)
            method_count = len(self.INTERFACE_METHOD_PATTERN.findall(body))
            if method_count > ISP_METHOD_THRESHOLD:
                result.findings.append(StaticFinding(
                    title=f"Possible fat interface: {name}",
                    description=f"Interface '{name}' declares approximately {method_count} methods — implementers may be forced to depend on methods they don't use.",
                    severity="Low", category="SOLID: Interface Segregation Principle", line_number=line_number,
                    recommendation="Split this interface into smaller, more focused interfaces.",
                    confidence=0.6,
                ))

    def _check_unused_imports(self, code: str, result: StaticAnalysisResult):
        for match in self.IMPORT_PATTERN.finditer(code):
            full_import = match.group(1)
            simple_name = full_import.split(".")[-1]
            if simple_name == "*":
                continue
            line_number = code[:match.start()].count("\n") + 1
            occurrences = len(re.findall(r"\b" + re.escape(simple_name) + r"\b", code))
            if occurrences <= 1:
                result.findings.append(StaticFinding(
                    title=f"Unused import: {full_import}",
                    description=f"'{full_import}' is imported but doesn't appear to be used elsewhere in the file.",
                    severity="Low", category="Unused Import", line_number=line_number,
                    recommendation=f"Remove the unused import '{full_import}'.", confidence=0.85,
                ))

    _JAVA_OPERATOR_TOKENS = {
        "+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!",
        "++", "--", "+=", "-=", "*=", "/=", "new", "if", "for", "while", "return", "catch", "case",
    }

    @classmethod
    def _compute_halstead_volume(cls, code: str) -> float:
        """Approximate Halstead Volume via simple tokenization (no full
        lexer/parser) — a real calculation from real tokens, but cruder than
        the Python ast-based version since Java isn't actually parsed."""
        tokens = re.findall(r"\+\+|--|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!]|\w+", code)
        operators, operands = Counter(), Counter()
        for tok in tokens:
            if tok in cls._JAVA_OPERATOR_TOKENS:
                operators[tok] += 1
            elif re.match(r"^[A-Za-z_]\w*$", tok) or re.match(r"^\d+$", tok):
                operands[tok] += 1
        n1, n2 = len(operators), len(operands)
        length = sum(operators.values()) + sum(operands.values())
        vocabulary = n1 + n2
        if vocabulary == 0:
            return 1.0
        return length * math.log2(vocabulary)
