"""
Synthesizer LLM call — generates the user-facing response.

Uses the strategy instruction as the only varying part of the system prompt.
The LLM is required to wrap its output as `{"rendered_format": "...",
"response": "..."}` so we can audit format compliance.

If the LLM ignores the wrapper, we fall back to per-strategy default
`rendered_format` and treat the raw text as the response.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Generator, List, Tuple

import anthropic

from ..strategies import (
    FORMAT_EXPECTATIONS,
    RENDERED_FORMAT_VOCABULARY,
)
from .prompts import build_synthesizer_system_prompt


def generate_response(
    client: anthropic.Anthropic,
    model: str,
    query: str,
    strategy: str,
    history: List[Dict[str, str]],
    max_tokens: int = 1500,
) -> Tuple[str, str]:
    """Run the synthesizer LLM call and parse its JSON wrapper.

    Returns (rendered_format, response_text). If parsing fails, falls back
    to (per-strategy-default, raw_text).
    """
    messages: List[Dict[str, str]] = [dict(m) for m in history]
    messages.append({"role": "user", "content": query})

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=build_synthesizer_system_prompt(strategy),
        messages=messages,
    )

    raw = _extract_text(response).strip()
    return parse_generation_wrapper(raw, strategy)


def generate_response_stream(
    client: anthropic.Anthropic,
    model: str,
    query: str,
    strategy: str,
    history: List[Dict[str, str]],
    max_tokens: int = 1500,
) -> Generator[Dict[str, Any], None, None]:
    """Streaming variant of generate_response.

    Yields a sequence of dicts:
       {"type": "delta",  "text": "..."}     for each token-chunk
       {"type": "done",
        "rendered_format": "...",
        "response": "...full text..."}        once at the end (final state)

    Uses Anthropic's native streaming API. We accumulate the raw text, then
    parse the JSON wrapper at the end exactly like the non-streaming path.
    During streaming we emit the *raw* text (which is JSON-ish) — the UI
    detects when the "response": "..." field begins and only shows from there.
    """
    messages: List[Dict[str, str]] = [dict(m) for m in history]
    messages.append({"role": "user", "content": query})

    accumulated: List[str] = []

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=build_synthesizer_system_prompt(strategy),
        messages=messages,
    ) as stream:
        for text_chunk in stream.text_stream:
            if text_chunk:
                accumulated.append(text_chunk)
                yield {"type": "delta", "text": text_chunk}

    raw = "".join(accumulated).strip()
    rendered_format, response_text = parse_generation_wrapper(raw, strategy)
    yield {
        "type":            "done",
        "rendered_format": rendered_format,
        "response":        response_text,
        "raw":             raw,
    }


def parse_generation_wrapper(text: str, strategy: str) -> Tuple[str, str]:
    """Parse `{"rendered_format": "...", "response": "..."}` from LLM output.

    Falls back gracefully if the model didn't honor the wrapper:
      - JSON parse fails: return (fallback_format, raw_text).
      - JSON parses but rendered_format is unknown: coerce to "hybrid".
    """
    fallback = _fallback_format(strategy)

    if not text:
        return fallback, ""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    parsed = _try_parse_json(cleaned)
    if parsed is None:
        # Try locating the first {...} block as a final attempt
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            parsed = _try_parse_json(cleaned[start : end + 1])

    if isinstance(parsed, dict) and "response" in parsed:
        rendered_format = (parsed.get("rendered_format") or fallback).strip()
        if rendered_format not in RENDERED_FORMAT_VOCABULARY:
            rendered_format = "hybrid"
        response_text = str(parsed.get("response", ""))
        return rendered_format, response_text

    # Parsing failed — preserve the raw text as the response
    return fallback, text


def _fallback_format(strategy: str) -> str:
    """Per-strategy default rendered_format used when JSON parse fails."""
    expected = FORMAT_EXPECTATIONS.get(strategy)
    if not expected or expected == "*":
        return "paragraph"
    return expected


def _try_parse_json(s: str) -> Any:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_text(response: Any) -> str:
    """Extract concatenated text from an Anthropic response object."""
    parts: List[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)
