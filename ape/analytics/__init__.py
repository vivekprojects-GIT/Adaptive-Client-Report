"""Analytics package — aggregates from ape_turn_record into business-friendly stores."""

from .compute import (
    compute_user_topic_interest,
    compute_topic_trends,
    recompute_all,
)
from .recommender import (
    eligible_offers_for_user,
)
from .facets import (
    compute_cognitive_facets,
)
from .active_users import (
    active_users_in_window,
)
from .user_profile import (
    compute_user_cognitive_profile,
)
from .platform import (
    compute_platform_overview,
)
from .strategy_performance import (
    compute_strategy_performance,
)
from .instruction_quality import (
    compute_instruction_quality,
)

__all__ = [
    "compute_user_topic_interest",
    "compute_topic_trends",
    "recompute_all",
    "eligible_offers_for_user",
    "compute_cognitive_facets",
    "active_users_in_window",
    "compute_user_cognitive_profile",
    "compute_platform_overview",
    "compute_strategy_performance",
    "compute_instruction_quality",
]
