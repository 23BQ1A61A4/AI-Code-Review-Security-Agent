---
id: secure-password-storage
title: Secure Password Storage
category: file_and_session
owasp_category: "A02:2021 - Cryptographic Failures"
cwe_id: CWE-916
languages: [python, java]
tags: [passwords, hashing]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Password Storage

## The core rule
Never store passwords in plaintext, and never hash them with a fast general-purpose algorithm (MD5, SHA1,
even plain SHA-256) — fast hashes can be brute-forced at billions of attempts per second on modern
hardware.

## What to use instead
- **bcrypt**: widely supported, battle-tested, adjustable work factor.
- **scrypt**: memory-hard, more resistant to GPU/ASIC cracking than bcrypt.
- **Argon2**: the current recommended default (winner of the Password Hashing Competition), memory-hard
  and tunable.

All three automatically handle salting per-password, so identical passwords produce different hashes.

## Practices
- Set the work factor as high as your latency budget allows — the goal is to make brute-forcing
  computationally expensive, not to be fast.
- Never implement your own hashing scheme; use a maintained library (`bcrypt`, `passlib`, Spring Security's
  `BCryptPasswordEncoder`).
- Compare hashes using the library's constant-time verify function, never a manual `==` comparison of
  computed hashes (timing side-channel).
- On password change/reset, invalidate all other active sessions for that account.
