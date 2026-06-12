"""
NvidiaClient — Anthropic-SDK-compatible facade over NVIDIA NIM's
OpenAI-style /chat/completions endpoint (integrate.api.nvidia.com).

The rest of the codebase calls:
    client.messages.create(model=..., max_tokens=..., system=..., messages=[...])
        -> response with .content = [block] where block.type == "text", block.text
    client.messages.stream(...) as stream:
        for chunk in stream.text_stream: ...

This module re-implements exactly that surface so classifier.py /
synthesizer.py / orchestrator.py work unchanged with the NVIDIA backend
(default model: minimaxai/minimax-m3).

Reasoning-model handling:
  - minimax-m3 emits chain-of-thought either as a separate
    `reasoning_content` delta field or inline inside <think>...</think>
    tags. Both are stripped: the caller only ever sees the final answer.
  - Reasoning burns completion tokens BEFORE the answer appears, so tiny
    caller budgets (the classifier asks for 250) would yield an empty
    answer. We enforce a floor of MIN_COMPLETION_TOKENS on every call.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Generator, Iterator, List, Optional

import requests

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "minimaxai/minimax-m3"

# Reasoning models think before answering; never let a small caller budget
# truncate the stream mid-thought (the answer would be empty).
MIN_COMPLETION_TOKENS = 8192

REQUEST_TIMEOUT_SEC = 180


# ─── Anthropic-shaped response objects ───────────────────────────────────────

class _TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


# ─── <think> tag filter ──────────────────────────────────────────────────────

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


def strip_think(text: str) -> str:
    """Remove every <think>...</think> block from a complete string."""
    out: List[str] = []
    i = 0
    while True:
        start = text.find(_THINK_OPEN, i)
        if start == -1:
            out.append(text[i:])
            break
        out.append(text[i:start])
        end = text.find(_THINK_CLOSE, start)
        if end == -1:
            # Unterminated think block — drop the rest.
            break
        i = end + len(_THINK_CLOSE)
    return "".join(out)


class _ThinkFilter:
    """Incremental <think>-block filter for streaming chunks.

    Feed it raw text chunks; it returns only the visible (non-reasoning)
    text. Handles tags split across chunk boundaries by holding back a
    small tail buffer.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._inside = False

    def feed(self, chunk: str) -> str:
        self._buf += chunk
        visible: List[str] = []
        while True:
            if self._inside:
                end = self._buf.find(_THINK_CLOSE)
                if end == -1:
                    # Still thinking — drop everything except a tail that
                    # could be the start of the close tag.
                    self._buf = self._buf[-(len(_THINK_CLOSE) - 1):]
                    break
                self._buf = self._buf[end + len(_THINK_CLOSE):]
                self._inside = False
            else:
                start = self._buf.find(_THINK_OPEN)
                if start == -1:
                    # Emit everything except the last keep chars — they
                    # might be the beginning of a split "<think>" tag.
                    keep = len(_THINK_OPEN) - 1
                    safe = self._buf[:-keep] if len(self._buf) > keep else ""
                    visible.append(safe)
                    self._buf = self._buf[len(safe):]
                    break
                visible.append(self._buf[:start])
                self._buf = self._buf[start + len(_THINK_OPEN):]
                self._inside = True
        return "".join(visible)

    def flush(self) -> str:
        """Return whatever visible text is still buffered (stream ended)."""
        if self._inside:
            self._buf = ""
            return ""
        out, self._buf = self._buf, ""
        return out


# ─── Messages API facade ─────────────────────────────────────────────────────

class _StreamContext:
    """Mimics `with client.messages.stream(...) as s: for t in s.text_stream`."""

    def __init__(self, response: requests.Response) -> None:
        self._response = response

    def __enter__(self) -> "_StreamContext":
        return self

    def __exit__(self, *exc: Any) -> None:
        self._response.close()

    @property
    def text_stream(self) -> Generator[str, None, None]:
        think = _ThinkFilter()
        for line in self._response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8") if isinstance(line, bytes) else line
            if not decoded.startswith("data:"):
                continue
            data = decoded[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            # `reasoning_content` is chain-of-thought — never surface it.
            chunk = delta.get("content")
            if not chunk:
                continue
            visible = think.feed(chunk)
            if visible:
                yield visible
        tail = think.flush()
        if tail:
            yield tail


class _Messages:
    def __init__(self, client: "NvidiaClient") -> None:
        self._client = client

    # -- shared payload builder ------------------------------------------
    def _payload(
        self,
        model: str,
        max_tokens: int,
        system: Optional[str],
        messages: List[Dict[str, str]],
        stream: bool,
    ) -> Dict[str, Any]:
        full_messages: List[Dict[str, str]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)
        return {
            "model": model or self._client.model,
            "messages": full_messages,
            "max_tokens": max(int(max_tokens), MIN_COMPLETION_TOKENS),
            "temperature": self._client.temperature,
            "top_p": self._client.top_p,
            "stream": stream,
        }

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: Optional[str] = None,
        messages: List[Dict[str, str]],
        **_: Any,
    ) -> _Response:
        resp = requests.post(
            self._client.invoke_url,
            headers=self._client._headers(stream=False),
            json=self._payload(model, max_tokens, system, messages, stream=False),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        body = resp.json()
        choices = body.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        text = strip_think(message.get("content") or "").strip()
        return _Response(text)

    def stream(
        self,
        *,
        model: str,
        max_tokens: int,
        system: Optional[str] = None,
        messages: List[Dict[str, str]],
        **_: Any,
    ) -> _StreamContext:
        resp = requests.post(
            self._client.invoke_url,
            headers=self._client._headers(stream=True),
            json=self._payload(model, max_tokens, system, messages, stream=True),
            timeout=REQUEST_TIMEOUT_SEC,
            stream=True,
        )
        resp.raise_for_status()
        return _StreamContext(resp)


class NvidiaClient:
    """Drop-in replacement for anthropic.Anthropic backed by NVIDIA NIM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        temperature: float = 1.0,
        top_p: float = 0.95,
    ) -> None:
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is required")
        self.invoke_url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.messages = _Messages(self)

    def _headers(self, stream: bool) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
            "Content-Type": "application/json",
        }
