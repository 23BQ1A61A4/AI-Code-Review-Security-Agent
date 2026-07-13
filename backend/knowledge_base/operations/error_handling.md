---
id: error-handling
title: Secure Error Handling
category: operations
owasp_category: "A05:2021 - Security Misconfiguration"
cwe_id: CWE-209
languages: [python, java]
tags: [error-handling, information-disclosure]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Error Handling

## The core risk
Verbose error messages (stack traces, SQL errors, internal file paths, framework version banners) leak
information that helps an attacker understand and exploit the system — even though the error itself might
seem harmless.

## Practices
- Return generic, user-friendly error messages to clients ("Something went wrong, please try again") while
  logging full details (stack trace, request context) server-side for debugging.
- Disable debug/development mode in production (Flask's `debug=True`, Django's `DEBUG=True`, detailed
  Spring Boot error pages) — these are meant for local development only.
- Use a centralized error handler/middleware so every unhandled exception is caught and converted to a safe
  response consistently, rather than relying on each handler to do this correctly.
- Distinguish between expected errors (validation failures — safe to describe precisely to the client) and
  unexpected errors (safe only to acknowledge generically).
- Don't let error messages reveal whether a resource exists when the user isn't authorized to know that
  (e.g. return the same "not found" for both "doesn't exist" and "exists but you can't access it").
