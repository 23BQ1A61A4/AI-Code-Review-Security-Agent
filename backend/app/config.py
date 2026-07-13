"""
Application configuration — Module 1.

Centralized constants so later modules (agents, RAG, reports) import from
one place instead of hardcoding values. Kept as plain constants for now
(no external settings library dependency); can be swapped for
pydantic-settings reading a .env file later without touching callers.
"""

MAX_CODE_CHARS = 20000
SUPPORTED_EXTENSIONS = (".py", ".java")

CORS_ALLOW_ORIGINS = ["*"]  # tighten to your actual frontend origin(s) before production
