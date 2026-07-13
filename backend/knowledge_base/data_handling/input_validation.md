---
id: input-validation
title: Input Validation
category: data_handling
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-20
languages: [python, java]
tags: [validation, sanitization]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Input Validation

Validating input at every trust boundary — before it's used — is a foundational control that reduces the
attack surface for injection, business-logic abuse, and data-integrity issues.

## Core practices
- Prefer allowlists (only permit known-good patterns/values) over denylists (blocking known-bad patterns),
  since denylists are easy to bypass with encoding tricks or patterns the author didn't anticipate.
- Validate type, length, format, and range — a numeric ID field should reject non-numeric input outright.
- Validate on the server even if the client already validates — client-side validation is a UX convenience,
  never a security control, since it can always be bypassed.
- Validate as early as possible (at the API boundary), using a schema/validation library (e.g. Pydantic in
  Python, Bean Validation in Java) rather than scattered manual checks.
- Remember validation is necessary but not sufficient — it complements, not replaces, output encoding and
  parameterized queries for injection defense.
