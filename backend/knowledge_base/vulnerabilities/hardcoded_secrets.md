---
id: hardcoded-secrets
title: Hardcoded Secrets
category: vulnerability
owasp_category: "A02:2021 - Cryptographic Failures"
cwe_id: CWE-798
languages: [python, java]
tags: [secrets, credentials]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Hardcoded Secrets

Committing API keys, passwords, or tokens directly into source code is a critical exposure — the secret
ends up in version control history permanently, even if a later commit removes it, and is visible to
anyone with repository access (including, if the repo is ever made public, everyone).

## Example (vulnerable)
`API_KEY = "sk_live_51H8x..."` committed directly in application code.

## Fix
- Load secrets from environment variables or a dedicated secrets manager (AWS Secrets Manager, HashiCorp
  Vault, GCP Secret Manager, Azure Key Vault) — never as literals in code.
- Add a pre-commit secret scanner (gitleaks, truffleHog, or your platform's built-in secret scanning) to
  catch accidental commits before they're pushed.
- Rotate any secret that was ever committed, even if later removed — assume it's compromised, since git
  history isn't automatically purged.
- Use `.env` files for local development, excluded from version control via `.gitignore`, never committed.
