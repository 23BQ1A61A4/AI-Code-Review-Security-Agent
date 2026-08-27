# OWASP Top 10 — Secure Coding Reference (2021 categories)

## A01: Broken Access Control
Occurs when restrictions on what authenticated users can do are not enforced.
Common causes: missing checks on object ownership before read/update/delete,
trusting client-supplied IDs, missing role checks on admin endpoints, and
CORS misconfiguration. Mitigation: enforce access control server-side on
every request, deny by default, and use centralized authorization logic
instead of scattering checks across handlers.

A related issue is Cross-Site Request Forgery (CSRF): a malicious site
tricks a logged-in user's browser into submitting an authenticated request
(e.g. changing a password or making a purchase) without the user's intent,
because the request carries valid session cookies automatically. Mitigate
CSRF with anti-CSRF tokens on state-changing requests and `SameSite`
cookies.

## A02: Cryptographic Failures
Sensitive data exposed because it was never encrypted, was encrypted with a
weak or broken algorithm (MD5, SHA1, DES, ECB mode), or used a hardcoded key.
Mitigation: use vetted libraries, strong modern algorithms (AES-GCM, bcrypt
or Argon2 for passwords), and never hardcode keys or secrets in source code.

## A03: Injection
Untrusted input is concatenated into a query, command, or template and
interpreted as code. Includes SQL injection, command injection, LDAP
injection, and template injection. Mitigation: use parameterized queries or
an ORM, never build SQL/shell commands via string concatenation or
f-strings with user input, and validate/escape input at trust boundaries.

## A04: Insecure Design
Missing or ineffective security controls at the design stage — for example,
no rate limiting on a login endpoint, or business logic that can be abused
(e.g. negative quantities in a shopping cart). Mitigation: threat model
early, apply secure design patterns, and use tested reference architectures.

## A05: Security Misconfiguration
Default credentials, verbose error messages leaking stack traces, debug
mode left on in production, unnecessary features/ports enabled, or missing
security headers. Mitigation: harden configuration, disable debug mode in
production, and remove unused features and default accounts.

## A06: Vulnerable and Outdated Components
Using libraries or frameworks with known vulnerabilities, or components no
longer maintained. Mitigation: track dependency versions, subscribe to
vulnerability advisories, and patch promptly.

## A07: Identification and Authentication Failures
Weak password policies, session IDs exposed in URLs, missing multi-factor
authentication, and predictable session tokens. Mitigation: use a vetted
auth framework, enforce strong password/session policies, and rotate
session identifiers after login.

## A08: Software and Data Integrity Failures
Code or infrastructure that relies on plugins, libraries, or CI/CD steps
from untrusted sources without verifying integrity, or insecure
deserialization of untrusted data (e.g. Python `pickle.loads`, Java
`ObjectInputStream.readObject` on attacker-controlled bytes). Mitigation:
verify signatures/checksums, and avoid deserializing untrusted data.

## A09: Security Logging and Monitoring Failures
Insufficient logging of authentication attempts, access control failures,
and server-side errors, or logs that are not monitored. Mitigation: log
security-relevant events with enough context, protect log integrity, and
alert on suspicious activity.

## A10: Server-Side Request Forgery (SSRF)
The application fetches a remote resource using a URL supplied by the
user without validating or restricting the destination, allowing an
attacker to reach internal services. Mitigation: allow-list destination
hosts, disable unused URL schemes, and isolate outbound network calls.
