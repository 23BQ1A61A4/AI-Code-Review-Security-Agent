---
id: a09-security-logging-and-monitoring-failures
title: A09:2021 - Security Logging and Monitoring Failures
category: owasp_top_10
owasp_category: "A09:2021 - Security Logging and Monitoring Failures"
cwe_id: CWE-778
languages: [python, java]
tags: [logging, monitoring, incident-response]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A09:2021 - Security Logging and Monitoring Failures

Without adequate logging and monitoring, breaches go undetected far longer, giving attackers more time to
escalate and exfiltrate data.

## Common patterns
- Login failures, access control failures, and input validation failures aren't logged.
- Logs exist only locally and are lost/overwritten, or not monitored/alerted on.
- Logs don't contain enough context (who, what, when, from where) to support investigation.
- Sensitive data (passwords, tokens, full card numbers) is logged in plaintext.

## Prevention
- Log security-relevant events with enough context for forensic use, and centralize logs somewhere
  tamper-resistant.
- Alert on suspicious patterns (repeated failed logins, privilege escalation attempts) in near-real-time.
- Mask or omit sensitive fields before logging — never log credentials or full secrets.
- Have an incident response plan, and test it, before you need it.
