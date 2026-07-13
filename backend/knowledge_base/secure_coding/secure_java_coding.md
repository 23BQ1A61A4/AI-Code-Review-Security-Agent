---
id: secure-java-coding
title: Secure Java Coding Practices
category: secure_coding
languages: [java]
tags: [java, secure-coding, best-practices]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure Java Coding Practices

## Injection
- Use `PreparedStatement` with parameterized placeholders (`?`), never `Statement` with concatenated SQL.
- Avoid `Runtime.exec()`/`ProcessBuilder` with concatenated, user-derived command strings; pass arguments
  as a separate list.

## Deserialization
- Avoid native Java deserialization (`ObjectInputStream.readObject()`) on untrusted input; if unavoidable,
  use `ObjectInputFilter` to restrict allowed classes.

## Cryptography
- Use `AES/GCM/NoPadding`, never `DES` or ECB mode.
- Use `SHA-256` or better for general hashing; use Spring Security's `BCryptPasswordEncoder` (or Argon2)
  specifically for passwords.
- Use `SecureRandom`, never `java.util.Random`, for security-sensitive values.

## Web (Spring)
- Don't disable Spring Security's CSRF protection (`.csrf().disable()`) without a documented, deliberate
  reason (e.g. a stateless token-authenticated API).
- Set session cookies `Secure` and `HttpOnly`.
- Validate `@RequestParam`/`@PathVariable` inputs with Bean Validation (`@Valid`, `@NotNull`, `@Pattern`).

## File handling
- Sanitize/validate uploaded filenames and extensions; store uploads outside the web root with generated
  names, never the client-supplied filename.

## Dependencies
- Track dependencies in `pom.xml`/`build.gradle`; run OWASP Dependency-Check in CI.
