"""The voice that answers in the chat.

WHY NOT THE BROWSER'S OWN VOICE
════════════════════════════════════════════════════════════════════════════

Voice mode first spoke through `speechSynthesis`. It is instant and free,
and it sounds like a machine reading a list. For a report about somebody's
money that is the wrong register — the written report is careful and warm,
and then a robot reads it out.

Piper is the same engine the podcasts already use, so the voice a client
hears in the chat is the voice they hear in their podcast, and both are the
voice `voices.py` chose for their language. It also runs here rather than in
the browser vendor's cloud, which keeps the answer — figures and all — on
this machine.

IS IT FAST ENOUGH TO HOLD A CONVERSATION?
────────────────────────────────────────────────────────────────────────────

Measured on this CPU: about 0.35s to synthesise 13 seconds of speech, or
roughly 40x realtime. A chat answer is two or three sentences, so the client
waits a fraction of a second — under the delay that makes an interface feel
broken, and far under the several seconds the podcast MCP takes for the same
work over the network.

The first call for a given language pays two one-off costs: downloading the
voice (a few seconds, once per machine) and loading it into memory (about
1.5s, once per process). Both are cached below.

MEMORY IS THE REAL LIMIT
────────────────────────────────────────────────────────────────────────────

Each loaded voice holds tens of megabytes. A server that answered in twenty
languages would keep twenty of them alive, so the cache is bounded and
evicts the least recently used. Two is enough for the common case — a client
speaking their own language, and English — and the cost of a miss is a
reload, not a failure.
"""

from __future__ import annotations

import io
import os
import threading
import time
import wave
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Tuple

# How many piper voices stay resident. Each is tens of MB.
MAX_VOICES = int(os.getenv("APE_TTS_CACHE", "2"))

# Long answers are not read aloud in full: past a point the client wants to
# read, not listen, and a two-minute monologue cannot be interrupted.
MAX_CHARS = int(os.getenv("APE_TTS_MAX_CHARS", "900"))

_VOICE_DIR = Path(os.getenv(
    "APE_PIPER_DIR", str(Path.home() / ".cache" / "piper")))

_cache: "OrderedDict[str, object]" = OrderedDict()
_lock = threading.Lock()


class SpeechError(RuntimeError):
    """The answer could not be spoken."""


def _log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass


def _load(voice_name: str):
    """Load a piper voice, downloading it once if this machine lacks it."""
    with _lock:
        if voice_name in _cache:
            _cache.move_to_end(voice_name)
            return _cache[voice_name]

        try:
            from piper import PiperVoice
            from piper.download_voices import download_voice
        except ImportError as exc:
            raise SpeechError(
                "piper-tts is not installed. Run: pip install piper-tts"
            ) from exc

        _VOICE_DIR.mkdir(parents=True, exist_ok=True)
        onnx = _VOICE_DIR / (voice_name + ".onnx")
        if not onnx.is_file():
            t0 = time.time()
            try:
                download_voice(voice_name, _VOICE_DIR)
            except Exception as exc:
                raise SpeechError(
                    f"could not fetch voice {voice_name}: {type(exc).__name__}"
                ) from exc
            _log(f"[tts] downloaded {voice_name} in {time.time() - t0:.1f}s")

        t0 = time.time()
        try:
            voice = PiperVoice.load(str(onnx))
        except Exception as exc:
            raise SpeechError(
                f"could not load voice {voice_name}: {type(exc).__name__}"
            ) from exc
        _log(f"[tts] loaded {voice_name} in {time.time() - t0:.1f}s")

        _cache[voice_name] = voice
        while len(_cache) > MAX_VOICES:
            old, _ = _cache.popitem(last=False)
            _log(f"[tts] evicted {old}")
        return voice


def clean_for_speech(text: str) -> str:
    """Strip what reads badly aloud.

    Markdown is written to be seen. Read out, an asterisk becomes a pause in
    the wrong place and a hash becomes nothing at all, so the emphasis the
    author intended lands as a stumble.
    """
    import re
    out = str(text or "")
    out = re.sub(r"```.*?```", " ", out, flags=re.S)     # code fences
    out = re.sub(r"[*_`#>|]", " ", out)                  # inline marks
    out = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", out)   # links keep the words
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) > MAX_CHARS:
        # Cut at a sentence end so the voice stops somewhere deliberate
        # rather than mid-clause.
        cut = out[:MAX_CHARS]
        stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        out = cut[:stop + 1] if stop > MAX_CHARS // 2 else cut
    return out


def synthesize(text: str, language: str = "en") -> Tuple[bytes, str]:
    """Speak `text` in `language`. Returns (wav_bytes, voice_name).

    The voice comes from the same table the podcast uses, so a client hears
    one voice across their whole report rather than a different one per
    feature.
    """
    said = clean_for_speech(text)
    if not said:
        raise SpeechError("nothing to say")

    from .voices import narrator
    voice_name = narrator(language)
    voice = _load(voice_name)

    t0 = time.time()
    buf = io.BytesIO()
    try:
        with wave.open(buf, "wb") as w:
            voice.synthesize_wav(said, w)
    except Exception as exc:
        raise SpeechError(
            f"synthesis failed: {type(exc).__name__}") from exc

    data = buf.getvalue()
    _log(f"[tts] {voice_name} {len(said)} chars -> {len(data)}B "
         f"in {time.time() - t0:.2f}s")
    return data, voice_name


def warm(language: str = "en") -> bool:
    """Load a voice ahead of the first client so nobody waits for it."""
    try:
        from .voices import narrator
        _load(narrator(language))
        return True
    except Exception as exc:
        _log(f"[tts] warm failed: {type(exc).__name__}: {exc}")
        return False
