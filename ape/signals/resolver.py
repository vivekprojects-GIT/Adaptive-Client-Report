"""
Signal resolution — merge UI and LLM signals into one resolved signal.

When multiple signals fire (user clicks thumbs_up AND copies AND the LLM
detects a deeper_question), we apply a priority ladder so the bandit gets
exactly ONE verdict per turn. The audit log preserves ALL signals fired
for later analysis.

Resolution rules:
  1. UI signals > LLM signals (a real click is more reliable than text inference)
  2. Among UI signals: priority ladder (negatives outrank positives;
     most-explicit outranks least-explicit)
  3. If no signals fired at all: "no_signal"
"""

from __future__ import annotations

from typing import Dict, Optional


# Priority ladder for UI signals — lower index = higher priority.
# Rationale:
#   regenerate_click > session_abandon > thumbs_down  (negatives first)
#   thumbs_up > copy_save                              (explicit before implicit positive)
UI_SIGNAL_PRIORITY = [
    "regenerate_click",
    "session_abandon",
    "thumbs_down",
    "thumbs_up",
    "copy_save",
]


def resolve_ui_signal(ui_signals: Optional[Dict[str, int]]) -> Optional[str]:
    """Pick the highest-priority UI signal that fired (value=1).

    Returns the signal name, or None if no UI signal fired.
    """
    if not ui_signals:
        return None
    for name in UI_SIGNAL_PRIORITY:
        if int(ui_signals.get(name, 0)) == 1:
            return name
    return None


def resolve_signal(
    ui_signals: Optional[Dict[str, int]],
    llm_signal: Optional[str],
) -> str:
    """Final signal resolution: UI wins over LLM; fall back to "no_signal".

    The returned signal is what gets fed to SIGNAL_ROUTING + REWARD_SCALE
    to compute the actual reward.
    """
    ui = resolve_ui_signal(ui_signals)
    return ui or llm_signal or "no_signal"
