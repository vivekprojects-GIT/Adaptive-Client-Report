"""Live Thompson parameters, read from the admin-editable config document.

One document governs both decisions:

    {entity_type: "bandit_config", entity_id: "thompson",
     prior_strength_d1: 4.0, prior_strength_d2: 2.0}

D1's prior strength is how many pseudo-observations the template's declared
style-fit is worth — bigger trusts the declaration longer before real
rewards outvote it. D2's is the same idea for answer strategies, kept
smaller because a declared "fit" for an answer format is a much weaker
claim than one for a whole report template.

Reads go through a short TTL cache: selection happens on every report
generation and every chat turn, and a Mongo round-trip per Beta draw would
put Atlas latency inside the request path for a value that changes at
most a few times a day. Failure of any kind falls back to the defaults —
selection must never break because config is unreachable.
"""

from __future__ import annotations

import time
from typing import Dict

DEFAULTS: Dict[str, float] = {
    "prior_strength_d1": 4.0,
    "prior_strength_d2": 2.0,
}

_TTL_SECONDS = 30.0
_cache: Dict[str, float] = {}
_cached_at = 0.0


def thompson_params(force: bool = False) -> Dict[str, float]:
    global _cache, _cached_at
    if not force and _cache and time.time() - _cached_at < _TTL_SECONDS:
        return _cache
    values = dict(DEFAULTS)
    try:
        from ape import api as _api
        doc = _api.STORE.db["ape_config"].find_one(
            {"entity_type": "bandit_config", "entity_id": "thompson"}) or {}
        for k in DEFAULTS:
            if isinstance(doc.get(k), (int, float)) and doc[k] > 0:
                values[k] = float(doc[k])
    except Exception:
        pass
    _cache, _cached_at = values, time.time()
    return values


def invalidate() -> None:
    """Called by the config-update endpoint so a change applies on the very
    next selection instead of up to TTL seconds later."""
    global _cached_at
    _cached_at = 0.0
