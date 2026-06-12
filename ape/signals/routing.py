"""
SIGNAL_CATALOG — the single source of truth for every signal APE knows about.

This catalog is the schema-stable backbone of the reward system. It survives
every migration stage:
  Stage 1 (now)  — hand-coded format/content strengths drive bandit reward
  Stage 2        — empirically-calibrated likelihood ratios per signal
  Stage 3        — Bayesian update with correlation discount
  Stage 4        — multi-task DNN consuming feature_id as input
  Stage 5        — off-policy reward learning

Forward-compatibility contract:
  - `feature_id` is FOREVER bound to a signal name once assigned.
  - `signal_name` never renames (analytics references the string).
  - Strengths may evolve between stages; that's the point of stages.
  - New signals are append-only with next available feature_id.
  - Deprecated signals set strengths to None but the row stays for decoding.

Each row carries 8 fields:
  signal_name         — canonical snake_case identifier
  source              — origin: "ui" | "llm" | "derived" | "composite" | "default"
  format_strength     — reward strength on format axis (or None = not recorded)
  content_strength    — reward strength on content axis (or None)
  feature_id          — stable integer for ML feature encoding (never reuse)
  expected_frequency  — "common" | "moderate" | "rare" (for sanity checks)
  evidence_quality    — "high" | "medium" | "low" (Stage 2 priors)
  consumers           — list of downstream systems that read this signal

Plus, for composites only:
  trigger_pattern     — human-readable description of detection rule
  time_window_sec     — max age of pattern (None = same-response only)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ============================================================================
# SIGNAL CATALOG — all 25 signals (15 atomic + 10 composite)
# ============================================================================

SIGNAL_CATALOG: Dict[str, Dict] = {

    # ── Default / null ─────────────────────────────────────────────────────
    "no_signal": {
        "source":             "default",
        "format_strength":    None,
        "content_strength":   None,
        "feature_id":         0,
        "expected_frequency": "common",
        "evidence_quality":   None,
        "consumers":          ["analytics"],
    },

    # ── Channel 1: Explicit format feedback (LLM-detected text) ────────────
    "format_change_request": {
        "source":             "llm",
        "format_strength":    "explicit_negative",
        "content_strength":   None,
        "feature_id":         1,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "instruction_quality"],
    },
    "format_keep_request": {
        "source":             "llm",
        "format_strength":    "explicit_positive",
        "content_strength":   None,
        "feature_id":         2,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit"],
    },

    # ── Channel 2: Objective format measurement (derived, automatic) ───────
    "format_compliance_pass": {
        "source":             "derived",
        "format_strength":    "inferred_positive",
        "content_strength":   None,
        "feature_id":         3,
        "expected_frequency": "common",
        "evidence_quality":   "medium",
        "consumers":          ["bandit"],
    },
    "format_compliance_fail": {
        "source":             "derived",
        "format_strength":    "inferred_negative",
        "content_strength":   None,
        "feature_id":         4,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["bandit", "instruction_quality"],
    },

    # ── Channel 3: Behavioral format evidence (UI actions) ─────────────────
    "copy_save": {
        "source":             "ui",
        "format_strength":    "inferred_positive",
        "content_strength":   "inferred_positive",
        "feature_id":         5,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["bandit", "analytics"],
    },
    "regenerate_click": {
        "source":             "ui",
        "format_strength":    "inferred_negative",
        "content_strength":   "inferred_negative",
        "feature_id":         6,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["bandit", "analytics"],
    },

    # ── Channel 4: Session continuity (derived lifecycle) ──────────────────
    "session_continue": {
        "source":             "derived",
        "format_strength":    "inferred_positive",
        "content_strength":   "inferred_positive",
        "feature_id":         7,
        "expected_frequency": "common",
        "evidence_quality":   "low",
        "consumers":          ["bandit", "retention"],
    },
    "session_abandon": {
        "source":             "derived",
        "format_strength":    "inferred_negative",
        "content_strength":   "inferred_negative",
        "feature_id":         8,
        "expected_frequency": "rare",
        "evidence_quality":   "low",
        "consumers":          ["bandit", "retention"],
    },

    # ── Channel 5: Content quality (LLM text — does NOT update bandit) ─────
    "content_correction": {
        "source":             "llm",
        "format_strength":    None,
        "content_strength":   "explicit_negative",
        "feature_id":         9,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["instruction_quality"],
    },
    "reask_same_question": {
        "source":             "llm",
        "format_strength":    None,
        "content_strength":   "inferred_negative",
        "feature_id":         10,
        "expected_frequency": "rare",
        "evidence_quality":   "medium",
        "consumers":          ["instruction_quality"],
    },
    "it_worked_statement": {
        "source":             "llm",
        "format_strength":    None,
        "content_strength":   "inferred_positive",
        "feature_id":         11,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["analytics"],
    },
    "deeper_question": {
        "source":             "llm",
        "format_strength":    None,
        "content_strength":   "inferred_positive",
        "feature_id":         12,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["analytics", "engagement"],
    },

    # ── Channel 6: Overall satisfaction (UI) ───────────────────────────────
    # Per APE_Reward_Computation.docx (ported from vg_mvp_v1.0): a thumb is
    # EXPLICIT evidence about content (±2) but only INFERRED valence on the
    # format axis (±1) — the user reacted to the answer overall, not its shape.
    # No cross-axis contamination: the format axis never gets the full ±2.
    "thumbs_up": {
        "source":             "ui",
        "format_strength":    "inferred_positive",   # F +1 (weak)
        "content_strength":   "explicit_positive",   # C +2
        "feature_id":         13,
        "expected_frequency": "moderate",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "analytics", "retention", "nps"],
    },
    "thumbs_down": {
        "source":             "ui",
        "format_strength":    "inferred_negative",   # F -1 (weak)
        "content_strength":   "explicit_negative",   # C -2
        "feature_id":         14,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "analytics", "retention", "nps"],
    },

    # ── Channel 8: Composite patterns (multi-signal combinations) ──────────
    "pattern_explicit_format_consensus_neg": {
        "source":             "composite",
        "format_strength":    "explicit_negative",
        "content_strength":   None,
        "feature_id":         15,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "instruction_quality"],
        "trigger_pattern":    "format_change_request AND (regenerate_click OR thumbs_down)",
        "time_window_sec":    None,
    },
    "pattern_explicit_format_consensus_pos": {
        "source":             "composite",
        "format_strength":    "explicit_positive",
        "content_strength":   None,
        "feature_id":         16,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit"],
        "trigger_pattern":    "format_keep_request AND (copy_save OR session_continue)",
        "time_window_sec":    None,
    },
    "pattern_engaged_positive": {
        "source":             "composite",
        "format_strength":    "inferred_positive",
        "content_strength":   "inferred_positive",
        "feature_id":         17,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["bandit", "analytics"],
        "trigger_pattern":    "≥3 positive atomic signals on same response",
        "time_window_sec":    None,
    },
    "pattern_confused_negative": {
        "source":             "composite",
        "format_strength":    "inferred_negative",
        "content_strength":   "inferred_negative",
        "feature_id":         18,
        "expected_frequency": "rare",
        "evidence_quality":   "medium",
        "consumers":          ["bandit", "instruction_quality"],
        "trigger_pattern":    "regenerate_click AND reask_same_question",
        "time_window_sec":    None,
    },
    "pattern_regret": {
        "source":             "composite",
        "format_strength":    "inferred_negative",
        "content_strength":   "inferred_negative",
        "feature_id":         19,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["bandit", "retention"],
        "trigger_pattern":    "thumbs_up THEN regenerate_click (sequence)",
        "time_window_sec":    60,
    },
    "pattern_change_of_heart": {
        "source":             "composite",
        "format_strength":    None,
        "content_strength":   None,
        "feature_id":         20,
        "expected_frequency": "rare",
        "evidence_quality":   "low",
        "consumers":          ["analytics"],
        "trigger_pattern":    "thumbs_down THEN thumbs_up (sequence)",
        "time_window_sec":    60,
    },
    "pattern_abandoned_after_approval": {
        "source":             "composite",
        "format_strength":    "inferred_negative",
        "content_strength":   "inferred_negative",
        "feature_id":         21,
        "expected_frequency": "rare",
        "evidence_quality":   "low",
        "consumers":          ["bandit", "retention"],
        "trigger_pattern":    "thumbs_up THEN session_abandon (sequence)",
        "time_window_sec":    120,
    },
    "pattern_content_failure_confirmed": {
        "source":             "composite",
        "format_strength":    None,
        "content_strength":   "explicit_negative",
        "feature_id":         22,
        "expected_frequency": "rare",
        "evidence_quality":   "high",
        "consumers":          ["instruction_quality"],
        "trigger_pattern":    "content_correction AND (regenerate_click OR thumbs_down)",
        "time_window_sec":    None,
    },
    "pattern_format_endorsed_through_behavior": {
        "source":             "composite",
        "format_strength":    "inferred_positive",
        "content_strength":   None,
        "feature_id":         23,
        "expected_frequency": "moderate",
        "evidence_quality":   "medium",
        "consumers":          ["bandit"],
        "trigger_pattern":    "copy_save AND session_continue",
        "time_window_sec":    90,
    },
    "pattern_silent_acceptance": {
        "source":             "composite",
        "format_strength":    "inferred_positive",
        "content_strength":   "inferred_positive",
        "feature_id":         24,
        "expected_frequency": "common",
        "evidence_quality":   "low",
        "consumers":          ["bandit", "analytics"],
        "trigger_pattern":    "only session_continue (no UI, no LLM signal)",
        "time_window_sec":    120,
    },
}


# ============================================================================
# Backward-compat: SIGNAL_ROUTING — (format, content) tuple per name
# Existing code reads this; derived from SIGNAL_CATALOG so we have one source.
# ============================================================================

SIGNAL_ROUTING: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    name: (entry["format_strength"], entry["content_strength"])
    for name, entry in SIGNAL_CATALOG.items()
}


# ============================================================================
# Source-grouped sets for whitelist enforcement
# ============================================================================

LLM_EMITTABLE_SIGNALS = {
    name for name, e in SIGNAL_CATALOG.items() if e["source"] == "llm"
}
UI_ONLY_SIGNALS = {
    name for name, e in SIGNAL_CATALOG.items() if e["source"] == "ui"
}
DERIVED_SIGNALS = {
    name for name, e in SIGNAL_CATALOG.items() if e["source"] == "derived"
}
COMPOSITE_SIGNALS = {
    name for name, e in SIGNAL_CATALOG.items() if e["source"] == "composite"
}


# ============================================================================
# Priority order for composite detection (Tier 1 = highest priority)
# Used at finalize-time to pick which composite "wins" if several match.
# ============================================================================

COMPOSITE_PRIORITY: List[str] = [
    # Tier 1 — Axis-explicit consensus (strongest evidence)
    "pattern_explicit_format_consensus_neg",
    "pattern_explicit_format_consensus_pos",
    "pattern_content_failure_confirmed",
    # Tier 2 — Temporal mind-changes (latest action wins)
    "pattern_regret",
    "pattern_change_of_heart",
    "pattern_abandoned_after_approval",
    # Tier 3 — Behavioral consensus
    "pattern_format_endorsed_through_behavior",
    "pattern_confused_negative",
    # Tier 4 — Weak consensus / catch-alls
    "pattern_engaged_positive",
    "pattern_silent_acceptance",
]
