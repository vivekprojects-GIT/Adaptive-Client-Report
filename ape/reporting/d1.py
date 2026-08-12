"""APE D1 — report template selection.

═══════════════════════════════════════════════════════════════════════════
THE DECISION
═══════════════════════════════════════════════════════════════════════════

    REPORT TYPE      determines WHICH ARMS ARE ELIGIBLE
    CLIENT EVIDENCE  determines WHICH ELIGIBLE ARM IS CHOSEN

That split is the whole design. `report_type` is the *decision context*, not
an intent — it is not something a classifier infers from natural language, it
is the situation the bandit is choosing under. Each report type carries its
own arm catalogue; there is deliberately no universal arm list, because a
risk review and a quarterly review have nothing shape-wise in common.

    report_type = quarterly_portfolio_review
      arms: balanced_default · concise_summary · visual_first
            comparison_focused · narrative_explanatory · numeric_detail

    report_type = rebalancing_proposal
      arms: rebalance_recommendation_first · rebalance_reasoning_first
            rebalance_side_by_side

D2 is the other decision and works the other way round: its context IS a
natural-language question intent, and its arms are answer formats.

═══════════════════════════════════════════════════════════════════════════
THE THREE-LAYER CELL
═══════════════════════════════════════════════════════════════════════════

    _global#<report_type>                  every report ever served
    SEGMENT#<segment_id>#<report_type>     one client archetype
    CLIENT#<user_hash>#<report_type>       one individual

Arms live in all three. What differs is how much evidence each has, and the
blend weights accordingly — see `effective_profile`.

The client's preference profile is NOT scoped by report type. "This client
prefers tables" holds for every report they receive, which is what lets a
rare report type (a rebalancing proposal, ~50/year firm-wide) inherit
personalisation earned on a frequent one.

═══════════════════════════════════════════════════════════════════════════
STORAGE NOTE
═══════════════════════════════════════════════════════════════════════════

D1 arms live in the existing `ape_user_bandit_state` collection so that
reward attribution, the admin Bandit State tab and the audit trail all work
unchanged. Its `intent` column holds the report_type. The column name is
legacy from the chat product — read it as "decision context". Renaming it
would break every existing index and query for no functional gain.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..bandit.selection import compute_ucb

# Shared presentation vocabulary. A template's style vector and a client's
# learned profile are expressed in these same terms — that shared vocabulary
# is what lets a chat signal reach a template the client never received.
DIMENSIONS: Tuple[str, ...] = (
    "concise", "detail", "visual", "table", "comparison",
    "numeric_precision", "narrative", "step_by_step", "technical_depth",
)

GLOBAL_SCOPE = "_global"

# How the two priors combine before client evidence is applied. Segment is
# weighted higher than global because an archetype is a better guess for an
# unknown client than the whole book's average.
W_GLOBAL_PRIOR = 0.4
W_SEGMENT_PRIOR = 0.6

# Evidence-confidence curve. n=0 -> 0.00, n=10 -> 0.33, n=20 -> 0.50,
# n=50 -> 0.71. Capped so the prior never disappears entirely: a client with
# a long history but one bad quarter still gets sanity-checked against what
# works for everyone.
EVIDENCE_K = 20
EVIDENCE_CAP = 0.80


class NotPersonalisableError(ValueError):
    """Raised when D1 is asked to shape a prescribed report.

    Deliberately an exception rather than a quiet default. A tax pack or a
    statutory valuation has its format set by regulation; code that asks the
    bandit to choose one is wrong and should fail loudly in a test rather
    than silently produce a personalised statutory document.
    """


# ---------------------------------------------------------------------------
# Cell keys
# ---------------------------------------------------------------------------

def cell_key(report_type: str, scope: str = GLOBAL_SCOPE) -> str:
    """`scope` is "_global", "SEGMENT#<id>" or "CLIENT#<user_hash>"."""
    return f"{scope}#{report_type}"


def segment_scope(segment_id: str) -> str:
    return f"SEGMENT#{segment_id}"


def client_scope(user_id_hash: str) -> str:
    return f"CLIENT#{user_id_hash}"


# ---------------------------------------------------------------------------
# Profile maths
# ---------------------------------------------------------------------------

def vector(profile: Dict[str, float]) -> List[float]:
    return [float(profile.get(d, 0.5)) for d in DIMENSIONS]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0.0 or nb == 0.0 else dot / (na * nb)


def evidence_weight(n_signals: int) -> float:
    """How far to trust this client over the priors."""
    if n_signals <= 0:
        return 0.0
    return min(EVIDENCE_CAP, n_signals / (n_signals + EVIDENCE_K))


def blend_prior(
    global_profile: Optional[Dict[str, float]],
    segment_profile: Optional[Dict[str, float]],
) -> Dict[str, float]:
    """Combine the two priors. Falls back to whichever exists.

    If segment evidence is missing we lean entirely on global rather than
    inventing a segment — a made-up archetype is worse than the honest
    population average.
    """
    if segment_profile is None and global_profile is None:
        return {d: 0.5 for d in DIMENSIONS}
    if segment_profile is None:
        return dict(global_profile or {})
    if global_profile is None:
        return dict(segment_profile)
    return {
        d: W_GLOBAL_PRIOR * float(global_profile.get(d, 0.5))
           + W_SEGMENT_PRIOR * float(segment_profile.get(d, 0.5))
        for d in DIMENSIONS
    }


def effective_profile(
    client_profile: Optional[Dict[str, float]],
    n_signals: int,
    global_profile: Optional[Dict[str, float]] = None,
    segment_profile: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[str, float], float]:
    """The profile actually scored against templates. Returns (profile, w)."""
    prior = blend_prior(global_profile, segment_profile)
    w = evidence_weight(n_signals)
    if not client_profile or w == 0.0:
        return prior, 0.0
    return (
        {d: (1.0 - w) * prior.get(d, 0.5) + w * float(client_profile.get(d, 0.5))
         for d in DIMENSIONS},
        w,
    )


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Selection policy
# ---------------------------------------------------------------------------
#
# THOMPSON, NOT UCB — and the reason is batch generation.
#
# UCB is a deterministic argmax. Reports are produced for a whole book at
# once, all reading the same cell before any state updates, so a
# deterministic policy hands every client the SAME arm. That collects
# hundreds of observations of one arm and none of the others: the sparsity
# problem the design set out to avoid, in a new disguise.
#
# Thompson draws independently per report, so a batch spreads across arms in
# proportion to how likely each is to be best, and the split tightens on its
# own as evidence accumulates. There is no exploration constant to tune.
#
# compute_ucb is retained for the admin display and for comparison, but it is
# no longer the production policy.

PRIOR_STRENGTH = 4.0   # fallback; the live value is admin-editable


def _live_strength() -> float:
    from ape.reporting.policy_config import thompson_params
    return thompson_params()["prior_strength_d1"]


def _beta_params(count: int, total_reward: float, prior_mean: float,
                 strength: float = None) -> tuple:
    if strength is None:
        strength = _live_strength()
    """Beta parameters for one arm.

    Observed reward is stored in [0, 1] per report, so `total_reward` is the
    success mass and `count - total_reward` the failure mass. The style-fit
    prior enters as pseudo-observations rather than as a separate term, which
    is what lets a well-matched but unserved arm compete without pretending
    it has real evidence.
    """
    obs_a = max(0.0, float(total_reward))
    obs_b = max(0.0, float(count) - float(total_reward))
    p = min(1.0, max(0.0, prior_mean))
    return (1.0 + strength * p + obs_a,
            1.0 + strength * (1.0 - p) + obs_b)


def thompson_draw(count: int, total_reward: float, prior_mean: float,
                  rng: Optional[random.Random] = None) -> float:
    a, b = _beta_params(count, total_reward, prior_mean)
    return (rng or random).betavariate(a, b)


def eligible_arms(
    templates: List[Dict[str, Any]],
    report_type: str,
) -> List[Dict[str, Any]]:
    """ACTIVE templates for this report type. The arm catalogue is
    report-type specific by design — there is no universal arm list."""
    return [
        t for t in templates
        if t.get("report_type") == report_type
        and t.get("status", "ACTIVE") == "ACTIVE"
    ]


def score_arms(
    templates: List[Dict[str, Any]],
    arm_state: Dict[str, Dict[str, Any]],
    report_type: str,
    client_profile: Optional[Dict[str, float]] = None,
    n_signals: int = 0,
    global_profile: Optional[Dict[str, float]] = None,
    segment_profile: Optional[Dict[str, float]] = None,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """Score every eligible arm, returning explainable rows (best first).

    Each row carries the intermediate values so the admin debug screen can
    show *why* an arm won, not merely that it did.
    """
    arms = eligible_arms(templates, report_type)
    eff, w = effective_profile(client_profile, n_signals,
                               global_profile, segment_profile)
    eff_vec = vector(eff)
    n_total = sum(int(arm_state.get(t["strategy"], {}).get("count", 0)) for t in arms)

    rows: List[Dict[str, Any]] = []
    for t in arms:
        st = arm_state.get(t["strategy"], {})
        count = int(st.get("count", 0))
        total_reward = float(st.get("total_reward", 0.0))
        avg = total_reward / count if count else 0.0

        # Cosine is [0,1] for non-negative vectors; rewards are [-1,+1], so
        # map fit onto the reward scale before the two are combined.
        fit = cosine_similarity(eff_vec, vector(t.get("style_profile") or {}))
        exploit = avg if count else 0.0
        exploit = 0.5 * exploit + 0.5 * ((fit * 2.0) - 1.0)

        # prior mean in [0,1] from the style fit; observations do the rest
        prior_mean = 0.5 * fit + 0.5 * ((avg + 1.0) / 2.0 if count else fit)
        draw = thompson_draw(count, total_reward, prior_mean, rng)
        score = draw
        rows.append({
            "draw":          round(draw, 4),
            "prior_mean":    round(prior_mean, 4),
            "ucb_display":   999.0 if compute_ucb(count, exploit, n_total) == float("inf")
                              else round(compute_ucb(count, exploit, n_total), 4),
            "strategy":      t["strategy"],
            "template_id":   t.get("template_id"),
            "label":         t.get("label") or t["strategy"],
            "count":         count,
            "avg_reward":    round(avg, 4),
            "fit":           round(fit, 4),
            "user_weight":   round(w, 4),
            "exploit":       round(exploit, 4),
            "score_display": 999.0 if score == float("inf") else round(score, 4),
            "_score":        score,
        })

    rows.sort(key=lambda r: (r["_score"], -_ord(r["strategy"])), reverse=True)
    # `_score` is +inf for any unpulled arm (round-robin's safety net) and JSON
    # has no infinity literal, so it must not survive past the sort. Dropping
    # it here rather than at each call site means no endpoint can leak it.
    # `score_display` already carries the presentable 999.0 sentinel.
    for r in rows:
        r.pop("_score", None)
    return rows


def select(
    templates: List[Dict[str, Any]],
    arm_state: Dict[str, Dict[str, Any]],
    report_type: str,
    personalisable: bool = True,
    client_profile: Optional[Dict[str, float]] = None,
    n_signals: int = 0,
    global_profile: Optional[Dict[str, float]] = None,
    segment_profile: Optional[Dict[str, float]] = None,
    explicit_preference: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Tuple[str, List[Dict[str, Any]], str]:
    """Choose one arm. Returns (strategy, scored_rows, method).

    Priority: explicit client preference > round-robin cold start > UCB.
    """
    if not personalisable:
        arms = eligible_arms(templates, report_type)
        if len(arms) == 1:
            # Prescribed types have exactly one mandated template. It is
            # served directly — this is not a bandit decision.
            return arms[0]["strategy"], [], "mandated"
        raise NotPersonalisableError(
            f"'{report_type}' is prescribed and must have exactly one active "
            f"template; found {len(arms)}"
        )

    rows = score_arms(templates, arm_state, report_type, client_profile,
                      n_signals, global_profile, segment_profile, rng)
    if not rows:
        raise ValueError(f"no active templates for report type '{report_type}'")

    live = {r["strategy"] for r in rows}
    if explicit_preference and explicit_preference in live:
        return explicit_preference, rows, "explicit"

    for r in rows:
        if r["count"] == 0:
            return r["strategy"], rows, "round_robin"

    return rows[0]["strategy"], rows, "thompson"


def _ord(s: str) -> int:
    """Deterministic tie-break: identical state always picks the same arm."""
    return sum(ord(c) for c in (s or ""))
