---
id: authentication
title: Authentication
category: identity
owasp_category: "A07:2021 - Identification and Authentication Failures"
cwe_id: CWE-287
languages: [python, java]
tags: [authentication, login, mfa]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Authentication

Authentication confirms *who* a user is, distinct from authorization (what they're allowed to do).

## Core practices
- Never store passwords in plaintext or with a fast general-purpose hash (MD5, SHA1, even unsalted SHA256).
  Use bcrypt, scrypt, or Argon2, which are deliberately slow and salted.
- Rate-limit login attempts (per account and per IP) with exponential backoff to slow brute-force/credential
  stuffing attacks.
- Use generic error messages ("invalid username or password") rather than revealing whether the username
  exists — this prevents username enumeration.
- Support and, for sensitive accounts/actions, require multi-factor authentication (TOTP, WebAuthn/passkeys
  preferred over SMS).
- Generate session tokens with a cryptographically secure random generator (`secrets.token_urlsafe()` in
  Python, `SecureRandom` in Java), never sequential or predictable IDs.
- Rotate the session identifier after login (prevents session fixation).
- For password reset, use a single-use, time-limited, cryptographically random token sent to a verified
  channel — never a predictable value like a user ID.
