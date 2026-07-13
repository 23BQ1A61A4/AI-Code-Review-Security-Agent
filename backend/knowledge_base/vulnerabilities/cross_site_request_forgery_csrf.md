---
id: cross-site-request-forgery-csrf
title: Cross-Site Request Forgery (CSRF)
category: vulnerability
owasp_category: "A01:2021 - Broken Access Control"
cwe_id: CWE-352
languages: [python, java]
tags: [access-control, session]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Cross-Site Request Forgery (CSRF)

CSRF tricks an authenticated user's browser into submitting an unwanted, state-changing request to an
application they're logged into — exploiting the fact that browsers automatically attach cookies to
requests, regardless of which site initiated them.

## Example
A malicious page auto-submits a form to `https://bank.example/transfer?to=attacker&amount=1000`. If the
victim is logged into `bank.example`, their session cookie is sent along, and the transfer succeeds unless
the server has CSRF protection.

## Fix
- Use anti-CSRF tokens: a unique, unpredictable token tied to the user's session, included in every
  state-changing form/request and validated server-side.
- Set cookies with `SameSite=Lax` or `SameSite=Strict` as defense in depth (blocks most cross-site
  automatic cookie attachment).
- Frameworks (Django, Spring Security, Flask-WTF) provide CSRF protection by default — don't disable it
  without a specific, documented reason (e.g. a stateless token-authenticated API that doesn't use cookies).
- For pure JSON APIs authenticated via a bearer token (not cookies), CSRF risk is much lower since the
  browser won't attach the token automatically.
