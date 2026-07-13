"""
Shared LLM client wrapper — Module 2.

A thin, reusable wrapper around the Anthropic API so every agent (this one's
semantic pass, and Security/Remediation/PR Summary in later modules) calls
the model the same way instead of duplicating client setup and JSON-parsing
boilerplate. Sharing this utility does NOT mean agents share prompts or
combine their logic — each agent still builds its own system prompt and
interprets the response independently.

The client is created lazily (on first call) rather than at import time, so
importing this module — and therefore starting the FastAPI app — doesn't
fail just because ANTHROPIC_API_KEY isn't set yet. The key is only required
when an agent actually makes a call.
"""

import json
from typing import Any, Dict, Optional

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()  # reads ANTHROPIC_API_KEY from environment
    return _client


def call_llm(system: str, user: str, max_tokens: int = 1000) -> str:
    """Make a single LLM call and return the concatenated text response."""
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def parse_json_safely(raw: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Strip markdown code fences if present and parse JSON, falling back safely on error."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return fallback
