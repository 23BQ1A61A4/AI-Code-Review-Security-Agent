---
id: a07-identification-and-authentication-failures
title: A07:2021 - Identification and Authentication Failures
category: owasp_top_10
owasp_category: "A07:2021 - Identification and Authentication Failures"
cwe_id: CWE-287
languages: [python, java]
tags: [authentication, session-management]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A07:2021 - Identification and Authentication Failures

Weaknesses in how an application confirms a user's identity, authenticates them, and manages their session.

## Common patterns
- Permitting weak passwords, or no protection against credential stuffing / brute force.
- Storing passwords in plaintext or with weak hashing (MD5, unsalted SHA1).
- Session IDs exposed in URLs, not rotated after login, or with excessively long lifetimes.
- Missing or ineffective multi-factor authentication for sensitive accounts.

## Prevention
- Hash passwords with bcrypt/scrypt/Argon2; never a fast general-purpose hash.
- Implement rate limiting / account lockout with backoff on authentication endpoints.
- Enforce a reasonable password policy (length over complexity rules) and check against known-breached
  password lists.
- Rotate session identifiers on privilege change (e.g. login), and set secure session cookie flags
  (Secure, HttpOnly, SameSite).
- Offer and, for sensitive contexts, require multi-factor authentication.
