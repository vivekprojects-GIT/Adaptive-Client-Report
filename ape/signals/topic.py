"""
Topic canonicalization — collapse phrasing variants to a single canonical key.

Handles two layers of normalization:

  1. Canonical match (lexical): lowercase + non-alnum-to-underscore.
     "Roth IRA", "roth-ira", "ROTH IRA" all collapse to "roth_ira".

  2. Whitelist + alias map (semantic): snap freeform topics to a curated
     vocabulary so the bandit doesn't fragment across near-duplicates.
     "roth_contribution", "roth_eligibility", "roth_limits" all snap to "roth_ira".

The whitelist is maintained by hand. When analytics show many turns falling
to "general", that's a signal to add new entries.
"""

from __future__ import annotations

import re
from typing import Dict, Set


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


# ---- Canonical vocabulary (the bandit cell key dimension) ------------------
TOPIC_WHITELIST: Set[str] = {
    # Retirement
    "roth_ira", "traditional_ira", "401k", "roth_conversion",
    "rmd", "retirement_planning",
    # Banking
    "checking_account", "savings_account", "money_market", "cd",
    "bank_statement", "wire_transfer", "ach_transfer",
    # Credit
    "credit_card", "credit_score", "debt", "loan",
    "mortgage", "refinance", "home_equity",
    # Investing
    "etf", "mutual_fund", "stock", "bond", "index_fund",
    "asset_allocation", "diversification", "rebalancing",
    # Taxes
    "income_tax", "capital_gains", "tax_deduction",
    "tax_credit", "tax_strategy",
    # Insurance
    "life_insurance", "health_insurance", "auto_insurance",
    # Planning
    "budgeting", "emergency_fund", "estate_planning", "college_savings",
    # Catch-all
    "general",
}


# Alias map for snapping freeform LLM output to the whitelist.
# Order matters — first match wins. Keep keys lowercase.
_ALIAS_MAP: Dict[str, str] = {
    # Retirement aliases
    "ira":               "traditional_ira",
    "roth":              "roth_ira",
    "roth_account":      "roth_ira",
    "roth_savings":      "roth_ira",
    "roth_contribution": "roth_ira",
    "roth_eligibility":  "roth_ira",
    "roth_limits":       "roth_ira",
    "roth_ira_tax":      "roth_ira",
    "conversion":        "roth_conversion",
    "401":               "401k",
    "401_k":             "401k",
    "fourohonek":        "401k",
    "retirement":        "retirement_planning",
    # Banking aliases
    "checking":          "checking_account",
    "savings":           "savings_account",
    "money_market_fund": "money_market",
    "wire":              "wire_transfer",
    "ach":               "ach_transfer",
    # Credit aliases
    "card":              "credit_card",
    "credit":            "credit_card",
    "loan_card":         "credit_card",
    "fico":              "credit_score",
    "credit_rating":     "credit_score",
    "home_loan":         "mortgage",
    "house_loan":        "mortgage",
    # Investing aliases
    "stocks":            "stock",
    "bonds":             "bond",
    "etfs":              "etf",
    "index":             "index_fund",
    "allocation":        "asset_allocation",
    # Tax aliases
    "taxes":             "income_tax",
    "tax":               "income_tax",
    "capital_gain":      "capital_gains",
    # Planning aliases
    "budget":            "budgeting",
    "savings_goal":      "emergency_fund",
    "estate":            "estate_planning",
    "college":           "college_savings",
}


def canonicalize_topic(raw: str | None) -> str:
    """Normalize a topic string and snap it to the whitelist.

    Examples:
        "Roth IRA"           -> "roth_ira"
        "Roth-IRA"           -> "roth_ira"
        "ROTH IRA"           -> "roth_ira"
        "Roth Conversion?"   -> "roth_conversion"
        "  401(k)  "         -> "401k"
        "cryptocurrency"     -> "general"   (not in whitelist or aliases)
        ""                   -> "general"
        None                 -> "general"
    """
    if not raw:
        return "general"

    # Layer 1: canonical (lexical) match
    s = str(raw).strip().lower()
    s = _NON_ALNUM.sub("_", s)
    s = s.strip("_")
    if not s:
        return "general"

    # Layer 2a: direct whitelist hit
    if s in TOPIC_WHITELIST:
        return s

    # Layer 2b: alias lookup
    if s in _ALIAS_MAP:
        target = _ALIAS_MAP[s]
        # Sanity check: alias must point to a real whitelist entry
        return target if target in TOPIC_WHITELIST else "general"

    # Layer 2c: substring containment heuristic — LONGEST KEYWORDS FIRST.
    # Without this, "roth_ira_contribution" would match the short alias
    # "ira" -> "traditional_ira" before reaching the longer "roth_*" aliases.
    # Sorting by length descending makes the most-specific match win.
    longest_first = sorted(_ALIAS_MAP.items(), key=lambda kv: -len(kv[0]))
    for keyword, target in longest_first:
        if keyword in s and target in TOPIC_WHITELIST:
            return target
    longest_whitelist = sorted(TOPIC_WHITELIST, key=lambda x: -len(x))
    for entry in longest_whitelist:
        if entry != "general" and entry in s:
            return entry

    # Nothing matched — catch-all
    return "general"


def slugify_topic(raw: str | None) -> str:
    """Lightweight topic key: lowercase snake_case, no whitelist snapping.

    Used for domains that don't have a curated whitelist (cricket, it,
    movies, travel, …). Keeps the LLM's topic phrase as its own bandit-cell
    key instead of collapsing everything unknown to "general".
    """
    if not raw:
        return "general"
    s = _NON_ALNUM.sub("_", str(raw).strip().lower()).strip("_")
    return s or "general"


# Domains that use the curated finance whitelist. Everything else is slugified.
_WHITELIST_DOMAINS = {"finance"}


def canonicalize_topic_for_domain(raw: str | None, domain: str | None) -> str:
    """Domain-aware topic key.

    finance  → snap to the curated finance whitelist (canonicalize_topic).
    others   → slugify only (preserve the LLM topic as its own key).
    """
    if (domain or "").lower() in _WHITELIST_DOMAINS:
        return canonicalize_topic(raw)
    return slugify_topic(raw)
