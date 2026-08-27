# Secure Coding Guidelines — Java

## Database access
Use `PreparedStatement` with bound parameters instead of building SQL with
string concatenation via `Statement`. Concatenating user input into a query
string (`"SELECT * FROM users WHERE name = '" + name + "'"`) is a classic
SQL injection vector.

## Secrets management
Never hardcode credentials, API keys, or symmetric keys as `String`
literals or `static final` fields. Load them from environment variables,
a properties file excluded from version control, or a secrets manager.

## Deserialization
Avoid `ObjectInputStream.readObject()` on data from an untrusted source —
Java deserialization of attacker-controlled bytes is a well-known remote
code execution vector. Prefer safe data formats like JSON with a schema,
and if native serialization is required, validate the class allow-list.

## Command execution
Avoid `Runtime.exec(String)` or `ProcessBuilder` with a command string built
from user input — this enables command injection. Use the array-argument
overloads and validate/allow-list any user-supplied values.

## Web output / XSS
Never write unescaped user input directly into an HTTP response
(`response.getWriter().println(userInput)`) or into a JSP without escaping
— this allows stored/reflected XSS. Use a templating engine with
auto-escaping, or explicitly HTML-encode output.

## Cryptography
Avoid MD5 and SHA-1 for anything security-sensitive (use SHA-256/SHA-3), and
avoid DES/ECB mode. For password storage use BCrypt or Argon2, never a fast
general-purpose hash.

## Code quality
Keep classes cohesive and methods short; long methods with high cyclomatic
complexity are hard to review and test. Avoid catching generic `Exception`
and swallowing it silently — catch specific exceptions and log with
context. Avoid public mutable static fields, and close resources
(streams, connections) in try-with-resources blocks.
