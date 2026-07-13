# Secure Coding Knowledge Base

30 structured Markdown documents covering OWASP Top 10, secure Python/Java coding, 17 individual
vulnerability/practice topics, authentication, authorization, and operational security topics. This is
**content + structure only** — no embeddings, no vector store, no retrieval. Loading and chunking-prep
logic lives in `app/rag/` (`loader.py`, `schema.py`, `indexing_prep.py`).

## Folder structure

```
knowledge_base/
├── owasp_top_10/              10 docs — one per OWASP Top 10 (2021) category
├── secure_coding/              2 docs — Python and Java language-specific guides
├── vulnerabilities/            8 docs — focused technical deep-dives (SQLi, XSS, CSRF,
│                                        Command Injection, Path Traversal, SSRF,
│                                        Hardcoded Secrets, Broken Access Control)
├── identity/                   2 docs — Authentication, Authorization
├── data_handling/              3 docs — Input Validation, Output Encoding, Cryptography
├── operations/                 2 docs — Logging, Error Handling
└── file_and_session/           3 docs — Secure File Upload, Secure Password Storage,
                                          Secure Session Management
```

Why some topics appear twice (e.g. SQL Injection is both part of `owasp_top_10/a03_injection.md`
and its own `vulnerabilities/sql_injection.md`): the OWASP doc covers the whole category at a survey
level; the vulnerability doc is a focused, example-driven deep dive on that one issue. A retriever
answering "how do I prevent SQL injection in Python" benefits from the focused doc; one answering
"what's OWASP A03" benefits from the category overview. Real-world knowledge bases commonly have this
kind of intentional overlap.

## Document format

Every document is Markdown with a YAML front-matter header:

```markdown
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
... Markdown content ...
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable, unique, kebab-case. Never reuse an id for a different document. |
| `title` | yes | Human-readable. |
| `category` | yes | Must match a `KnowledgeCategory` enum value (see `app/rag/schema.py`) — also the folder it lives in. |
| `owasp_category` | no | e.g. `"A03:2021 - Injection"` |
| `cwe_id` | no | e.g. `CWE-89` |
| `languages` | no | Which languages the guidance applies to — `[python, java]`, or just one. |
| `tags` | no | Free-form, for future filtering/faceting. |
| `source` | no | Defaults to `internal-authored`; use this field to note if a doc is adapted from an external source (with attribution) later. |
| `version` | no | Bump when a document's guidance changes materially. |
| `last_updated` | no | ISO date. |

## Adding a new document

1. Create a new `.md` file under the appropriate category folder.
2. Add the front-matter block with at minimum `id`, `title`, `category`.
3. Run the loader to validate it: `python -c "from app.rag.loader import load_knowledge_base; load_knowledge_base()"` — it raises immediately if the front-matter is malformed, the category is invalid, or the `id` collides with an existing document.
4. No other registration step is needed — the loader discovers every `.md` file under `knowledge_base/` automatically.
