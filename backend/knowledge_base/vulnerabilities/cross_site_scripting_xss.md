---
id: cross-site-scripting-xss
title: Cross-Site Scripting (XSS)
category: vulnerability
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-79
languages: [python, java]
tags: [injection, frontend, output-encoding]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Cross-Site Scripting (XSS)

XSS occurs when untrusted input is rendered into a page as HTML/JavaScript without proper encoding, letting
an attacker's script run in another user's browser — stealing session cookies, defacing the page, or acting
on the victim's behalf.

## Types
- **Reflected**: payload comes from the current request (e.g. a search query echoed back unescaped).
- **Stored**: payload is saved (e.g. a comment) and rendered to other users later.
- **DOM-based**: vulnerable JavaScript writes untrusted data into the DOM client-side.

## Fix
- Rely on your templating engine's autoescaping (Jinja2/Django templates escape by default) — don't
  manually build HTML strings with concatenation.
- Never mark untrusted data as "safe" (`mark_safe()`, `|safe`) without independently sanitizing it.
- Encode based on context: HTML body, HTML attribute, JavaScript string, and URL each need different
  encoding.
- Set a Content-Security-Policy header as defense in depth, restricting script sources.
- For DOM-based XSS, avoid `innerHTML`/`document.write()` with untrusted data; use `textContent` or a
  sanitization library.
