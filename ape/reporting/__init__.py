"""Adaptive client reporting — D1 (report shape) and the report pipeline."""

from .d1 import (
    DIMENSIONS,
    NotPersonalisableError,
    blend_prior,
    cell_key,
    client_scope,
    effective_profile,
    eligible_arms,
    evidence_weight,
    score_arms,
    segment_scope,
    select,
)

__all__ = [
    "DIMENSIONS", "NotPersonalisableError", "cell_key", "segment_scope",
    "client_scope", "evidence_weight", "blend_prior", "effective_profile",
    "eligible_arms", "score_arms", "select",
]
