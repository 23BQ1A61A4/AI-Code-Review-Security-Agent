# Milestone 4 — Detection & Report Validation (Real Pipeline Run)

## sample1_simple.py (Python)
**Expected characteristic:** Basic code-quality issue (mutable default argument)

- Language detected: **Python** (auto-detected: False)
- Syntax valid: **True**
- Engines used: code analysis = `ast+radon`, security scan = `regex-fallback`

**Bugs detected:**
  - [Medium] Mutable default argument

**Security issues detected:**
  - None

**Code smells detected:**
  - No significant code smells detected.

- PR verdict: **Approve with suggestions**
- Metrics: {'security_score': 100, 'quality_score': 92, 'maintainability_score': 96, 'complexity': 'Low'}
- Fixes generated (pipeline `fixes` list): 1
- Report findings count (per-finding remediation, report module): 1
- Report severity breakdown: {'Critical': 0, 'High': 0, 'Medium': 1, 'Low': 0, 'Info': 0}
- PDF report: `validation\report_sample1_simple_py.pdf` (4724 bytes, valid PDF header: True)

---

## sample2_vulnerable.py (Python)
**Expected characteristic:** Realistic security vulnerabilities (SQLi, hardcoded secret, command injection, weak crypto, bare except)

- Language detected: **Python** (auto-detected: False)
- Syntax valid: **True**
- Engines used: code analysis = `ast+radon`, security scan = `regex-fallback`

**Bugs detected:**
  - [Medium] Bare except clause

**Security issues detected:**
  - [Critical] Possible SQL Injection (string-built query) (A03: Injection)
  - [Critical] Command Injection (A03: Injection)
  - [Medium] Weak cryptographic algorithm (A02: Cryptographic Failures)

**Code smells detected:**
  - No significant code smells detected.

- PR verdict: **Block**
- Metrics: {'security_score': 32, 'quality_score': 92, 'maintainability_score': 88, 'complexity': 'Low'}
- Fixes generated (pipeline `fixes` list): 4
- Report findings count (per-finding remediation, report module): 4
- Report severity breakdown: {'Critical': 2, 'High': 0, 'Medium': 2, 'Low': 0, 'Info': 0}
- PDF report: `validation\report_sample2_vulnerable_py.pdf` (7237 bytes, valid PDF header: True)

---

## sample3_sample.java (Java)
**Expected characteristic:** Java code-quality/security issues (SQLi, hardcoded secret, empty catch, too many params)

- Language detected: **Java** (auto-detected: False)
- Syntax valid: **True**
- Engines used: code analysis = `javalang`, security scan = `regex-fallback`

**Bugs detected:**
  - [Low] Method with too many parameters

**Security issues detected:**
  - [Critical] Possible SQL Injection (string-built query) (A03: Injection)
  - [Critical] Command Injection (A03: Injection)

**Code smells detected:**
  - Empty catch block — exception silently swallowed (1x)

- PR verdict: **Block**
- Metrics: {'security_score': 40, 'quality_score': 93, 'maintainability_score': 66, 'complexity': 'High'}
- Fixes generated (pipeline `fixes` list): 3
- Report findings count (per-finding remediation, report module): 3
- Report severity breakdown: {'Critical': 2, 'High': 0, 'Medium': 0, 'Low': 1, 'Info': 0}
- PDF report: `validation\report_sample3_sample_java.pdf` (6351 bytes, valid PDF header: True)

---
