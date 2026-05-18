"""Strategies package — the bandit's arm catalog and per-strategy instructions."""

from .catalog import INTENT_STRATEGIES, VALID_INTENTS
from .instructions import (
    STRATEGY_INSTRUCTIONS,
    FORMAT_EXPECTATIONS,
    RENDERED_FORMAT_VOCABULARY,
    compute_format_compliance,
)

__all__ = [
    "INTENT_STRATEGIES",
    "VALID_INTENTS",
    "STRATEGY_INSTRUCTIONS",
    "FORMAT_EXPECTATIONS",
    "RENDERED_FORMAT_VOCABULARY",
    "compute_format_compliance",
]
