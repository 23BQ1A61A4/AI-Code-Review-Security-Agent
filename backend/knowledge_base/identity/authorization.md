---
id: authorization
title: Authorization
category: identity
owasp_category: "A01:2021 - Broken Access Control"
cwe_id: CWE-285
languages: [python, java]
tags: [authorization, rbac, access-control]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Authorization

Authorization determines *what* an authenticated user is allowed to do — distinct from authentication,
which only confirms who they are.

## Core practices
- Default-deny: a request is rejected unless explicitly authorized, not the other way around.
- Enforce authorization server-side on every request — never trust a client-side check (a hidden button,
  a disabled menu item) as the actual control.
- Verify resource ownership, not just role — a "user" role check alone doesn't prevent user A from
  accessing user B's specific resource (see IDOR).
- Use a well-understood model (RBAC — role-based, or ABAC — attribute-based) rather than ad-hoc
  scattered checks; centralize the logic so it's consistent and auditable.
- Re-check authorization on every sensitive action, not just at login — a user's permissions can change
  mid-session (e.g. account suspended).
- Log authorization failures; repeated failures from one account/IP are a strong signal worth alerting on.
