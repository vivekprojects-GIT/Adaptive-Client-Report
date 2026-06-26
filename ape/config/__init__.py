"""Config package — admin-managed configuration in MongoDB + seed script."""

from .manager import ConfigManager
from .seed import cleanup_non_canonical_intents, cleanup_strategy_format_metadata, seed_all, DEFAULT_DOMAIN

__all__ = [
    "ConfigManager",
    "seed_all",
    "DEFAULT_DOMAIN",
    "cleanup_strategy_format_metadata",
    "cleanup_non_canonical_intents",
]
