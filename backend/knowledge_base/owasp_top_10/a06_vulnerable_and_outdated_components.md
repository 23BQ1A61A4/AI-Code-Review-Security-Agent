---
id: a06-vulnerable-and-outdated-components
title: A06:2021 - Vulnerable and Outdated Components
category: owasp_top_10
owasp_category: "A06:2021 - Vulnerable and Outdated Components"
cwe_id: CWE-1104
languages: [python, java]
tags: [dependencies, supply-chain]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# A06:2021 - Vulnerable and Outdated Components

Using a library, framework, or other software component with a known vulnerability, or one that's no longer
maintained, exposes the whole application to that vulnerability.

## Common patterns
- Dependencies pinned to old versions with published CVEs.
- No visibility into the full dependency tree (transitive dependencies are often the actual risk).
- No process for tracking or applying security advisories.
- Using unsupported/end-of-life runtimes, frameworks, or OS versions.

## Prevention
- Maintain an inventory of dependencies and their versions (a software bill of materials).
- Run automated dependency scanning in CI (e.g. `pip-audit`, OWASP Dependency-Check, GitHub Dependabot,
  Snyk) and fail builds on known-critical CVEs.
- Subscribe to security advisories for your key dependencies and runtimes.
- Remove unused dependencies — every dependency is attack surface, used or not.
- Prefer actively-maintained libraries with a track record of prompt security fixes.
