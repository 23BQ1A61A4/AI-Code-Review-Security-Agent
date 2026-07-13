---
id: logging
title: Secure Logging
category: operations
owasp_category: "A09:2021 - Security Logging and Monitoring Failures"
cwe_id: CWE-532
languages: [python, java]
tags: [logging, monitoring]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Logging

## What to log
- Authentication events (successful and failed logins, password changes, MFA events).
- Authorization failures (access denied events).
- Input validation failures (possible probing/attack attempts).
- Administrative actions (role changes, configuration changes, data exports).

## What NOT to log
- Passwords, full session tokens, full credit card numbers, or other raw secrets — mask or omit them.
- Full request/response bodies for endpoints handling sensitive data, unless explicitly redacted first.

## Practices
- Include enough context per log entry to support investigation: timestamp, actor (user/service), action,
  outcome, and relevant identifiers — without including the sensitive payload itself.
- Centralize logs somewhere append-only/tamper-resistant, separate from the systems generating them, so an
  attacker who compromises a host can't simply delete the evidence.
- Set up alerting on suspicious patterns (repeated failed logins, privilege escalation attempts, unusual
  data access volume) rather than only reviewing logs after an incident is already suspected.
- Apply a retention policy that satisfies both compliance requirements and storage practicality.
