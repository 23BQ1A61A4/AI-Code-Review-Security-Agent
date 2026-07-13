---
id: secure-session-management
title: Secure Session Management
category: file_and_session
owasp_category: "A07:2021 - Identification and Authentication Failures"
cwe_id: CWE-384
languages: [python, java]
tags: [session, cookies]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Session Management

## Session identifiers
- Generate session IDs with a cryptographically secure random generator, long enough to resist guessing
  (128+ bits of entropy).
- Rotate the session ID after login (prevents session fixation, where an attacker pre-sets a victim's
  session ID before they authenticate).
- Invalidate the session server-side on logout — don't rely solely on the client discarding the cookie.

## Cookie flags
- `Secure`: cookie is only sent over HTTPS.
- `HttpOnly`: cookie isn't accessible to JavaScript, mitigating cookie theft via XSS.
- `SameSite=Lax` or `Strict`: cookie isn't sent on most cross-site requests, mitigating CSRF.

## Lifetime
- Set a reasonable absolute session timeout and an idle timeout; don't let sessions live indefinitely.
- For sensitive actions (changing email/password, viewing payment details), consider requiring
  re-authentication even within an active session.

## Storage
- Prefer server-side session storage (with only an opaque ID in the cookie) over storing sensitive data
  directly in a client-side cookie/JWT payload, which the client can read even if it can't forge it.
