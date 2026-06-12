"""
SIGNAL_CATALOG — closed signal set per APE_Reward_Computation.docx
(exactly the vg_mvp_v1.0 catalog — 9 signals, nothing more).

Each signal maps its CONTENT and FORMAT axes to a reward tier (REWARD_SCALE):
  explicit_positive/negative = ±2   ·   inferred_positive/negative = ±1   ·   None = 0

This is the SINGLE SOURCE OF TRUTH for signal rewards. seed.py pushes this
catalog into MongoDB, where the runtime reward path and the admin
Signal-Routing UI read it — so the displayed config and the runtime reward
are always identical.

UI-emitted: thumbs_up, thumbs_down
LLM-detected: content_correction, format_change_request, format_praise_explicit,
              it_worked_statement, deeper_question, reask_same_question

Forward-compatibility contract:
  - `feature_id` is FOREVER bound to a signal name once assigned.
  - `signal_name` never renames (analytics references the string).
  - New signals are append-only with the next available feature_id.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


SIGNAL_CATALOG: Dict[str, Dict] = {
    "thumbs_up": {
        "source":             "ui",
        "format_strength":    "inferred_positive",   # F +1 (weak)
        "content_strength":   "explicit_positive",   # C +2
        "feature_id":         1,
        "expected_frequency": "moderate",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "analytics"],
    },
    "thumbs_down": {
        "source":             "ui",
        "format_strength":    "inferred_negative",   # F -1 (weak)
        "content_strength":   "explicit_negative",   # C -2
        "feature_id":         2,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "analytics"],
    },
    "content_correction": {
        "source":             "llm",
        "format_strength":    None,                  # F 0 — no format opinion
        "content_strength":   "explicit_negative",   # C -2
        "feature_id":         3,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["analytics"],
    },
    "format_change_request": {
        "source":             "llm",
        "format_strength":    "explicit_negative",   # F -2 — explicit reshape
        "content_strength":   None,                  # C 0
        "feature_id":         4,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit"],
    },
    "format_praise_explicit": {
        "source":             "llm",
        "format_strength":    "explicit_positive",   # F +2 — "the table was perfect"
        "content_strength":   None,                  # C 0
        "feature_id":         5,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit"],
    },
    "it_worked_statement": {
        "source":             "llm",
        "format_strength":    None,                  # F 0 — politeness firewall
        "content_strength":   "inferred_positive",   # C +1 (weak)
        "feature_id":         6,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["analytics"],
    },
    "deeper_question": {
        "source":             "llm",
        "format_strength":    None,                  # F 0 — politeness firewall
        "content_strength":   "inferred_positive",   # C +1 (engagement)
        "feature_id":         7,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["analytics"],
    },
    "reask_same_question": {
        "source":             "llm",
        "format_strength":    None,                  # F 0
        "content_strength":   "inferred_negative",   # C -1 — answer didn't land
        "feature_id":         8,
        "expected_frequency": "rare",
        "evidence_quality":   "medium",
        "consumers":          ["analytics"],
    },
    "no_signal": {
        "source":             "system",
        "format_strength":    None,
        "content_strength":   None,
        "feature_id":         9,
        "expected_frequency": "moderate",
        "evidence_quality":   "low",
        "consumers":          [],
    },
}


# ============================================================================
# Backward-compat: SIGNAL_ROUTING — (format, content) tuple per name
# ============================================================================

SIGNAL_ROUTING: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    name: (entry["format_strength"], entry["content_strength"])
    for name, entry in SIGNAL_CATALOG.items()
}


# ============================================================================
# Source-grouped sets
# ============================================================================

LLM_EMITTABLE_SIGNALS = {n for n, e in SIGNAL_CATALOG.items() if e["source"] == "llm"}
UI_ONLY_SIGNALS       = {n for n, e in SIGNAL_CATALOG.items() if e["source"] == "ui"}
DERIVED_SIGNALS:   set = set()
COMPOSITE_SIGNALS: set = set()
COMPOSITE_PRIORITY: List[str] = []
