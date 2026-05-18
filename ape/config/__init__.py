"""Config package — admin-managed configuration in MongoDB + seed script."""

from .manager import ConfigManager
from .seed import seed_all, DEFAULT_DOMAIN

__all__ = ["ConfigManager", "seed_all", "DEFAULT_DOMAIN"]
