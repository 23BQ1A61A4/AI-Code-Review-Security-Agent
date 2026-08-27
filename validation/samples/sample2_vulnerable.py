"""
Sample 2 — Python code with realistic security issues.

Intentional issues:
  - SQL injection via string-concatenated query
  - hardcoded credential
  - command injection via os.system with untrusted input
  - use of a weak hash (MD5) for password storage
  - a bare except that silently swallows errors
"""
import hashlib
import os
import sqlite3


DB_PASSWORD = "prod-db-p@ssw0rd"


def get_user_by_name(username):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cur.execute(query)
    return cur.fetchone()


def backup_user_folder(username):
    os.system("tar -czf /backups/" + username + ".tar.gz /data/" + username)


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def load_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        pass
