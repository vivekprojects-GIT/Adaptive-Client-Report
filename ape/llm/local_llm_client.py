"""
LocalLLMClient — Anthropic-SDK-compatible facade over a small self-hosted
chat LLM (default: TinyLlama/TinyLlama-1.1B-Chat-v1.0) via transformers.

The rest of the codebase calls:
    client.messages.create(model=..., max_tokens=..., system=..., messages=[...])
        -> response with .content = [block] where block.type == "text", block.text
    with client.messages.stream(...) as stream:
        for chunk in stream.text_stream: ...

This module re-implements exactly that surface so classifier.py /
synthesizer.py / orchestrator.py work unchanged with a local model — no API
key, no network calls at inference time.

Reality check (the tradeoff you accepted): a 1.1B model on CPU is slow
(~seconds to a minute per answer) and far weaker than Claude at honoring the
strict JSON contracts the classifier/synthesizer expect. The lenient parsers
already fall back gracefully, but expect noisier classification.

The model is loaded ONCE (lazily, cached on the singleton) — never per
request. Set LOCAL_LLM_MODEL to override the model id.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, Generator, List, Optional

DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# CPU generation is expensive; cap new tokens so a stray max_tokens=1500 from
# the synthesizer doesn't turn into a multi-minute wait. Override via env.
MAX_NEW_TOKENS_CAP = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "512"))


# ─── Anthropic-shaped response objects ───────────────────────────────────────

class _TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


# ─── lazy, process-global model load ─────────────────────────────────────────

_MODEL = None
_TOKENIZER = None
_LOAD_LOCK = threading.Lock()


def _ensure_loaded(model_id: str):
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        with _LOAD_LOCK:
            if _MODEL is None:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer

                tok = AutoTokenizer.from_pretrained(model_id)
                model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=torch.float32,   # CPU-safe
                    low_cpu_mem_usage=True,
                )
                model.eval()
                _TOKENIZER = tok
                _MODEL = model
    return _MODEL, _TOKENIZER


def _build_prompt(tokenizer, system: Optional[str], messages: List[Dict[str, str]]) -> str:
    """Render system + messages with the model's chat template."""
    chat: List[Dict[str, str]] = []
    if system:
        chat.append({"role": "system", "content": system})
    chat.extend({"role": m["role"], "content": m["content"]} for m in messages)
    try:
        return tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        # Fallback to the Zephyr/TinyLlama format if no chat_template is present
        parts: List[str] = []
        if system:
            parts.append(f"<|system|>\n{system}</s>")
        for m in messages:
            tag = "user" if m["role"] == "user" else "assistant"
            parts.append(f"<|{tag}|>\n{m['content']}</s>")
        parts.append("<|assistant|>")
        return "\n".join(parts)


# ─── Messages API facade ─────────────────────────────────────────────────────

class _StreamContext:
    """Mimics `with client.messages.stream(...) as s: for t in s.text_stream`."""

    def __init__(self, streamer, thread) -> None:
        self._streamer = streamer
        self._thread = thread

    def __enter__(self) -> "_StreamContext":
        return self

    def __exit__(self, *exc: Any) -> None:
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass

    @property
    def text_stream(self) -> Generator[str, None, None]:
        for token in self._streamer:
            if token:
                yield token


class _Messages:
    def __init__(self, client: "LocalLLMClient") -> None:
        self._client = client

    def _gen_kwargs(self, max_tokens: int) -> Dict[str, Any]:
        return {
            "max_new_tokens": min(int(max_tokens), MAX_NEW_TOKENS_CAP),
            "do_sample": self._client.temperature > 0,
            "temperature": max(self._client.temperature, 1e-3),
            "top_p": self._client.top_p,
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
        import torch

        m, tok = _ensure_loaded(self._client.model)
        prompt = _build_prompt(tok, system, messages)
        inputs = tok(prompt, return_tensors="pt")
        with torch.no_grad():
            out = m.generate(
                **inputs,
                pad_token_id=tok.eos_token_id,
                **self._gen_kwargs(max_tokens),
            )
        gen = out[0][inputs["input_ids"].shape[1]:]
        text = tok.decode(gen, skip_special_tokens=True).strip()
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
        import torch
        from transformers import TextIteratorStreamer

        m, tok = _ensure_loaded(self._client.model)
        prompt = _build_prompt(tok, system, messages)
        inputs = tok(prompt, return_tensors="pt")
        streamer = TextIteratorStreamer(
            tok, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = dict(
            **inputs,
            streamer=streamer,
            pad_token_id=tok.eos_token_id,
            **self._gen_kwargs(max_tokens),
        )

        def _run():
            with torch.no_grad():
                m.generate(**gen_kwargs)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return _StreamContext(streamer, thread)


class LocalLLMClient:
    """Drop-in replacement for anthropic.Anthropic backed by a local model."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        top_p: float = 0.95,
        preload: bool = False,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.top_p = top_p
        self.messages = _Messages(self)
        if preload:
            _ensure_loaded(self.model)
