"""
Pydantic schemas for API request and response bodies.

Identity model (per the production design):
  - user_id is required on every /turn request; the orchestrator hashes it
    to user_id_hash before any DB write.
  - session_id is OPTIONAL context — the orchestrator mints one if missing.
  - response_id is returned with every /turn response. The client must
    send this back on /feedback to target the exact response being rated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------------
# /turn
# ----------------------------------------------------------------------------

class TurnRequest(BaseModel):
    """The client no longer sends conversation history — the server reads it
    from MongoDB based on session_id. Just send the new query.
    """
    user_id:           str = Field(..., min_length=1)
    session_id:        Optional[str] = None
    query:             str = Field(..., min_length=1)
    generate_response: bool = True


class TurnResponse(BaseModel):
    response_id:           str
    session_id:            str
    assistant_message_id:  str
    classification:        Dict[str, Any]
    selection:             Dict[str, Any]
    answer:                str
    rendered_format:       str
    timings_ms:            Optional[Dict[str, float]] = None


# ----------------------------------------------------------------------------
# Conversation history
# ----------------------------------------------------------------------------

class ChatMessage(BaseModel):
    message_id:      str
    role:            str
    content:         str
    ts:              str
    response_id:     Optional[str] = None
    rendered_format: Optional[str] = None
    meta:            Optional[Dict[str, Any]] = None


class SessionSummary(BaseModel):
    session_id:           str
    started_at:           Optional[str] = None
    last_active_at:       Optional[str] = None
    message_count:        int = 0
    first_user_message:   Optional[str] = None


# ----------------------------------------------------------------------------
# /feedback
# ----------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    """Explicit UI feedback targeting an exact response_id.

    Per the design: response_id is REQUIRED. session_id alone is not enough
    to identify which response gets the reward.
    """
    user_id:     str = Field(..., min_length=1)
    response_id: str = Field(..., min_length=1)
    signal:      str = Field(..., min_length=1)


class FeedbackResponse(BaseModel):
    status:              str
    response_id:         Optional[str] = None
    signal:              Optional[str] = None
    # FORMAT axis — what the bandit consumed (explicit ±2 / inferred ±1)
    reward_category:     Optional[str] = None
    normalized_reward:   Optional[float] = None
    # CONTENT axis — recorded for display/analytics, not consumed by the bandit
    content_category:    Optional[str] = None
    content_reward:      Optional[float] = None
    reason:              Optional[str] = None
    strategy_row_after:  Optional[Dict[str, Any]] = None
    current_status:      Optional[str] = None


# ----------------------------------------------------------------------------
# Admin / config endpoints
# ----------------------------------------------------------------------------

class SignalRuleUpdate(BaseModel):
    signal_name:        str
    format_relevant:    bool
    content_relevant:   bool
    format_category:    Optional[str] = None
    content_category:   Optional[str] = None
    # Extended catalog fields (Stage 1+). All optional for back-compat.
    source:             Optional[str] = None              # ui | llm | derived | composite | default
    feature_id:         Optional[int] = None              # stable ML-feature integer
    expected_frequency: Optional[str] = None              # common | moderate | rare
    evidence_quality:   Optional[str] = None              # high | medium | low
    consumers:          Optional[List[str]] = None        # bandit | analytics | ...
    trigger_pattern:    Optional[str] = None              # composite-only, free text
    time_window_sec:    Optional[int] = None              # composite-only, None=same response
    changed_by:         str = "admin_user"


class RewardScaleUpdate(BaseModel):
    category:          str
    normalized_reward: float
    changed_by:        str = "admin_user"


class PolicyUpsert(BaseModel):
    domain:               str
    intent:               str
    topic:                str
    strategy_id:          str
    policy_version:       str = "v1"
    exploration_constant: float = 1.0
    changed_by:           str = "admin_user"


class InstructionPublish(BaseModel):
    strategy_id:      str
    version:          str
    instruction_text: str
    instruction_uri:  Optional[str] = None
    activate:         bool = False
    changed_by:       str = "admin_user"


class IntentUpsert(BaseModel):
    intent_id:   str
    description: str = ""
    changed_by:  str = "admin_user"


class StrategyUpsert(BaseModel):
    strategy_id: str
    format_type: str = "paragraph"
    changed_by:  str = "admin_user"


class HealthResponse(BaseModel):
    status: str
