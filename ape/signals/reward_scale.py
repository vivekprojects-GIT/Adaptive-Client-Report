"""
REWARD_SCALE — strength label -> numeric reward value.

Maps the 5 strength categories to their integer reward values. Strong signals
are 2x weak signals. Symmetric in magnitude. `None` means NOT_RECORDED.

Design choices:
  - Integer values keep totals exact (no floating-point drift)
  - Symmetric magnitudes avoid baking in positivity/negativity bias
  - 2:1 strong:weak ratio — one explicit signal worth two implicit ones
  - Bounded range [-2, +2] keeps running means interpretable
"""

from __future__ import annotations

from typing import Dict, Optional


REWARD_SCALE: Dict[Optional[str], Optional[int]] = {
    "strong_positive": +2,
    "weak_positive":   +1,
    "weak_negative":   -1,
    "strong_negative": -2,
    None:              None,    # NOT_RECORDED — counter is not bumped
}
