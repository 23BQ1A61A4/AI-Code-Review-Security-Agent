---
id: a08-software-and-data-integrity-failures
title: A08:2021 - Software and Data Integrity Failures
category: owasp_top_10
owasp_category: "A08:2021 - Software and Data Integrity Failures"
cwe_id: CWE-502
languages: [python, java]
tags: [deserialization, supply-chain, ci-cd]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A08:2021 - Software and Data Integrity Failures

Covers code and infrastructure that doesn't protect against integrity violations — including insecure
deserialization and unverified software updates/CI-CD pipelines.

## Common patterns
- Deserializing untrusted data with a native mechanism that can execute code (Python `pickle`, Java
  `ObjectInputStream`).
- Auto-updating software without verifying a digital signature.
- CI/CD pipelines that pull unpinned dependencies or run with excessive privilege.

## Prevention
- Never deserialize untrusted data with a native/unsafe deserializer; use a safe format (JSON) or a
  restrictive allowlist-based deserializer.
- Verify digital signatures/checksums before applying updates or trusting third-party artifacts.
- Pin dependency versions and lockfiles; review changes to CI/CD configuration like code.
- Use integrity checks (e.g. Subresource Integrity for CDN-hosted scripts).
