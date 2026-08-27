# Secure Coding Guidelines — Python

## Database access
Never build SQL with string formatting or f-strings. Use parameterized
queries: `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`
instead of `cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")`.
When using an ORM (SQLAlchemy, Django ORM), prefer the query builder over
raw SQL, and if raw SQL is unavoidable, use bound parameters.

## Secrets management
Never hardcode API keys, passwords, or tokens as string literals in source
files. Load them from environment variables (`os.getenv`) or a secrets
manager, and keep `.env` files out of version control via `.gitignore`.

## Deserialization
Avoid `pickle.loads`/`pickle.load` on data from an untrusted source —
pickle can execute arbitrary code during unpickling. Prefer `json` for
untrusted data. If YAML is required, use `yaml.safe_load`, never
`yaml.load` without an explicit safe loader.

## Command execution
Avoid `os.system` and `subprocess` calls with `shell=True` when any part of
the command includes user input — this enables command injection. Prefer
`subprocess.run([...], shell=False)` with an argument list, and validate or
allow-list inputs.

## Dynamic code execution
`eval()` and `exec()` on untrusted input allow arbitrary code execution.
Avoid them entirely for user-controlled data; use safer alternatives like
`ast.literal_eval` for parsing literals.

## Error handling
Avoid bare `except:` clauses that silently swallow all errors — catch
specific exceptions, log them with context, and avoid leaking stack traces
or internal details to end users in production responses.

## Code quality
Keep functions short and single-purpose; a function longer than ~50 lines
or with more than 4-5 parameters is a sign it should be split. Avoid deeply
nested conditionals (more than 3-4 levels) — consider early returns. Avoid
mutable default arguments (`def f(x, items=[])`), magic numbers without a
named constant, and unused imports/variables.
