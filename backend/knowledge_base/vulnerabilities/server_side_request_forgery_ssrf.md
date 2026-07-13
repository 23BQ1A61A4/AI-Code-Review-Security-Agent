---
id: server-side-request-forgery-ssrf
title: Server-Side Request Forgery (SSRF)
category: vulnerability
owasp_category: "A10:2021 - Server-Side Request Forgery"
cwe_id: CWE-918
languages: [python, java]
tags: [ssrf, network]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Server-Side Request Forgery (SSRF)

SSRF lets an attacker make the server issue HTTP (or other protocol) requests on their behalf, often to
internal-only systems (databases, admin panels, cloud metadata services like `169.254.169.254`) that
aren't reachable directly from the internet.

## Example (vulnerable)
`requests.get(request.args.get("url"))` used to "fetch a preview" — an attacker supplies an internal URL
instead of a public one.

## Fix
- Allowlist destination hosts/protocols; reject requests to private IP ranges (`10.0.0.0/8`,
  `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`) and `localhost`.
- Resolve the hostname and validate the resulting IP (not just the string) — DNS rebinding can bypass a
  naive hostname check.
- Disable automatic redirect-following, or re-validate the destination after every redirect hop.
- Isolate services that must fetch user-supplied URLs on a restricted network segment with no access to
  internal infrastructure.
