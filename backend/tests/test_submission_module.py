"""
Unit tests for the Milestone 1 audit fixes: basic syntax checking and
content-based language detection in the Submission Module.

Run with:
    pytest tests/test_submission_module.py -v
"""

import pytest

from app.models.submission import Language, SubmissionCreate
from app.services.submission_service import SubmissionService, SubmissionValidationError
from app.services.syntax_check import check_java_syntax_basic, check_python_syntax, detect_language_from_content


class TestPythonSyntaxCheck:
    def test_valid_code_passes(self):
        is_valid, error, line = check_python_syntax("def f():\n    return 1\n")
        assert is_valid and error is None

    def test_invalid_code_caught_with_line_number(self):
        is_valid, error, line = check_python_syntax("def f(:\n    pass\n")
        assert not is_valid
        assert line == 1


class TestJavaSyntaxCheckBasic:
    def test_balanced_code_passes(self):
        is_valid, error, line = check_java_syntax_basic("public class Foo {\n    void bar() { int x = 1; }\n}\n")
        assert is_valid

    def test_unclosed_brace_caught(self):
        is_valid, error, line = check_java_syntax_basic("public class Foo {\n    void bar() { int x = 1;\n")
        assert not is_valid
        assert "Unclosed" in error

    def test_braces_inside_strings_and_comments_ignored(self):
        code = 'String s = "{ not a real brace }"; // { also not real }'
        is_valid, error, line = check_java_syntax_basic(code)
        assert is_valid


class TestLanguageDetection:
    def test_detects_python_from_signals(self):
        assert detect_language_from_content("def add(a, b):\n    return a + b\n") == Language.PYTHON

    def test_detects_java_from_signals(self):
        code = "public class Demo {\n    public static void main(String[] a) { System.out.println(1); }\n}\n"
        assert detect_language_from_content(code) == Language.JAVA

    def test_ambiguous_snippet_returns_none_not_a_guess(self):
        assert detect_language_from_content("x = 1 + 1") is None


class TestSubmissionServiceIntegration:
    def setup_method(self):
        self.service = SubmissionService()

    def test_create_with_explicit_language_works(self):
        submission = self.service.create(SubmissionCreate(language=Language.PYTHON, code="x = 1"))
        assert submission.language == Language.PYTHON
        assert submission.language_auto_detected is False

    def test_create_without_language_auto_detects(self):
        submission = self.service.create(SubmissionCreate(code="def f():\n    return 1\n"))
        assert submission.language == Language.PYTHON
        assert submission.language_auto_detected is True

    def test_create_without_language_and_no_signal_raises(self):
        with pytest.raises(SubmissionValidationError):
            self.service.create(SubmissionCreate(code="x = 1"))

    def test_syntax_error_surfaced_on_submission(self):
        submission = self.service.create(SubmissionCreate(language=Language.PYTHON, code="def f(:\n  pass"))
        assert submission.syntax_valid is False
        assert submission.syntax_error_line == 1

    def test_valid_syntax_surfaced_on_submission(self):
        submission = self.service.create(SubmissionCreate(language=Language.PYTHON, code="def f():\n    return 1\n"))
        assert submission.syntax_valid is True
        assert submission.syntax_error is None

    def test_file_upload_syntax_check(self):
        submission = self.service.create_from_file("Demo.java", "public class Demo {\n    void x() {\n")
        assert submission.language == Language.JAVA
        assert submission.syntax_valid is False
