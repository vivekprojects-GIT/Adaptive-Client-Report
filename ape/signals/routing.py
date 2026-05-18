"""
SIGNAL_ROUTING — maps each signal to its per-axis (relevance, strength).

This is v1 of the reward function: hand-tuned, deterministic, no ML involved.
A future learned-weight function would replace this table without touching
the rest of the system. Treat values here as MUTABLE design choices, not
constants.

Each entry is a tuple:
    (format_strength, content_strength)

Where strength is one of:
    "strong_positive" | "weak_positive" | "weak_negative" | "strong_negative" | None

`None` means NOT_RECORDED for that axis — the strategy's counter is left
exactly as it was. This is distinct from a zero reward (which would still
bump the count and pull the average toward zero).

Design rules:
  - Explicit UI actions (button clicks)          -> STRONG on both axes
  - Explicit text complaints about one axis       -> STRONG on that axis only
  - Behavioral inference (engagement, re-asking)  -> WEAK on content only
  - No evidence                                   -> NOT_RECORDED on both axes
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple


# (format_strength, content_strength)
SIGNAL_ROUTING: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    # UI button signals — explicit user actions, strong on both axes
    "thumbs_up":             ("strong_positive", "strong_positive"),
    "thumbs_down":           ("strong_negative", "strong_negative"),
    "copy_save":             ("strong_positive", "strong_positive"),
    "regenerate_click":      ("strong_negative", "strong_negative"),
    "session_abandon":       ("strong_negative", "strong_negative"),

    # Explicit text complaints — strong on the relevant axis, None on the other
    "format_change_request": ("strong_negative", None),
    "content_correction":    (None,              "strong_negative"),

    # Behavioral inferences from text — weak, content-only
    "reask_same_question":   (None,              "weak_negative"),
    "it_worked_statement":   (None,              "weak_positive"),
    "deeper_question":       (None,              "weak_positive"),

    # No information
    "no_signal":             (None,              None),
}


# Whitelist of signals the LLM classifier may emit. UI-only signals are
# never emitted by the model — they come from real button clicks or session
# lifecycle events. If the LLM hallucinates one of these, the normalizer
# coerces it to "no_signal".
LLM_EMITTABLE_SIGNALS = {
    "format_change_request",
    "content_correction",
    "reask_same_question",
    "it_worked_statement",
    "deeper_question",
    "no_signal",
}

UI_ONLY_SIGNALS = {
    "thumbs_up",
    "thumbs_down",
    "copy_save",
    "regenerate_click",
    "session_abandon",
}
