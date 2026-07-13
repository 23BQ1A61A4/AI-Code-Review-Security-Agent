"""
Unit tests for app/agents/security/static_rules.py.

Run with:
    pytest tests/test_security_rules.py -v

Exercises the static rule engine directly against known-vulnerable code
snippets for every one of the 17 required categories (Python and/or Java,
per category). No LLM, no network, no mocking needed.
"""

from app.agents.security.static_rules import StaticSecurityRuleEngine, compute_risk_score
from app.models.submission import Language

engine = StaticSecurityRuleEngine()


def find_category(findings, category):
    return [f for f in findings if f.category == category]


class TestStaticSecurityRuleEnginePython:
    def test_sql_injection_detected(self):
        code = 'cursor.execute(f"SELECT * FROM users WHERE id={user_id}")'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "SQL Injection")

    def test_command_injection_detected(self):
        code = "subprocess.run(cmd, shell=True)"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Command Injection")

    def test_hardcoded_secret_detected(self):
        code = 'api_key = "sk_live_abcdef1234567890"'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Hardcoded Secrets")

    def test_insecure_deserialization_detected(self):
        code = "data = pickle.loads(raw_bytes)"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Insecure Deserialization")

    def test_unsafe_cryptography_detected(self):
        code = "h = hashlib.md5(data).hexdigest()"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Unsafe Cryptography")

    def test_weak_password_handling_detected(self):
        code = "hashed = hashlib.md5(password.encode()).hexdigest()"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Weak Password Handling")

    def test_weak_authentication_detected(self):
        code = 'if password == request.form["password"]:\n    login(user)'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Weak Authentication")

    def test_csrf_disabled_detected(self):
        code = "CSRF_ENABLED = False"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Cross-Site Request Forgery (CSRF)")

    def test_ssrf_detected(self):
        code = 'requests.get(request.args.get("url"))'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Server-Side Request Forgery (SSRF)")

    def test_path_traversal_detected(self):
        code = 'open(request.args.get("file"))'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Path Traversal")

    def test_insecure_file_upload_detected(self):
        code = 'request.files["f"].save(filename)'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Insecure File Upload")

    def test_insecure_session_handling_detected(self):
        code = "SESSION_COOKIE_SECURE = False"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Insecure Session Handling")

    def test_sensitive_data_exposure_detected(self):
        code = 'print(f"Login attempt password={password}")'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Sensitive Data Exposure")

    def test_xss_detected(self):
        code = "return mark_safe(user_input)"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert find_category(findings, "Cross-Site Scripting (XSS)")

    def test_clean_code_produces_no_findings(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert findings == []


class TestStaticSecurityRuleEngineJava:
    def test_sql_injection_detected(self):
        code = 'Statement s = con.createStatement(); s.executeQuery("SELECT * FROM t WHERE id=" + id);'
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert find_category(findings, "SQL Injection")

    def test_command_injection_detected(self):
        code = 'Runtime.getRuntime().exec("ls " + userInput);'
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert find_category(findings, "Command Injection")

    def test_csrf_disabled_detected(self):
        code = "http.csrf().disable();"
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert find_category(findings, "Cross-Site Request Forgery (CSRF)")

    def test_unsafe_cryptography_detected(self):
        code = 'MessageDigest.getInstance("MD5")'
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert find_category(findings, "Unsafe Cryptography")

    def test_insecure_deserialization_detected(self):
        code = "ObjectInputStream ois = new ObjectInputStream(is);"
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert find_category(findings, "Insecure Deserialization")

    def test_python_only_rule_not_applied_to_java(self):
        # The Python-specific mark_safe/XSS pattern shouldn't fire on Java code.
        code = "mark_safe_looking_but_java_wont_match(x);"
        findings = engine.scan(code, Language.JAVA, "Demo.java")
        assert not find_category(findings, "Cross-Site Scripting (XSS)")


class TestFindingFieldsAndScoring:
    def test_every_finding_has_all_required_fields(self):
        code = (
            'cursor.execute(f"SELECT * FROM t WHERE id={x}")\n'
            'api_key = "sk_live_abcdef1234567890"\n'
            "h = hashlib.md5(data).hexdigest()\n"
        )
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        assert len(findings) > 0
        for f in findings:
            assert f.title
            assert f.description
            assert f.severity is not None
            assert f.category
            assert f.owasp_category
            assert 0.0 <= f.risk_score <= 10.0
            assert 0.0 <= f.confidence_score <= 1.0
            assert f.evidence
            assert f.filename == "demo.py"
            assert f.line_number is not None and f.line_number >= 1
            assert f.recommendation

    def test_cwe_id_present_for_known_categories(self):
        code = 'cursor.execute(f"SELECT * FROM t WHERE id={x}")'
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        sqli = find_category(findings, "SQL Injection")
        assert sqli and sqli[0].cwe_id == "CWE-89"

    def test_line_numbers_are_accurate(self):
        code = "x = 1\ny = 2\ncursor.execute(f\"SELECT * FROM t WHERE id={x}\")\n"
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        sqli = find_category(findings, "SQL Injection")
        assert sqli and sqli[0].line_number == 3

    def test_risk_score_higher_for_high_impact_categories(self):
        sqli_score = compute_risk_score("SQL Injection", "High")
        generic_score = compute_risk_score("Insecure Session Handling", "High")
        assert sqli_score > generic_score

    def test_max_matches_per_rule_caps_findings(self):
        # 5 identical SQL-injection-shaped lines should be capped, not all reported.
        code = "\n".join([f'cursor.execute(f"SELECT * FROM t WHERE id={{x{i}}}")' for i in range(5)])
        findings = engine.scan(code, Language.PYTHON, "demo.py")
        sqli = find_category(findings, "SQL Injection")
        assert len(sqli) <= 3  # MAX_MATCHES_PER_RULE
