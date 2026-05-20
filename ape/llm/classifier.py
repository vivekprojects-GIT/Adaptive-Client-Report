"""
Classifier LLM call — single call that extracts intent + topic + signal.

The classifier reads the new user message in context of the previous
assistant response and returns one JSON object. We normalize its output
to a closed vocabulary so the rest of the system never sees a hallucinated
label.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import anthropic

from ..rag.corpus import RAG_DOMAINS
from ..signals import canonicalize_topic, canonicalize_topic_for_domain, LLM_EMITTABLE_SIGNALS
from ..strategies import VALID_INTENTS
from .prompts import CLASSIFIER_PROMPT

# Closed domain vocabulary: the four RAG domains plus a "general" catch-all.
VALID_DOMAINS = set(RAG_DOMAINS) | {"general"}
DEFAULT_DOMAIN = "general"

_DOMAIN_ALIASES = {
    "tech": "it", "technology": "it", "software": "it", "programming": "it",
    "computers": "it", "computing": "it", "coding": "it",
    "film": "movies", "films": "movies", "cinema": "movies", "movie": "movies",
    "tourism": "travel", "trips": "travel", "trip": "travel", "vacation": "travel",
    "sport": "cricket", "sports": "cricket",
    "none": "general", "other": "general", "unknown": "general",
}


# ---- Aliases for normalization ---------------------------------------------
_INTENT_ALIASES = {
    "decision":       "Decision",
    "recommendation": "Decision",
    "explanation":    "Explanation",
    "explain":        "Explanation",
    "comparison":     "Comparison",
    "compare":        "Comparison",
    "instructional":  "Instructional",
    "instructions":  "Instructional",
    "how_to":         "Instructional",
    "definitional":   "Definitional",
    "definition":     "Definitional",
    "define":         "Definitional",
    "evaluation":     "Evaluation",
    "validate":       "Evaluation",
    "unmapped":       "unmapped",
    "off_topic":      "unmapped",
}

_SIGNAL_ALIASES = {
    "nosignal":            "no_signal",
    "none":                "no_signal",
    "format_change":       "format_change_request",
    "reask":               "reask_same_question",
    "it_worked":           "it_worked_statement",
    "deeper":              "deeper_question",
}


def classify_and_detect(
    client: anthropic.Anthropic,
    model: str,
    query: str,
    history: List[Dict[str, str]],
    prev_format: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the combined classify + signal-detect LLM call.

    Returns a normalized dict with keys:
      intent, intent_confidence, unmapped_name, topic, signal
    """
    prev_response_text = _last_assistant_text(history) or "none"
    user_payload = (
        f"PREVIOUS_RESPONSE_FORMAT:    {prev_format or 'none'}\n"
        f"PREVIOUS_ASSISTANT_RESPONSE: {prev_response_text}\n"
        f"NEW_USER_MESSAGE:            {query}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=250,
        system=CLASSIFIER_PROMPT,
        messages=[{"role": "user", "content": user_payload}],
    )
    raw_text = _extract_text(response).strip()

    parsed = _parse_json_lenient(raw_text)
    parsed["_query"] = query  # for the heuristic-rescue in normalize
    return normalize_classifier_output(parsed)


# ----- Normalization --------------------------------------------------------

def normalize_classifier_output(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce a raw LLM classification dict into a clean closed-set payload.

    1. Map aliases / casing variants to canonical labels.
    2. Force unrecognized intents to "unmapped" with confidence 0.3.
    3. Force unrecognized signals to "no_signal".
    4. Heuristic rescue for very common phrasings ("what is X" → Definitional).
    5. Canonicalize the topic via the whitelist + alias map.
    6. Always return the same key set: intent, intent_confidence,
       unmapped_name, topic, signal.
    """
    out = dict(raw)

    # Intent normalization
    raw_intent = str(out.get("intent", "")).strip()
    normalized_intent = _INTENT_ALIASES.get(raw_intent.lower(), raw_intent)
    if normalized_intent in VALID_INTENTS:
        out["intent"] = normalized_intent
    else:
        out["intent"] = "unmapped"
        out["intent_confidence"] = 0.3

    # Signal normalization
    raw_signal = str(out.get("signal", "")).strip()
    normalized_signal = _SIGNAL_ALIASES.get(raw_signal.lower(), raw_signal)
    if normalized_signal in LLM_EMITTABLE_SIGNALS:
        out["signal"] = normalized_signal
    else:
        out["signal"] = "no_signal"

    # Heuristic rescue: "what is X" -> Definitional; "X vs Y" -> Comparison
    if out["intent"] == "unmapped":
        query_text = str(out.get("_query", "")).lower()
        if "difference between" in query_text or " vs " in query_text:
            out["intent"] = "Comparison"
            out["intent_confidence"] = max(float(out.get("intent_confidence", 0.3)), 0.7)
        elif query_text.startswith("what is") or query_text.startswith("what's") or "define " in query_text:
            out["intent"] = "Definitional"
            out["intent_confidence"] = max(float(out.get("intent_confidence", 0.3)), 0.7)

    # unmapped_name only meaningful when intent == "unmapped"
    if out.get("intent") != "unmapped":
        out["unmapped_name"] = None

    # Domain normalization → closed set (RAG domains + "general")
    raw_domain = str(out.get("domain", "")).strip().lower()
    norm_domain = _DOMAIN_ALIASES.get(raw_domain, raw_domain)
    out["domain"] = norm_domain if norm_domain in VALID_DOMAINS else DEFAULT_DOMAIN

    # Canonicalize topic — domain-aware (finance uses the whitelist; other
    # domains slugify so their topics survive as their own bandit cells).
    out["topic"] = canonicalize_topic_for_domain(out.get("topic"), out["domain"])
    out["intent_confidence"] = float(out.get("intent_confidence", 0.3))
    out.setdefault("unmapped_name", None)
    out.pop("_query", None)

    return out


# ----- Helpers --------------------------------------------------------------

def _last_assistant_text(history: List[Dict[str, str]]) -> Optional[str]:
    for m in reversed(history):
        if m.get("role") == "assistant":
            return m.get("content")
    return None


def _extract_text(response: Any) -> str:
    """Extract concatenated text from an Anthropic response object."""
    parts: List[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


def _parse_json_lenient(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction — strips code fences, finds first {...}."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: locate first {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass
    # Total failure — return a no-signal stub
    return {"intent": "unmapped", "intent_confidence": 0.3, "domain": "general", "topic": "general", "signal": "no_signal"}
