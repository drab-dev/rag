"""LLM client wrapper for Groq-based chat completions.

This module provides a small abstraction over the Groq Python SDK so the
rest of the backend can call an LLM without depending directly on the
client details. It is intentionally minimal:

- Reads GROQ_API_KEY from the environment (handled by the Groq SDK).
- Exposes `is_llm_configured()` to allow fast checks and graceful fallbacks.
- Exposes `call_llm_for_json(...)` which asks the model to return strict JSON
  and parses it into a Python dict, with some robustness for slightly messy
  outputs.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:  # The groq package may not be installed in all environments yet.
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover - import error handled at runtime
    Groq = None  # type: ignore


_CLIENT: Optional["Groq"] = None


def _get_client() -> Optional["Groq"]:
    """Return a singleton Groq client instance, or None if unavailable.

    We treat the client as unavailable if:
    - The groq package is not installed, or
    - The GROQ_API_KEY environment variable is not set.
    """

    global _CLIENT

    if _CLIENT is not None:
        return _CLIENT

    if Groq is None:
        return None

    # The Groq client will look up GROQ_API_KEY from the environment.
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        _CLIENT = Groq(api_key=api_key)
        return _CLIENT
    except Exception:
        # If client construction fails, treat as unavailable.
        _CLIENT = None
        return None


def is_llm_configured() -> bool:
    """Return True if the Groq LLM client appears to be usable."""

    return _get_client() is not None


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from raw model text.

    The model is instructed to return strict JSON, but we defend against
    small deviations (leading text, markdown fences, etc.) by locating the
    first "{" and the last "}" and attempting to parse the substring.
    """

    text = text.strip()

    # Fast path: direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to locate a JSON object inside the text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM output did not contain a JSON object")

    candidate = text[start : end + 1]
    return json.loads(candidate)


def call_llm_for_json(
    *,
    model: str = "openai/gpt-oss-20b",
    system_prompt: str,
    user_content: str,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
) -> Dict[str, Any]:
    """Call the Groq LLM and parse the response as JSON.

    Args:
        model: Groq model identifier.
        system_prompt: System message guiding the model's behavior.
        user_content: User message content (typically JSON or structured text).
        temperature: Sampling temperature.
        max_output_tokens: Maximum tokens in the completion.

    Returns:
        Parsed JSON as a Python dict.

    Raises:
        RuntimeError: If the LLM client is not available.
        ValueError / json.JSONDecodeError: If the output cannot be parsed as JSON.
    """

    client = _get_client()
    if client is None:
        raise RuntimeError("Groq LLM client is not configured (missing package or GROQ_API_KEY)")

    # Compose messages. We tell the model *explicitly* to respond with JSON.
    system_message = (
        system_prompt
        + "\n\nRespond with a single valid JSON object only. Do not include any "
        "markdown, code fences, or explanatory text."
    )

    completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_completion_tokens=max_output_tokens,
        top_p=1,
        reasoning_effort="medium",
        stream=False,
        stop=None,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ],
    )

    # Non-streaming: take the first choice's content.
    choice = completion.choices[0]
    text = choice.message.content or ""
    return _extract_json_from_text(text)
