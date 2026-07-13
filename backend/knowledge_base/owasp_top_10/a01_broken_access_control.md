---
id: a01-broken-access-control
title: A01:2021 - Broken Access Control
category: owasp_top_10
owasp_category: "A01:2021 - Broken Access Control"
cwe_id: CWE-284
languages: [python, java]
tags: [access-control, authorization, idor]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A01:2021 - Broken Access Control

Broken access control moved to the #1 OWASP category in 2021, reflecting how common it is in real breaches.
It occurs when an application fails to properly enforce what an authenticated user is allowed to do.

## Common patterns
- **Insecure Direct Object Reference (IDOR)**: changing an ID in a URL/API call (`/orders/1042`) to access another
  user's data, because the server never checks that the caller owns resource 1042.
- **Missing function-level access control**: an admin-only endpoint is reachable by any authenticated user
  because the check exists only in the UI (a hidden button), not on the server.
- **CORS misconfiguration**: `Access-Control-Allow-Origin: *` combined with credentialed requests, letting
  any origin read authenticated responses.
- **Privilege escalation**: a user can elevate their own role by editing a client-controlled `role` field.

## Prevention
- Enforce access control server-side, on every request, never relying on client-side hiding.
- Default to deny; explicitly grant access rather than explicitly denying it.
- Verify ownership of a resource on every read/write, not just on creation.
- Use a centralized authorization mechanism (middleware/decorator) rather than duplicating checks per handler.
- Log access control failures and alert on repeated ones.
