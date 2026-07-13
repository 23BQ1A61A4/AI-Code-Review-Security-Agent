---
id: secure-python-coding
title: Secure Python Coding Practices
category: secure_coding
languages: [python]
tags: [python, secure-coding, best-practices]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Python Coding Practices

## Injection
- Always use parameterized queries (`cursor.execute(query, params)`), never f-strings/`%`/`.format()` to
  build SQL.
- Avoid `shell=True` in `subprocess`; pass command and arguments as a list.
- Never use `eval()`/`exec()` on untrusted input.

## Deserialization
- Never call `pickle.loads()` on untrusted data — it can execute arbitrary code.
- Use `yaml.safe_load()`, never plain `yaml.load()`, for untrusted YAML.
- Prefer JSON for untrusted data interchange.

## Secrets
- Load secrets from environment variables or a secrets manager, never hardcode them.
- Use `secrets.token_urlsafe()` for security-sensitive random values, never `random`.

## Web frameworks (Flask/Django)
- Keep template autoescaping enabled; avoid `mark_safe()`/`|safe` on untrusted input.
- Keep CSRF protection enabled (`WTF_CSRF_ENABLED`, Django's `CsrfViewMiddleware`).
- Set `SESSION_COOKIE_SECURE=True` and `SESSION_COOKIE_HTTPONLY=True` in production.

## Passwords
- Hash with `bcrypt` or `passlib`'s Argon2/bcrypt handlers, never `hashlib.md5`/`sha1` directly.

## Dependencies
- Pin versions in `requirements.txt`/lockfiles; run `pip-audit` in CI.

## Type safety and validation
- Use type hints and a validation library (e.g. Pydantic) at trust boundaries (API input) to reject
  malformed data early.
