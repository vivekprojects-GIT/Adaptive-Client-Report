"""
REWARD_SCALE — strength label -> normalized reward value (float in [-1, +1]).

Single source of truth. Bandit math consumes this directly; no `raw_reward`
companion field. `None` means NOT_RECORDED on that axis.

Design:
  - Bounded range [-1.0, +1.0] required for UCB confidence-bound math
  - Symmetric magnitudes avoid baking in positivity/negativity bias
  - 2:1 strong:weak ratio — one explicit signal worth two implicit ones
"""

from __future__ import annotations

from typing import Dict, Optional


REWARD_SCALE: Dict[Optional[str], Optional[float]] = {
    "strong_positive": +1.0,
    "weak_positive":   +0.5,
    "weak_negative":   -0.5,
    "strong_negative": -1.0,
    None:              None,    # NOT_RECORDED — counter is not bumped
}
