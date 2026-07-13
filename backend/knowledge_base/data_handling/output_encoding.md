---
id: output-encoding
title: Output Encoding
category: data_handling
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-116
languages: [python, java]
tags: [output-encoding, xss]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Output Encoding

Output encoding transforms data so it's interpreted as data, not code, by whatever's consuming it — the
primary defense against XSS and injection into non-database interpreters.

## Core practices
- Encode based on context — the same string needs different encoding depending on whether it lands in an
  HTML body, an HTML attribute, a JavaScript string, a URL, or a CSS value.
- Rely on your templating engine's autoescaping by default (Jinja2, Django templates, Thymeleaf) rather
  than manually concatenating markup strings.
- Never bypass autoescaping (`mark_safe()`, `|safe`, `dangerouslySetInnerHTML`) on data derived from user
  input without independently sanitizing it with a dedicated library.
- For JSON responses, ensure the framework is serializing correctly (not string-concatenating JSON), which
  handles escaping automatically.
- Set the `Content-Type` header explicitly and correctly — letting a browser guess content type can enable
  MIME-sniffing-based attacks.
