"""Speech to text for the client chat, in whatever language was spoken.

WHY NOT THE BROWSER'S OWN RECOGNISER
════════════════════════════════════════════════════════════════════════════

The first version of the microphone used the browser's SpeechRecognition.
It works, it is free, and it has two faults that matter here.

It cannot detect a language. It transcribes according to one tag you set in
advance, so the best it can do is "dictate in the language this report is
written in". A client whose report is Dutch but who asks a question in
English gets nonsense back, because the recogniser is not translating — it
is trying to hear English sounds as Dutch words.

And in Chrome it is not local. The audio goes to Google's servers, which is
a thing worth knowing about a wealth report's chat box, and it does not
exist at all in Firefox.

Whisper solves both. It identifies the language itself from the audio, and
it runs here — the recording reaches this process and stops. Nothing about
the client's voice leaves the building, which is the same standard the rest
of the system is held to and a stronger one than the podcast renderer meets.

MODEL SIZE AND THE COST OF BEING WRONG
────────────────────────────────────────────────────────────────────────────

`tiny` by default: about 39MB, measured here at 2-3x the speed of `base`
with identical language detection on clean speech - a conversational turn
transcribes in well under a second, which is the budget a voice exchange
has before it feels broken. `base` and `small` are stronger on accented or
noisy speech; APE_WHISPER_MODEL switches without a code change.

Accuracy matters less here than it looks, because the text lands in the
question box for the client to read before they send it. A mistake is
visible and correctable. That is also why this must never send on its own.

THE SHORT-UTTERANCE PROBLEM
────────────────────────────────────────────────────────────────────────────

Language detection reads the first 30 seconds, and a two-word question does
not give it much. "Hoeveel?" is a plausible word in several languages, and a
confident-sounding wrong answer means the whole sentence is transcribed
against the wrong phonetics.

So when detection comes back unsure, the report's own language is used
instead. It is the best prior available: this client was sent a report in
that language, which is a real signal about what they speak. A second pass
on a few seconds of audio is cheap, and being right matters more.
"""

from __future__ import annotations

import io
import os
import threading
import time
from typing import Optional, Tuple

# Below this, detection is treated as a guess rather than an answer. Chosen
# from observation: genuine detections on clear speech come back at 0.9+,
# while the ambiguous short ones land far below.
_CONFIDENCE_FLOOR = float(os.getenv("APE_WHISPER_MIN_CONFIDENCE", "0.55"))

# "tiny", measured against "base" on this CPU: 2-3x faster (0.7s vs 1.6s
# on a 25-second Dutch clip), identical language detection at 0.99-1.00,
# and equivalent transcripts on clean speech. The risk is accented or noisy
# speech, where base is stronger - but a voice-mode transcript is shown on
# screen before anything is sent, so a miss is visible and correctable,
# and APE_WHISPER_MODEL=base is one env var away.
MODEL_SIZE = os.getenv("APE_WHISPER_MODEL", "tiny")

# Greedy decoding. Beam search buys little on short conversational turns
# and costs up to 2x on longer ones; the visible-transcript safety net
# applies here too.
BEAM = int(os.getenv("APE_WHISPER_BEAM", "1"))

# A recording this long is not a question. The browser stops well before it,
# so this is the guard for anything that did not come from our own page.
MAX_AUDIO_BYTES = int(os.getenv("APE_WHISPER_MAX_BYTES", str(8 * 1024 * 1024)))

_model = None
# Loading takes several seconds and pulls the weights into memory once. Two
# simultaneous first-requests would otherwise both load, doubling the memory
# for no gain.
_load_lock = threading.Lock()


class TranscriptionError(RuntimeError):
    """Audio could not be turned into text."""


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _load_lock:
        if _model is not None:               # won the race while waiting
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:           # noqa: F841
            raise TranscriptionError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc
        # int8 on CPU: markedly faster, and the quality difference is not
        # audible in a transcript that a person is about to read and edit.
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio: bytes,
               fallback_language: Optional[str] = None) -> Tuple[str, str, float]:
    """Turn recorded audio into (text, language, confidence).

    `audio` is whatever the browser recorded — WebM/Opus from Chrome, MP4
    from Safari. Both are decoded in memory by PyAV, which carries its own
    ffmpeg, so no system binary has to be present.

    `fallback_language` is the report's language, used only when detection
    is not confident. Passing None disables the second pass.
    """
    if not audio:
        raise TranscriptionError("no audio received")
    if len(audio) > MAX_AUDIO_BYTES:
        raise TranscriptionError(
            f"recording too large ({len(audio)} bytes)")

    model = _get_model()
    started = time.time()

    try:
        segments, info = model.transcribe(io.BytesIO(audio), vad_filter=True,
                                          beam_size=BEAM)
        text = " ".join(s.text.strip() for s in segments).strip()
        language = info.language
        confidence = float(info.language_probability)
    except Exception as exc:
        raise TranscriptionError(
            f"could not decode audio: {type(exc).__name__}") from exc

    # Unsure, and we have a better prior than a coin flip.
    retried = False
    if (confidence < _CONFIDENCE_FLOOR and fallback_language
            and fallback_language != language):
        try:
            segments, info = model.transcribe(
                io.BytesIO(audio), language=fallback_language, vad_filter=True,
                beam_size=BEAM)
            second = " ".join(s.text.strip() for s in segments).strip()
            if second:
                text, language, retried = second, fallback_language, True
        except Exception:
            # The first pass stands. A shaky transcript the client can edit
            # beats an error for a question they did manage to ask.
            pass

    _log(f"[stt] {len(audio)}B -> {language} "
         f"({confidence:.2f}{', fell back' if retried else ''}) "
         f"in {time.time() - started:.1f}s, {len(text)} chars")
    return text, language, confidence


def _log(msg: str) -> None:
    # Same encoding-safety as the writer's logger: a transcript can contain
    # any script, and a print() that raises would take the request with it.
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass


def warm() -> bool:
    """Load the model ahead of the first client, so nobody pays for it."""
    try:
        _get_model()
        return True
    except Exception as exc:
        _log(f"[stt] warm failed: {type(exc).__name__}: {exc}")
        return False
