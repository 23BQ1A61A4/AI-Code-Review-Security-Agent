---
id: a02-cryptographic-failures
title: A02:2021 - Cryptographic Failures
category: owasp_top_10
owasp_category: "A02:2021 - Cryptographic Failures"
cwe_id: CWE-310
languages: [python, java]
tags: [cryptography, sensitive-data, encryption]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A02:2021 - Cryptographic Failures

Formerly "Sensitive Data Exposure," renamed to focus on the root cause: failures related to cryptography
(or its absence) that lead to exposure of sensitive data.

## Common patterns
- Transmitting sensitive data in plaintext (HTTP instead of HTTPS, unencrypted internal traffic).
- Using weak or outdated algorithms (MD5, SHA1, DES) for hashing or encryption.
- Hardcoded or weak encryption keys, or keys that are never rotated.
- Storing sensitive data that doesn't need to be stored at all (e.g. full credit card numbers).
- Missing encryption at rest for sensitive database fields.

## Prevention
- Classify data and encrypt sensitive data at rest and in transit by default.
- Use strong, modern algorithms: AES-256-GCM for encryption, SHA-256 or better for general hashing,
  and bcrypt/scrypt/Argon2 specifically for password hashing.
- Manage keys via a dedicated secrets manager, not source code or config files.
- Disable caching for responses containing sensitive data.
- Enforce HTTPS everywhere (HSTS headers) and disable weak TLS versions/ciphers.
