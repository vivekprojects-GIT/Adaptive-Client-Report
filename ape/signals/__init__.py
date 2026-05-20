"""Signals package — signal routing, reward scale, resolution, and topic canonicalization."""

from .routing import (
    SIGNAL_CATALOG,
    SIGNAL_ROUTING,
    LLM_EMITTABLE_SIGNALS,
    UI_ONLY_SIGNALS,
    DERIVED_SIGNALS,
    COMPOSITE_SIGNALS,
    COMPOSITE_PRIORITY,
)
from .reward_scale import REWARD_SCALE
from .resolver import resolve_signal, resolve_ui_signal, UI_SIGNAL_PRIORITY
from .topic import (
    canonicalize_topic,
    canonicalize_topic_for_domain,
    slugify_topic,
    TOPIC_WHITELIST,
)

__all__ = [
    "SIGNAL_CATALOG",
    "SIGNAL_ROUTING",
    "LLM_EMITTABLE_SIGNALS",
    "UI_ONLY_SIGNALS",
    "DERIVED_SIGNALS",
    "COMPOSITE_SIGNALS",
    "COMPOSITE_PRIORITY",
    "REWARD_SCALE",
    "resolve_signal",
    "resolve_ui_signal",
    "UI_SIGNAL_PRIORITY",
    "canonicalize_topic",
    "canonicalize_topic_for_domain",
    "slugify_topic",
    "TOPIC_WHITELIST",
]
