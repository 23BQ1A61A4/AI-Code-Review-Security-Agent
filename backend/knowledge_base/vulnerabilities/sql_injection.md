---
id: sql-injection
title: SQL Injection
category: vulnerability
owasp_category: "A03:2021 - Injection"
cwe_id: CWE-89
languages: [python, java]
tags: [injection, database]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# SQL Injection

SQL Injection occurs when untrusted input is concatenated or formatted directly into a SQL query, letting
an attacker alter the query's structure — read unauthorized data, bypass authentication, or in some cases
modify/delete data or execute admin operations on the database.

## Example (vulnerable)
Python: `cursor.execute(f"SELECT * FROM users WHERE id={user_id}")`
Java: `stmt.executeQuery("SELECT * FROM users WHERE id=" + userId)`

An attacker supplying `user_id = "1 OR 1=1"` returns every row instead of one.

## Fix
Python: `cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))`
Java: use `PreparedStatement` with `?` placeholders and `setInt()`/`setString()`.

## Defense in depth
- Parameterized queries/prepared statements are the primary defense — always use them.
- Apply least-privilege database accounts (the application's DB user shouldn't have DROP/ALTER rights it
  doesn't need).
- Validate input types/format where the expected shape is known (e.g. numeric IDs).
- Use an ORM correctly — watch for "raw SQL" escape hatches that reintroduce the same risk.
