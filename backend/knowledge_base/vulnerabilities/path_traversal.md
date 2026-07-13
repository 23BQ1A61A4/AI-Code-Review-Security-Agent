---
id: path-traversal
title: Path Traversal
category: vulnerability
owasp_category: "A01:2021 - Broken Access Control"
cwe_id: CWE-22
languages: [python, java]
tags: [access-control, file-system]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Path Traversal

Path (directory) traversal occurs when user input is used to build a file path without validation, letting
an attacker use `../` sequences (or absolute paths) to access files outside the intended directory.

## Example (vulnerable)
`open(os.path.join(UPLOAD_DIR, request.args.get("file")))` — a request for
`file=../../etc/passwd` escapes `UPLOAD_DIR` entirely.

## Fix
- Validate the requested filename against an allowlist of expected values/patterns; reject anything
  containing `..`, absolute paths, or null bytes.
- Resolve the final path and verify it's still within the intended base directory
  (`os.path.realpath()` / `Path.resolve()` and a prefix check) before opening it.
- Where possible, use an opaque identifier (a database key) rather than a user-supplied filename to look
  up the actual file location.
- Run the application with a filesystem user that has no access outside the directories it legitimately
  needs.
