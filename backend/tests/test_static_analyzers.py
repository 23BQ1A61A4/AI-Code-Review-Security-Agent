"""
Unit tests for app/agents/static_analyzers.py.

Run with:
    pytest tests/test_static_analyzers.py -v

These tests exercise the deterministic (non-LLM) analysis layer directly,
so they need no API key and no network access.
"""

from app.agents.static_analyzers import (
    JavaStaticAnalyzer,
    PythonStaticAnalyzer,
    compute_maintainability_index,
    find_duplicate_blocks,
)


def categories(findings):
    return [f.category for f in findings]


def titles(findings):
    return [f.title for f in findings]


# ---------------------------------------------------------------------------
# Python analyzer
# ---------------------------------------------------------------------------
class TestPythonStaticAnalyzer:
    def setup_method(self):
        self.analyzer = PythonStaticAnalyzer()

    def test_long_method_detected(self):
        body = "\n".join(f"    x{i} = {i}" for i in range(45))
        code = f"def long_function():\n{body}\n    return x0"
        result = self.analyzer.analyze(code)
        assert "Long Method" in categories(result.findings)

    def test_naming_convention_detected_for_function_and_class(self):
        code = "def BadlyNamedFunction():\n    pass\n\nclass badClassName:\n    pass\n"
        result = self.analyzer.analyze(code)
        assert "Naming Convention" in categories(result.findings)
        # both the function and the class should be flagged
        naming_findings = [f for f in result.findings if f.category == "Naming Convention"]
        assert len(naming_findings) == 2

    def test_unused_import_detected(self):
        code = "import os\nimport sys\n\ndef f():\n    return sys.path\n"
        result = self.analyzer.analyze(code)
        unused_imports = [f for f in result.findings if f.category == "Unused Import"]
        assert any("os" in f.title for f in unused_imports)
        assert not any("sys" in f.title for f in unused_imports)  # sys IS used

    def test_dunder_all_exempts_import_from_unused_check(self):
        code = "import os\n\n__all__ = ['os']\n"
        result = self.analyzer.analyze(code)
        assert not any(f.category == "Unused Import" for f in result.findings)

    def test_unused_variable_detected(self):
        code = "def f():\n    unused_value = 42\n    return 1\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "Unused Variable" and "unused_value" in f.title for f in result.findings)

    def test_augmented_assignment_not_flagged_as_unused(self):
        # `total += x` reads `total` before writing it, so it must NOT be
        # flagged as an unused variable even though its only Store context
        # would otherwise look like an unread assignment.
        code = "def f(items):\n    total = 0\n    for x in items:\n        total += x\n    return total\n"
        result = self.analyzer.analyze(code)
        assert not any(f.category == "Unused Variable" and "total" in f.title for f in result.findings)

    def test_high_cyclomatic_complexity_detected(self):
        nested = "\n".join(
            f"{'    ' * (i + 1)}if x{i} > 0:" for i in range(11)
        )
        code = f"def deeply_nested(x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10):\n{nested}\n{'    ' * 12}pass\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "Complexity" for f in result.findings)
        assert max(result.function_complexities) > 10

    def test_cognitive_complexity_higher_for_nested_than_flat(self):
        flat = "def flat(a,b,c):\n    if a: pass\n    if b: pass\n    if c: pass\n    return 1\n"
        nested = "def nested(a,b,c):\n    if a:\n        if b:\n            if c:\n                pass\n    return 1\n"
        flat_result = self.analyzer.analyze(flat)
        nested_result = self.analyzer.analyze(nested)
        # Same number of `if`s (cyclomatic complexity similar), but nesting
        # should make cognitive complexity higher for the nested version.
        assert nested_result.function_cognitive_complexities[0] > flat_result.function_cognitive_complexities[0]

    def test_magic_number_detected_in_condition_not_in_assignment(self):
        code = "def f(x):\n    limit = 5\n    if x > 47:\n        return True\n    return False\n"
        result = self.analyzer.analyze(code)
        magic_findings = [f for f in result.findings if "Magic number" in f.title]
        assert any("47" in f.title for f in magic_findings)
        # `limit = 5` is a plain assignment, not a condition/call argument —
        # it should NOT be flagged as a magic number.
        assert not any("The literal 5 " in f.description for f in magic_findings)

    def test_long_parameter_list_detected(self):
        code = "def f(a, b, c, d, e, f, g):\n    return a\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "Design Anti-pattern" and "parameter" in f.title.lower() for f in result.findings)

    def test_god_object_srp_heuristic(self):
        methods = "\n".join(f"    def method_{i}(self): pass" for i in range(20))
        code = f"class Everything:\n{methods}\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "SOLID: Single Responsibility Principle" for f in result.findings)

    def test_dip_heuristic_flags_many_concrete_instantiations(self):
        code = (
            "class Service:\n"
            "    def run(self):\n"
            "        a = Database()\n"
            "        b = Cache()\n"
            "        c = Logger()\n"
            "        d = Mailer()\n"
            "        return a\n"
        )
        result = self.analyzer.analyze(code)
        assert any(f.category == "SOLID: Dependency Inversion Principle" for f in result.findings)

    def test_isp_heuristic_flags_fat_abstract_interface(self):
        methods = "\n".join(f"    @abstractmethod\n    def m{i}(self): pass" for i in range(8))
        code = f"from abc import ABC, abstractmethod\n\nclass BigInterface(ABC):\n{methods}\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "SOLID: Interface Segregation Principle" for f in result.findings)

    def test_duplicate_exact_blocks_detected(self):
        block = "    print(1)\n    print(2)\n    print(3)\n    print(4)\n"
        code = f"def a():\n{block}\ndef b():\n{block}\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "Duplicate Code" and f.confidence >= 0.85 for f in result.findings)

    def test_duplicate_renamed_variable_blocks_detected(self):
        # Same structure, different variable names — should be caught by the
        # normalized (Type-2) duplicate check, not the exact-match check.
        block_a = "    total_x = 0\n    total_x = total_x + 1\n    total_x = total_x + 2\n    return total_x\n"
        block_b = "    total_y = 0\n    total_y = total_y + 1\n    total_y = total_y + 2\n    return total_y\n"
        code = f"def a():\n{block_a}\ndef b():\n{block_b}\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "Duplicate Code" for f in result.findings)

    def test_syntax_error_reported_gracefully(self):
        result = self.analyzer.analyze("def f(:\n    pass\n")
        assert len(result.findings) == 1
        assert result.findings[0].severity == "High"
        assert result.findings[0].confidence == 1.0

    def test_maintainability_index_and_halstead_computed(self):
        code = "def add(a, b):\n    return a + b\n"
        result = self.analyzer.analyze(code)
        assert result.halstead_volume is not None and result.halstead_volume > 0
        assert result.maintainability_index is not None
        assert 0 <= result.maintainability_index <= 100

    def test_every_finding_has_required_fields(self):
        code = (
            "import os\n"
            "def BadName(a,b,c,d,e,f,g):\n"
            "    unused = 1\n"
            "    if a > 999:\n"
            "        return a\n"
            "    return b\n"
        )
        result = self.analyzer.analyze(code)
        assert len(result.findings) > 0
        for f in result.findings:
            assert f.title
            assert f.description
            assert f.severity in ("Low", "Medium", "High", "Critical")
            assert f.category
            assert f.recommendation
            assert 0.0 <= f.confidence <= 1.0


# ---------------------------------------------------------------------------
# Java analyzer
# ---------------------------------------------------------------------------
class TestJavaStaticAnalyzer:
    def setup_method(self):
        self.analyzer = JavaStaticAnalyzer()

    def test_naming_convention_detected(self):
        code = "public class badClassName {\n    public void BadMethodName() {\n        int x = 1;\n    }\n}\n"
        result = self.analyzer.analyze(code)
        assert "Naming Convention" in categories(result.findings)

    def test_unused_import_detected(self):
        code = (
            "import java.util.List;\n"
            "import java.io.IOException;\n"
            "public class Demo {\n"
            "    public void run() {\n"
            "        List x = null;\n"
            "    }\n"
            "}\n"
        )
        result = self.analyzer.analyze(code)
        unused = [f for f in result.findings if f.category == "Unused Import"]
        assert any("IOException" in f.title for f in unused)
        assert not any("List" in f.title for f in unused)

    def test_long_parameter_list_detected(self):
        code = (
            "public class Demo {\n"
            "    public void run(int a, int b, int c, int d, int e, int f, int g) {\n"
            "        int x = 1;\n"
            "    }\n"
            "}\n"
        )
        result = self.analyzer.analyze(code)
        assert any(f.category == "Design Anti-pattern" for f in result.findings)

    def test_fat_interface_detected(self):
        methods = "\n".join(f"    void m{i}();" for i in range(8))
        code = f"public interface BigInterface {{\n{methods}\n}}\n"
        result = self.analyzer.analyze(code)
        assert any(f.category == "SOLID: Interface Segregation Principle" for f in result.findings)

    def test_maintainability_index_computed(self):
        code = "public class Demo {\n    public int add(int a, int b) {\n        return a + b;\n    }\n}\n"
        result = self.analyzer.analyze(code)
        assert result.maintainability_index is not None
        assert 0 <= result.maintainability_index <= 100


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------
def test_compute_maintainability_index_bounds():
    assert compute_maintainability_index(halstead_volume=1, avg_cyclomatic=1, loc=1) <= 100
    assert compute_maintainability_index(halstead_volume=100000, avg_cyclomatic=50, loc=5000) >= 0


def test_find_duplicate_blocks_ignores_trivial_blank_blocks():
    code = "\n\n\n\n\n\n\n\n"
    assert find_duplicate_blocks(code, keywords=set()) == []
