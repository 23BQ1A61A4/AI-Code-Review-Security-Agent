---
id: cryptography
title: Cryptography
category: data_handling
owasp_category: "A02:2021 - Cryptographic Failures"
cwe_id: CWE-327
languages: [python, java]
tags: [cryptography, encryption, hashing]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Cryptography

## Encryption
- Use AES-256-GCM (authenticated encryption) for symmetric encryption; avoid ECB mode entirely (it leaks
  patterns in the plaintext) and avoid DES/3DES (too weak/slow for modern use).
- Use TLS 1.2+ for data in transit; disable older TLS/SSL versions and weak cipher suites.

## Hashing
- For general-purpose hashing (checksums, non-secret data), use SHA-256 or better — never MD5 or SHA1,
  both of which have known collision weaknesses.
- For passwords specifically, use a dedicated slow hash: bcrypt, scrypt, or Argon2 — never a fast
  general-purpose hash, even SHA-256, since fast hashes are brute-forceable at scale.

## Key management
- Never hardcode encryption keys in source code; use a secrets manager or KMS (Key Management Service).
- Rotate keys periodically and have a plan for re-encrypting data on rotation.
- Use distinct keys for distinct purposes — don't reuse one key across encryption, signing, and MAC.

## Randomness
- Use a cryptographically secure random number generator for anything security-sensitive (tokens, keys,
  nonces): `secrets` module in Python, `SecureRandom` in Java — never `random`/`Math.random()`.
