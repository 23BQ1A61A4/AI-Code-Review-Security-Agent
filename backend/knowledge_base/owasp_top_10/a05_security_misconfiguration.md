---
id: a05-security-misconfiguration
title: A05:2021 - Security Misconfiguration
category: owasp_top_10
owasp_category: "A05:2021 - Security Misconfiguration"
cwe_id: CWE-16
languages: [python, java]
tags: [configuration, hardening]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A05:2021 - Security Misconfiguration

The most commonly seen category — happens when security settings are left at insecure defaults, misconfigured,
or simply missing.

## Common patterns
- Debug mode / verbose error pages enabled in production, leaking stack traces and internal details.
- Default credentials left unchanged on databases, admin panels, or cloud services.
- Unnecessary features, ports, services, or sample applications left enabled.
- Overly permissive CORS policy (`Access-Control-Allow-Origin: *`).
- Missing security headers (Content-Security-Policy, X-Content-Type-Options, Strict-Transport-Security).
- Cloud storage buckets left publicly readable/writable.

## Prevention
- Have a repeatable, automated hardening process for every environment (dev/staging/prod) rather than
  manual one-off configuration.
- Disable debug mode and verbose errors in production; return generic errors to clients, log details
  server-side.
- Remove unused features, sample apps, and default accounts before deployment.
- Scan configuration (especially cloud infrastructure) automatically for common misconfigurations.
- Set security headers by default at the framework/proxy level.
