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
from typing import Any, Dict, Generator, List, Optional, Tuple

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
    context: str = "",
    instruction_text: Optional[str] = None,
) -> Tuple[str, str]:
    """Run the synthesizer LLM call and parse its JSON wrapper.

    Returns (rendered_format, response_text). If parsing fails, falls back
    to (per-strategy-default, raw_text). `context` carries retrieved RAG
    passages injected into the system prompt as grounding.
    """
    messages: List[Dict[str, str]] = [dict(m) for m in history]
    messages.append({"role": "user", "content": query})

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=build_synthesizer_system_prompt(
            strategy,
            context,
            instruction_text=instruction_text,
        ),
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
    context: str = "",
    instruction_text: Optional[str] = None,
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
        system=build_synthesizer_system_prompt(
            strategy,
            context,
            instruction_text=instruction_text,
        ),
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
        return coerce_response_to_strategy_format(strategy, rendered_format, response_text)

    # Parsing failed — preserve the raw text as the response
    return coerce_response_to_strategy_format(strategy, fallback, text)


def coerce_response_to_strategy_format(
    strategy: str,
    rendered_format: str,
    response_text: str,
) -> Tuple[str, str]:
    """Apply deterministic repairs for high-risk format drift.

    The LLM can overfit to previous conversation shape. For bullet_contrast,
    comparison questions strongly bias it toward markdown tables even when the
    selected strategy forbids them. Convert simple tables to labelled bullet
    blocks so the rendered output matches the selected arm.
    """
    if strategy != "bullet_contrast":
        return rendered_format, response_text

    repaired = _table_to_labelled_bullets(response_text)
    if repaired:
        return "bulleted_list", repaired
    return rendered_format, response_text


def _table_to_labelled_bullets(text: str) -> str:
    """Convert a simple markdown table into two or more labelled bullet blocks."""
    rows = _parse_markdown_table(text)
    if not rows or len(rows) < 2:
        return ""

    headers = rows[0]
    data_rows = rows[1:]
    if len(headers) < 2:
        return ""

    blocks: List[str] = []
    if len(headers) >= 3:
        row_label_header = headers[0]
        option_headers = headers[1:]
        for col_idx, option in enumerate(option_headers, start=1):
            bullets = []
            for row in data_rows:
                if len(row) <= col_idx:
                    continue
                label = row[0].strip()
                value = row[col_idx].strip()
                if label and value:
                    bullets.append(f"- {label}: {value}")
                elif value:
                    bullets.append(f"- {value}")
            if option and bullets:
                blocks.append(f"**{option}**\n" + "\n".join(bullets))
        if blocks:
            return "\n\n".join(blocks)

    # Two-column tables such as Pros/Cons.
    for col_idx, header in enumerate(headers):
        bullets = []
        for row in data_rows:
            if len(row) <= col_idx:
                continue
            value = row[col_idx].strip()
            if value:
                bullets.append(f"- {value}")
        if header and bullets:
            blocks.append(f"**{header}**\n" + "\n".join(bullets))
    return "\n\n".join(blocks)


def _parse_markdown_table(text: str) -> List[List[str]]:
    table_lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|") and "|" in line[1:-1]):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and all(_is_separator_cell(c) for c in cells):
            continue
        table_lines.append(cells)
    return table_lines


def _is_separator_cell(cell: str) -> bool:
    compact = cell.replace(":", "").replace("-", "").strip()
    return compact == ""


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
