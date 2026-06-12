"""
REWARD_SCALE — evidence tier -> reward value (per APE_Reward_Computation.docx,
ported from vg_mvp_v1.0).

Single source of truth for the magnitudes. SIGNAL_CATALOG (routing.py) maps each
signal's content/format axis to one of these tiers; seed.py pushes both into
MongoDB, where the runtime reward path and the admin Reward-Scale /
Signal-Routing UI read them — so the displayed config and the runtime reward
can never diverge.

Three tiers (the doc):
  Explicit evidence about an axis → full magnitude  ±2
  Inferred valence (carried over) → reduced         ±1
  No evidence about that axis     → None            (counter not bumped → 0)
"""

from __future__ import annotations

from typing import Dict, Optional


REWARD_SCALE: Dict[Optional[str], Optional[float]] = {
    "explicit_positive": +2.0,
    "explicit_negative": -2.0,
    "inferred_positive": +1.0,
    "inferred_negative": -1.0,
    None:                None,    # NOT_RECORDED — counter is not bumped
}
