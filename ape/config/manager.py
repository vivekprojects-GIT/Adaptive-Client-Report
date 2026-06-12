"""
ConfigManager — CRUD wrapper around ape_config that automatically logs every
change to ape_admin_audit.

All admin-facing config mutations should go through this class, never through
direct MongoStore writes. That guarantees:

  1. The before/after states are recorded for traceability.
  2. We can roll back by reading the audit log.
  3. The active version of a given entity is enforced (only one ACTIVE
     instruction version per strategy, etc.).

Usage:
    cfg = ConfigManager(store)
    cfg.update_signal_rule("thumbs_up", format_relevant=True, content_relevant=True,
                           format_category="inferred_positive",
                           content_category="explicit_positive",
                           changed_by="admin_user")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..store import (
    ENTITY_INSTRUCTION,
    ENTITY_INTENT,
    ENTITY_POLICY,
    ENTITY_REWARD_RULE,
    ENTITY_SIGNAL_RULE,
    ENTITY_STRATEGY,
    MongoStore,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
)


class ConfigManager:
    def __init__(self, store: MongoStore) -> None:
        self.store = store

    # ------------------------------------------------------------------
    # Intent management
    # ------------------------------------------------------------------
    def upsert_intent(self, intent_id: str, description: str = "", changed_by: str = "system") -> None:
        before = self.store.get_active_config(ENTITY_INTENT, intent_id)
        self.store.upsert_config(
            entity_type=ENTITY_INTENT,
            entity_id=intent_id,
            fields={"intent_id": intent_id, "description": description},
        )
        after = self.store.get_active_config(ENTITY_INTENT, intent_id)
        self.store.log_admin_action(
            action_type="UPSERT_INTENT",
            entity_type=ENTITY_INTENT,
            entity_id=intent_id,
            changed_by=changed_by,
            before=_clean(before),
            after=_clean(after),
        )

    # ------------------------------------------------------------------
    # Strategy management
    # ------------------------------------------------------------------
    def upsert_strategy(self, strategy_id: str, format_type: str, changed_by: str = "system") -> None:
        before = self.store.get_active_config(ENTITY_STRATEGY, strategy_id)
        self.store.upsert_config(
            entity_type=ENTITY_STRATEGY,
            entity_id=strategy_id,
            fields={
                "strategy_id":     strategy_id,
                "format_type":     format_type,
                "expected_format": format_type,
            },
        )
        after = self.store.get_active_config(ENTITY_STRATEGY, strategy_id)
        self.store.log_admin_action(
            action_type="UPSERT_STRATEGY",
            entity_type=ENTITY_STRATEGY,
            entity_id=strategy_id,
            changed_by=changed_by,
            before=_clean(before),
            after=_clean(after),
        )

    # ------------------------------------------------------------------
    # Instruction versioning
    # ------------------------------------------------------------------
    def publish_instruction(
        self,
        strategy_id: str,
        version: str,
        instruction_text: str,
        instruction_uri: Optional[str] = None,
        changed_by: str = "system",
    ) -> None:
        """Publish a new instruction version as DRAFT, then activate it."""
        # 1) Write the new version as DRAFT
        self.store.upsert_config(
            entity_type=ENTITY_INSTRUCTION,
            entity_id=strategy_id,
            version=version,
            fields={
                "strategy_id":      strategy_id,
                "instruction_text": instruction_text,
                "instruction_uri":  instruction_uri,
            },
            status="DRAFT",
        )
        self.store.log_admin_action(
            action_type="UPSERT_INSTRUCTION",
            entity_type=ENTITY_INSTRUCTION,
            entity_id=f"{strategy_id}:{version}",
            changed_by=changed_by,
            after={"version": version, "status": "DRAFT"},
        )

    def activate_instruction(self, strategy_id: str, version: str, changed_by: str = "system") -> None:
        # Demote currently-active version to INACTIVE
        existing_active = self.store.config.find_one({
            "entity_type": ENTITY_INSTRUCTION,
            "entity_id":   strategy_id,
            "status":      STATUS_ACTIVE,
        })
        if existing_active and existing_active.get("version") != version:
            self.store.config.update_one(
                {"_id": existing_active["_id"]},
                {"$set": {"status": STATUS_INACTIVE}},
            )
            self.store.log_admin_action(
                action_type="DEACTIVATE_INSTRUCTION",
                entity_type=ENTITY_INSTRUCTION,
                entity_id=f"{strategy_id}:{existing_active.get('version')}",
                changed_by=changed_by,
                before=_clean(existing_active),
            )

        # Promote the requested version to ACTIVE
        self.store.config.update_one(
            {
                "entity_type": ENTITY_INSTRUCTION,
                "entity_id":   strategy_id,
                "version":     version,
            },
            {"$set": {"status": STATUS_ACTIVE}},
        )
        self.store.log_admin_action(
            action_type="ACTIVATE_INSTRUCTION",
            entity_type=ENTITY_INSTRUCTION,
            entity_id=f"{strategy_id}:{version}",
            changed_by=changed_by,
            after={"version": version, "status": STATUS_ACTIVE},
        )

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------
    def upsert_policy(
        self,
        domain: str,
        intent: str,
        topic: str,
        strategy_id: str,
        policy_version: str = "v1",
        exploration_constant: float = 1.0,
        changed_by: str = "system",
    ) -> None:
        entity_id = f"{intent}#{topic}#{strategy_id}"
        before = self.store.get_active_config(ENTITY_POLICY, entity_id)
        self.store.upsert_config(
            entity_type=ENTITY_POLICY,
            entity_id=entity_id,
            fields={
                "domain":               domain,
                "intent":               intent,
                "topic":                topic,
                "strategy_id":          strategy_id,
                "policy_version":       policy_version,
                "exploration_constant": exploration_constant,
                "ucb_algorithm":        "UCB",
            },
        )
        after = self.store.get_active_config(ENTITY_POLICY, entity_id)
        self.store.log_admin_action(
            action_type="UPSERT_POLICY",
            entity_type=ENTITY_POLICY,
            entity_id=entity_id,
            changed_by=changed_by,
            before=_clean(before),
            after=_clean(after),
        )

    # ------------------------------------------------------------------
    # Signal routing
    # ------------------------------------------------------------------
    def update_signal_rule(
        self,
        signal_name: str,
        format_relevant: bool,
        content_relevant: bool,
        format_category: Optional[str],
        content_category: Optional[str],
        source: Optional[str] = None,
        feature_id: Optional[int] = None,
        expected_frequency: Optional[str] = None,
        evidence_quality: Optional[str] = None,
        consumers: Optional[list] = None,
        trigger_pattern: Optional[str] = None,
        time_window_sec: Optional[int] = None,
        changed_by: str = "system",
    ) -> None:
        before = self.store.get_signal_routing(signal_name)
        # Preserve existing extended fields if the caller didn't supply them
        # (so edits from the basic form don't clobber feature_id, etc.).
        fields = {
            "signal_name":      signal_name,
            "format_relevant":  format_relevant,
            "content_relevant": content_relevant,
            "format_category":  format_category,
            "content_category": content_category,
        }
        if source is not None:
            fields["source"] = source
        elif before is not None:
            fields["source"] = before.get("source")
        if feature_id is not None:
            fields["feature_id"] = feature_id
        elif before is not None:
            fields["feature_id"] = before.get("feature_id")
        if expected_frequency is not None:
            fields["expected_frequency"] = expected_frequency
        elif before is not None:
            fields["expected_frequency"] = before.get("expected_frequency")
        if evidence_quality is not None:
            fields["evidence_quality"] = evidence_quality
        elif before is not None:
            fields["evidence_quality"] = before.get("evidence_quality")
        if consumers is not None:
            fields["consumers"] = consumers
        elif before is not None:
            fields["consumers"] = before.get("consumers")
        # Composite-only fields
        if trigger_pattern is not None:
            fields["trigger_pattern"] = trigger_pattern
        elif before is not None and before.get("trigger_pattern") is not None:
            fields["trigger_pattern"] = before.get("trigger_pattern")
        if time_window_sec is not None:
            fields["time_window_sec"] = time_window_sec
        elif before is not None and before.get("time_window_sec") is not None:
            fields["time_window_sec"] = before.get("time_window_sec")

        self.store.upsert_config(
            entity_type=ENTITY_SIGNAL_RULE,
            entity_id=signal_name,
            fields=fields,
        )
        after = self.store.get_signal_routing(signal_name)
        self.store.log_admin_action(
            action_type="UPSERT_SIGNAL_RULE",
            entity_type=ENTITY_SIGNAL_RULE,
            entity_id=signal_name,
            changed_by=changed_by,
            before=_clean(before),
            after=_clean(after),
        )

    # ------------------------------------------------------------------
    # Reward scale
    # ------------------------------------------------------------------
    def update_reward_value(
        self,
        category: str,
        normalized_reward: float,
        changed_by: str = "system",
    ) -> None:
        before = self.store.get_reward_scale(category)
        self.store.upsert_config(
            entity_type=ENTITY_REWARD_RULE,
            entity_id=category,
            fields={
                "reward_category":   category,
                "normalized_reward": float(normalized_reward),
            },
        )
        after = self.store.get_reward_scale(category)
        self.store.log_admin_action(
            action_type="UPSERT_REWARD_VALUE",
            entity_type=ENTITY_REWARD_RULE,
            entity_id=category,
            changed_by=changed_by,
            before=_clean(before),
            after=_clean(after),
        )

    # ------------------------------------------------------------------
    # Read helpers — admin views return ALL docs (active + paused) so the
    # admin can re-activate paused ones. The runtime uses list_active_config
    # directly (NOT these methods) — see orchestrator + recommender.
    # ------------------------------------------------------------------
    def list_intents(self) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_all_config(ENTITY_INTENT)]

    def list_strategies(self) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_all_config(ENTITY_STRATEGY)]

    def list_policies(self) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_all_config(ENTITY_POLICY)]

    def list_signal_rules(self) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_all_config(ENTITY_SIGNAL_RULE)]

    def list_reward_scale(self) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_all_config(ENTITY_REWARD_RULE)]

    def list_audit(self, date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return [_clean(d) for d in self.store.list_audit(date=date, limit=limit)]


def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc is None:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out
