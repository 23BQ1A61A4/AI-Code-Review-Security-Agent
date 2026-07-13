---
id: a10-server-side-request-forgery
title: A10:2021 - Server-Side Request Forgery (SSRF)
category: owasp_top_10
owasp_category: "A10:2021 - Server-Side Request Forgery"
cwe_id: CWE-918
languages: [python, java]
tags: [ssrf, network]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A10:2021 - Server-Side Request Forgery (SSRF)

SSRF happens when an application fetches a remote resource based on a URL supplied (directly or indirectly)
by the user, without validating the destination — letting an attacker make the server issue requests to
internal systems, cloud metadata endpoints, or arbitrary external hosts.

## Common patterns
- A "fetch this URL and show a preview" or webhook feature that accepts any URL.
- Image/file processing that fetches a remote resource by URL.
- No restriction on target hostname/IP, allowing requests to `169.254.169.254` (cloud metadata) or internal
  services (`localhost`, private IP ranges).

## Prevention
- Validate and allowlist destination hosts/schemes before making an outbound request on behalf of user input.
- Block requests to private/link-local IP ranges and cloud metadata endpoints at the network layer.
- Disable automatic redirect-following, or re-validate the destination after each redirect.
- Use a dedicated, isolated network segment for services that must fetch user-supplied URLs.
