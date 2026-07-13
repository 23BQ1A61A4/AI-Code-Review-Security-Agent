---
id: broken-access-control
title: Broken Access Control (technical deep dive)
category: vulnerability
owasp_category: "A01:2021 - Broken Access Control"
cwe_id: CWE-284
languages: [python, java]
tags: [access-control, authorization, idor]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Broken Access Control (technical deep dive)

Broken access control means the application allows a user to do something they shouldn't be authorized to
do — read, modify, or delete data or functionality outside their permission scope.

## Insecure Direct Object Reference (IDOR)
The most common concrete form: an endpoint accepts an object ID (`/api/invoices/1042`) and returns/modifies
it without checking that the authenticated caller actually owns or is authorized for invoice 1042 — only
that they're logged in at all.

## Fix pattern
```
# vulnerable
invoice = db.get_invoice(invoice_id)
return invoice

# fixed
invoice = db.get_invoice(invoice_id)
if invoice.owner_id != current_user.id and not current_user.is_admin:
    abort(403)
return invoice
```

## Broader guidance
- Centralize authorization logic (a decorator/middleware) rather than duplicating ownership checks in
  every handler — duplication is how checks get forgotten on a new endpoint.
- Test authorization explicitly: for every endpoint, verify a user CANNOT access another user's resource,
  not just that they CAN access their own.
- Default-deny: require an explicit authorization check to pass, rather than requiring an explicit denial.
