---
id: command-injection
title: OS Command Injection
category: vulnerability
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-78
languages: [python, java]
tags: [injection, os]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# OS Command Injection

Occurs when an application passes untrusted input to a system shell, letting an attacker inject additional
commands or shell metacharacters (`;`, `|`, `&&`, backticks) to run arbitrary commands on the host.

## Example (vulnerable)
Python: `os.system(f"ping {host}")` — an attacker supplying `host = "8.8.8.8; rm -rf /"` chains a second
command.
Java: `Runtime.getRuntime().exec("ping " + host)` has the same issue.

## Fix
- Avoid shell invocation entirely if possible — use a language-native library instead of shelling out.
- If a subprocess is required, pass the command and arguments as a list, never a concatenated string, and
  never with `shell=True` (Python) — this avoids shell metacharacter interpretation entirely.
- If user input must be part of a command, strictly validate it against an allowlist of expected values.
- Run subprocess calls with least-privilege (a restricted user/service account, not root).
