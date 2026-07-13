---
id: secure-file-upload
title: Secure File Upload
category: file_and_session
owasp_category: "A04:2021 - Insecure Design"
cwe_id: CWE-434
languages: [python, java]
tags: [file-upload, validation]
source: internal-authored
version: 1
last_updated: 2026-07-12
---

# Secure File Upload

File upload features are a common attack vector — a malicious upload can lead to remote code execution,
XSS (via an uploaded HTML/SVG file), or path traversal.

## Core practices
- Validate the file extension AND the actual file content/MIME type (don't trust the client-supplied
  `Content-Type` header or extension alone) — a common bypass is a `.php` file renamed `.jpg`.
- Generate a new, random filename for the stored file rather than trusting the client-supplied filename,
  which prevents path traversal and overwrite attacks.
- Store uploads outside the web root, or in object storage (S3, GCS) that doesn't execute code, so even a
  successfully uploaded malicious file can't be directly executed by visiting its URL.
- Enforce a maximum file size to prevent denial-of-service via huge uploads.
- Scan uploaded files for malware where feasible, especially if they'll be shared with other users.
- For image uploads specifically, re-encode the image server-side (rather than passing the original bytes
  through) to strip any embedded malicious payload.
