---
id: a04-insecure-design
title: A04:2021 - Insecure Design
category: owasp_top_10
owasp_category: "A04:2021 - Insecure Design"
cwe_id: CWE-1006
languages: [python, java]
tags: [design, threat-modeling]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A04:2021 - Insecure Design

Insecure design is a broad category about missing or ineffective security controls at the design stage —
distinct from an implementation bug. Even perfect code can't fix a fundamentally insecure design.

## Common patterns
- No threat modeling done before building a sensitive feature (e.g. password reset, payments).
- Business logic flaws: e.g. a checkout flow that trusts a client-submitted price rather than recalculating
  it server-side.
- Missing rate limiting on sensitive operations (login, password reset, OTP verification), enabling abuse.
- Trusting client-side validation as the only line of defense.

## Prevention
- Threat-model new features before building them: what can go wrong, who's the attacker, what's the impact.
- Use secure design patterns and reference architectures rather than inventing security-critical flows
  from scratch.
- Enforce business rules and limits server-side, always — treat every client input as untrusted.
- Segment the application so a compromise of one component has limited blast radius.
- Write abuse-case tests, not just happy-path tests.
