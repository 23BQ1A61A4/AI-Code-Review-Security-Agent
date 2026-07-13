---
id: a03-injection
title: A03:2021 - Injection
category: owasp_top_10
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-74
languages: [python, java]
tags: [injection, sql-injection, xss, command-injection]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A03:2021 - Injection

Injection flaws occur when untrusted data is sent to an interpreter (SQL, OS shell, LDAP, etc.) as part of a
command or query, and the interpreter is tricked into executing unintended commands. This category now
includes Cross-Site Scripting (XSS), previously its own category.

## Common patterns
- Building SQL queries via string concatenation/formatting with user input (SQL Injection).
- Rendering user input into HTML without escaping (XSS).
- Passing user input to a shell command (OS Command Injection).
- Building LDAP, XPath, or NoSQL queries via string concatenation.

## Prevention
- Use parameterized queries / prepared statements for all database access — never string-build SQL.
- Use an ORM's query builder correctly (avoid its "raw SQL" escape hatches with untrusted input).
- Escape output based on context (HTML body, attribute, JS, URL) — rely on your templating engine's
  autoescaping rather than manually concatenating markup.
- Avoid shell invocation entirely where possible; if unavoidable, pass arguments as a list, never a
  concatenated string, and never with `shell=True`.
- Validate input against an allowlist wherever the expected format is known (e.g. a numeric ID).
