"""
Dynamic wrapper around the Gemini API, read from environment or .env.

Every agent goes through `generate()`. If GEMINI_API_KEY (or GOOGLE_API_KEY) is not set,
the required SDK isn't installed, or the call fails (e.g. no network/quota),
`generate()` raises `LLMUnavailable` and the caller (each agent) falls back
to its local, rule-based analysis so the platform still runs end-to-end
without an internet connection or API key — see each agent's `*_local()`
function.
"""
from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

load_dotenv()


def get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


class LLMUnavailable(Exception):
    """Raised when no LLM backend can be reached; callers should fall back."""


def extract_json(text: str) -> dict | list:
    """Safely extracts JSON data from LLM responses even if wrapped in markdown code blocks or commentary."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.I)
        clean = re.sub(r"\s*```$", "", clean)
        clean = clean.strip()
    
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", clean)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {clean[:200]}")


def generate(prompt: str, system: str | None = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise LLMUnavailable("GEMINI_API_KEY / GOOGLE_API_KEY not set")

    model_name = get_model_name()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    # 1. Try modern google-genai package
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model_name, contents=full_prompt)
        text = getattr(response, "text", None)
        if text:
            return text.strip()
    except ImportError:
        pass
    except Exception as e:
        raise LLMUnavailable(f"google-genai error: {e}") from e

    # 2. Try legacy google-generativeai package if installed
    try:
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key)
        model = legacy_genai.GenerativeModel(model_name)
        response = model.generate_content(full_prompt)
        text = getattr(response, "text", None)
        if text:
            return text.strip()
    except ImportError:
        pass
    except Exception as e:
        raise LLMUnavailable(f"google-generativeai error: {e}") from e

    raise LLMUnavailable("Neither google-genai nor google-generativeai SDK is installed or available.")
