"""
Static Security Rule Engine — Module 3.

Regex-based detection for common, mechanically-recognizable vulnerability
patterns. This is deliberately positioned as ONE scanner among several (see
scanner_base.py) — it implements SecurityScanner exactly like a future real
Bandit/Semgrep integration would.

Honest coverage note: some of the 17 required categories are genuinely hard
to detect reliably with regex alone (e.g. "missing" input validation, or
Broken Access Control, which requires tracing whether an auth check exists
*somewhere* in a call chain). For those, this engine provides a narrow,
low-confidence heuristic where one exists, and leans on the LLM semantic
pass (see security_vulnerability_agent.py) for the rest — the same
static-for-mechanical / LLM-for-semantic split used in the Code Analysis
Agent (Module 2). Every category below is annotated with how confident its
static rule actually is.
"""

import re
from dataclasses import dataclass
from typing import List, Pattern

from app.agents.security.scanner_base import SecurityScanner
from app.models.security import SecurityFinding, SecurityFindingSource
from app.models.submission import Language

MAX_MATCHES_PER_RULE = 3  # cap so one noisy pattern doesn't flood the findings list

# ---------------------------------------------------------------------------
# OWASP / CWE mapping — one source of truth for all 17 categories
# ---------------------------------------------------------------------------
CATEGORY_METADATA = {
    "SQL Injection":                       {"owasp": "A03:2021 - Injection", "cwe": "CWE-89"},
    "Cross-Site Scripting (XSS)":           {"owasp": "A03:2021 - Injection", "cwe": "CWE-79"},
    "Cross-Site Request Forgery (CSRF)":    {"owasp": "A01:2021 - Broken Access Control", "cwe": "CWE-352"},
    "Command Injection":                   {"owasp": "A03:2021 - Injection", "cwe": "CWE-78"},
    "Path Traversal":                      {"owasp": "A01:2021 - Broken Access Control", "cwe": "CWE-22"},
    "Server-Side Request Forgery (SSRF)":  {"owasp": "A10:2021 - Server-Side Request Forgery", "cwe": "CWE-918"},
    "Hardcoded Secrets":                   {"owasp": "A02:2021 - Cryptographic Failures", "cwe": "CWE-798"},
    "Weak Authentication":                 {"owasp": "A07:2021 - Identification and Authentication Failures", "cwe": "CWE-287"},
    "Weak Password Handling":              {"owasp": "A02:2021 - Cryptographic Failures", "cwe": "CWE-916"},
    "Broken Access Control":               {"owasp": "A01:2021 - Broken Access Control", "cwe": "CWE-284"},
    "Insecure File Upload":                {"owasp": "A04:2021 - Insecure Design", "cwe": "CWE-434"},
    "Insecure Deserialization":            {"owasp": "A08:2021 - Software and Data Integrity Failures", "cwe": "CWE-502"},
    "Sensitive Data Exposure":             {"owasp": "A02:2021 - Cryptographic Failures", "cwe": "CWE-200"},
    "Unsafe Cryptography":                 {"owasp": "A02:2021 - Cryptographic Failures", "cwe": "CWE-327"},
    "Missing Input Validation":            {"owasp": "A03:2021 - Injection", "cwe": "CWE-20"},
    "Missing Output Encoding":             {"owasp": "A03:2021 - Injection", "cwe": "CWE-116"},
    "Insecure Session Handling":           {"owasp": "A07:2021 - Identification and Authentication Failures", "cwe": "CWE-384"},
}

# ---------------------------------------------------------------------------
# CVSS-style risk scoring: base value per severity, bumped for categories
# whose typical real-world impact (RCE, data breach) runs higher than their
# severity label alone suggests.
# ---------------------------------------------------------------------------
_SEVERITY_BASE_RISK = {"Low": 3.0, "Medium": 5.5, "High": 7.5, "Critical": 9.3}
_HIGH_IMPACT_CATEGORIES = {
    "SQL Injection", "Command Injection", "Insecure Deserialization",
    "Server-Side Request Forgery (SSRF)", "Broken Access Control",
}


def compute_risk_score(category: str, severity: str) -> float:
    base = _SEVERITY_BASE_RISK.get(severity, 5.0)
    if category in _HIGH_IMPACT_CATEGORIES:
        base = min(10.0, base + 0.6)
    return round(base, 1)


@dataclass
class SecurityRule:
    category: str
    language: str  # "python" | "java" | "both"
    pattern: Pattern
    severity: str  # "Low" | "Medium" | "High" | "Critical"
    description: str
    recommendation: str
    confidence: float  # static confidence for THIS specific regex signal


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------
RULES: List[SecurityRule] = [
    # --- SQL Injection --- (confidence: fairly reliable — string building into execute())
    SecurityRule(
        "SQL Injection", "python",
        re.compile(r"""(?:execute|executemany)\s*\(\s*(?:f["']|["'][^"']*["']\s*[%+]|.*?\.format\()"""),
        "Critical", "User-controlled or formatted string passed directly into a SQL execute call.",
        "Use parameterized queries: cursor.execute(query, params) with placeholders, never string formatting.",
        0.75,
    ),
    SecurityRule(
        "SQL Injection", "java",
        re.compile(r"""(?:createStatement\(\)|Statement\s+\w+\s*=).*?(?:executeQuery|executeUpdate)\s*\(\s*["']?[^"')]*["']?\s*\+"""),
        "Critical", "SQL query string built via concatenation and executed via Statement.",
        "Use PreparedStatement with parameterized placeholders (?) instead of Statement with string concatenation.",
        0.7,
    ),

    # --- Command Injection --- (confidence: high — these calls are rarely used safely with dynamic input)
    SecurityRule(
        "Command Injection", "python",
        re.compile(r"\bos\.system\s*\(|subprocess\.(?:call|run|Popen)\([^)]*shell\s*=\s*True|os\.popen\s*\("),
        "Critical", "Shell command execution with shell=True or os.system/os.popen — vulnerable if any part of the command includes user input.",
        "Avoid shell=True; pass arguments as a list to subprocess.run() and never build the command string via concatenation.",
        0.7,
    ),
    SecurityRule(
        "Command Injection", "java",
        re.compile(r"Runtime\.getRuntime\(\)\.exec\s*\(\s*[^)]*\+|ProcessBuilder\s*\([^)]*\+"),
        "Critical", "OS command built via string concatenation and executed via Runtime.exec/ProcessBuilder.",
        "Pass command and arguments as separate list elements to ProcessBuilder; never concatenate user input into a shell command string.",
        0.7,
    ),

    # --- Hardcoded Secrets --- (confidence: moderate — placeholders like "changeme" still match, documented limitation)
    SecurityRule(
        "Hardcoded Secrets", "both",
        re.compile(r"""(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd|private[_-]?key)\b\s*[:=]\s*["'][A-Za-z0-9+/=_\-]{8,}["']"""),
        "High", "A credential-like value is assigned directly as a string literal.",
        "Load secrets from environment variables or a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault) — never commit them as literals.",
        0.6,
    ),

    # --- Insecure Deserialization --- (confidence: high — these APIs are inherently dangerous on untrusted input)
    SecurityRule(
        "Insecure Deserialization", "python",
        re.compile(r"pickle\.loads?\s*\(|yaml\.load\s*\((?!.*SafeLoader)|marshal\.loads?\s*\("),
        "High", "Deserializing data with an API that can execute arbitrary code if the input is untrusted.",
        "Use json for untrusted data; if pickle/yaml is required, use yaml.safe_load() and never unpickle data from an untrusted source.",
        0.75,
    ),
    SecurityRule(
        "Insecure Deserialization", "java",
        re.compile(r"new\s+ObjectInputStream\s*\(|readObject\s*\(\s*\)"),
        "High", "Native Java deserialization (ObjectInputStream) can execute arbitrary code from a crafted stream.",
        "Avoid native deserialization of untrusted input; if required, use an ObjectInputFilter to restrict allowed classes.",
        0.6,
    ),

    # --- Unsafe Cryptography --- (confidence: high — these algorithms are unambiguously weak)
    SecurityRule(
        "Unsafe Cryptography", "python",
        re.compile(r"\bDES\.new\s*\(|MODE_ECB|hashlib\.md5\s*\(|hashlib\.sha1\s*\("),
        "Medium", "A cryptographically weak algorithm or mode (DES, ECB, MD5, SHA1) is used.",
        "Use AES-GCM for encryption and SHA-256 or better for hashing; avoid ECB mode entirely.",
        0.7,
    ),
    SecurityRule(
        "Unsafe Cryptography", "java",
        re.compile(r"""Cipher\.getInstance\s*\(\s*["']DES|["']AES/ECB|MessageDigest\.getInstance\s*\(\s*["'](?:MD5|SHA-?1)["']"""),
        "Medium", "A cryptographically weak algorithm or mode (DES, ECB, MD5, SHA-1) is used.",
        "Use AES/GCM/NoPadding for encryption and SHA-256 or better for hashing; avoid ECB mode entirely.",
        0.7,
    ),

    # --- Weak Password Handling --- (confidence: high when paired with 'password' context)
    SecurityRule(
        "Weak Password Handling", "python",
        re.compile(r"(?:hashlib\.md5|hashlib\.sha1)\s*\([^)]*password"),
        "High", "A password is hashed with MD5/SHA1 — both are fast to brute-force and unsuitable for passwords.",
        "Use bcrypt, scrypt, or Argon2 for password hashing, never a fast general-purpose hash.",
        0.7,
    ),
    SecurityRule(
        "Weak Password Handling", "java",
        re.compile(r"""MessageDigest\.getInstance\s*\(\s*["'](?:MD5|SHA-?1)["']\)[^;]*password"""),
        "High", "A password appears to be hashed with MD5/SHA-1 — both are fast to brute-force and unsuitable for passwords.",
        "Use BCrypt (Spring Security's BCryptPasswordEncoder) or Argon2 for password hashing.",
        0.6,
    ),

    # --- Weak Authentication --- (confidence: moderate — plaintext password comparison heuristic)
    SecurityRule(
        "Weak Authentication", "python",
        re.compile(r"""if\s+.*password.*==\s*(?:request\.|input\(|["'])"""),
        "High", "Password appears to be compared directly with '==' rather than via a constant-time hash comparison.",
        "Compare hashed passwords using a library's constant-time verify function (e.g. bcrypt.checkpw), never plaintext '=='.",
        0.5,
    ),
    SecurityRule(
        "Weak Authentication", "java",
        re.compile(r"""\.equals\s*\(\s*password\s*\)|password\.equals\s*\("""),
        "Medium", "Password appears to be compared with .equals() rather than via a constant-time hash comparison.",
        "Compare hashed passwords using BCrypt.checkpw() or an equivalent constant-time comparison, never plain .equals().",
        0.45,
    ),

    # --- SSRF --- (confidence: moderate — user input reaching an outbound HTTP call)
    SecurityRule(
        "Server-Side Request Forgery (SSRF)", "python",
        re.compile(r"requests\.(?:get|post|put|delete)\s*\([^)]*request\.(?:args|form|GET|POST|json)"),
        "High", "An outbound HTTP request URL appears to be built directly from incoming request data.",
        "Validate/allowlist destination hosts before making outbound requests on behalf of user input.",
        0.55,
    ),
    SecurityRule(
        "Server-Side Request Forgery (SSRF)", "java",
        re.compile(r"new\s+URL\s*\(\s*(?:request\.getParameter|req\.getParameter)"),
        "High", "A URL is constructed directly from an HTTP request parameter before being fetched.",
        "Validate/allowlist destination hosts before making outbound requests on behalf of user input.",
        0.5,
    ),

    # --- Path Traversal --- (confidence: moderate — file op combined with unsanitized user input)
    SecurityRule(
        "Path Traversal", "python",
        re.compile(r"open\s*\(\s*[^)]*request\.(?:args|form|GET|POST)|send_file\s*\(\s*[^)]*request\.(?:args|form)"),
        "High", "A file path passed to open()/send_file() appears to come directly from request data.",
        "Validate the requested filename against an allowlist and resolve it within a fixed base directory (reject '..').",
        0.55,
    ),
    SecurityRule(
        "Path Traversal", "java",
        re.compile(r"new\s+File\s*\(\s*(?:request\.getParameter|req\.getParameter)"),
        "High", "A file path is constructed directly from an HTTP request parameter.",
        "Validate the requested filename against an allowlist and resolve it within a fixed base directory (reject '..').",
        0.5,
    ),

    # --- Insecure File Upload --- (confidence: low-moderate — absence-based heuristic)
    SecurityRule(
        "Insecure File Upload", "python",
        re.compile(r"request\.files\[[^\]]+\]\.save\s*\("),
        "Medium", "An uploaded file is saved without an evident filename-sanitization or extension check nearby.",
        "Sanitize the filename (e.g. werkzeug.utils.secure_filename) and validate the file extension/content type before saving.",
        0.4,
    ),
    SecurityRule(
        "Insecure File Upload", "java",
        re.compile(r"\.transferTo\s*\(\s*new\s+File\s*\("),
        "Medium", "An uploaded MultipartFile is saved without an evident filename-sanitization or extension check nearby.",
        "Sanitize/validate the filename and extension, and store uploads outside the web root with a generated name.",
        0.4,
    ),

    # --- CSRF --- (confidence: high — explicit disabling of protection)
    SecurityRule(
        "Cross-Site Request Forgery (CSRF)", "python",
        re.compile(r"csrf_exempt|CSRF_ENABLED\s*=\s*False|WTF_CSRF_ENABLED\s*=\s*False"),
        "High", "CSRF protection appears to be explicitly disabled or exempted.",
        "Remove the exemption; enable CSRF tokens on all state-changing (POST/PUT/DELETE) endpoints.",
        0.8,
    ),
    SecurityRule(
        "Cross-Site Request Forgery (CSRF)", "java",
        re.compile(r"\.csrf\s*\(\s*\)\s*\.disable\s*\("),
        "High", "Spring Security CSRF protection is explicitly disabled.",
        "Remove .csrf().disable() unless the endpoint is a pure API secured by another mechanism (e.g. token auth) — document why if so.",
        0.8,
    ),

    # --- Insecure Session Handling --- (confidence: high — explicit insecure cookie flags)
    SecurityRule(
        "Insecure Session Handling", "python",
        re.compile(r"SESSION_COOKIE_SECURE\s*=\s*False|SESSION_COOKIE_HTTPONLY\s*=\s*False"),
        "Medium", "Session cookie Secure/HttpOnly flag is explicitly disabled.",
        "Set SESSION_COOKIE_SECURE=True and SESSION_COOKIE_HTTPONLY=True in production.",
        0.75,
    ),
    SecurityRule(
        "Insecure Session Handling", "java",
        re.compile(r"\.cookieSecure\s*\(\s*false\s*\)|setHttpOnly\s*\(\s*false\s*\)"),
        "Medium", "Session cookie Secure/HttpOnly flag is explicitly disabled.",
        "Enable Secure and HttpOnly flags on session cookies in production.",
        0.7,
    ),

    # --- Sensitive Data Exposure --- (confidence: moderate — logging secrets)
    SecurityRule(
        "Sensitive Data Exposure", "both",
        re.compile(r"""(?:print|log(?:ger)?\.\w+|System\.out\.println|System\.err\.println)\s*\([^)]*password"""),
        "Medium", "A value that appears to be a password is being logged or printed.",
        "Never log credentials; mask or omit sensitive fields before logging.",
        0.55,
    ),

    # --- Cross-Site Scripting (XSS) --- (confidence: low-moderate — narrow patterns only)
    SecurityRule(
        "Cross-Site Scripting (XSS)", "python",
        re.compile(r"mark_safe\s*\(|render_template_string\s*\([^)]*\+|\|\s*safe\b"),
        "High", "Output is marked safe / rendered from a concatenated template string, bypassing autoescaping.",
        "Avoid mark_safe/|safe on anything derived from user input; let the templating engine autoescape by default.",
        0.5,
    ),
]


class StaticSecurityRuleEngine(SecurityScanner):
    source_name = "static_rules"

    def scan(self, code: str, language: Language, filename: str) -> List[SecurityFinding]:
        lang_key = "python" if language == Language.PYTHON else "java"
        findings: List[SecurityFinding] = []

        for rule in RULES:
            if rule.language not in (lang_key, "both"):
                continue
            matches = list(rule.pattern.finditer(code))[:MAX_MATCHES_PER_RULE]
            for match in matches:
                line_number = code[:match.start()].count("\n") + 1
                evidence = code[match.start():match.end()].strip()[:200] or match.group(0)[:200]
                meta = CATEGORY_METADATA.get(rule.category, {})

                findings.append(SecurityFinding(
                    title=f"{rule.category} risk detected",
                    description=rule.description,
                    severity=rule.severity,
                    category=rule.category,
                    owasp_category=meta.get("owasp", "Unclassified"),
                    cwe_id=meta.get("cwe"),
                    risk_score=compute_risk_score(rule.category, rule.severity),
                    confidence_score=rule.confidence,
                    evidence=evidence,
                    filename=filename,
                    line_number=line_number,
                    recommendation=rule.recommendation,
                    source=SecurityFindingSource.STATIC_RULES,
                ))
        return findings
