"""LLM composer — the model designs the template instead of choosing one.

The bandit picks among six templates a human wrote. This asks the model to
assemble a bespoke one from the block registry, given the report type, what
data this client actually has, and their learned presentation preferences.

    report type + available blocks + client facts + style profile
                              |
                            LLM
                              |
              ordered list of block names (JSON)
                              |
                  validated against the registry
                              |
             the normal pipeline: build -> coverage -> grounding

WHAT THE COMPOSER MAY AND MAY NOT DO
------------------------------------
It chooses PRESENTATION: which blocks, in what order, how many. It never
touches facts — the blocks bind to the frozen snapshot exactly as before,
the coverage gate still appends any category it omitted, and the grounding
validator still checks every number. So a badly composed template produces
a badly ORDERED report, never a wrong one.

Names are validated against the registry rather than filtered: a
hallucinated block that is silently dropped is indistinguishable from one
the composer never asked for, and that difference matters when judging
whether this approach is working.

THE TRADE-OFF, STATED PLAINLY
-----------------------------
A composed template is a one-off. There is no arm to reward, so nothing
here feeds D1 learning — engagement with a composed report teaches the
system nothing about which template to send next time. Composition buys
per-client fit at the cost of accumulating evidence. That is why it is a
mode, not a replacement.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ape.reporting.csv_source import ClientSnapshot
from ape.reporting.registry import catalogue_flat, is_valid

MAX_BLOCKS = 14
MIN_BLOCKS = 5

_SYSTEM = """You design the layout of one wealth-management client report.

You choose WHICH blocks appear and IN WHAT ORDER. You never write figures
and never invent block names — every name must come from the catalogue you
are given.

Judgement you are expected to apply:
- Lead with the headline, close with the small print.
- Prefer charts for a client who reads visually, tables for one who wants
  precision, prose for one who wants explanation.
- Do not include two blocks that show the same thing the same way.
- Cover performance, allocation, attribution and costs. A client must not
  be told less because of how they like to read.

Return ONLY JSON: {"blocks": ["name", ...], "reasoning": "one sentence"}"""


def _prompt(snapshot: ClientSnapshot, report_type: str,
            dimensions: Optional[Dict[str, float]], skill: str = "") -> str:
    label = report_type.replace("_", " ")
    lines = [f"REPORT TYPE: {label}",
             f"CLIENT: {snapshot.display_name}, period {snapshot.period}"]

    moved = {k: v for k, v in (dimensions or {}).items()
             if abs(v - 0.5) > 0.02}
    if moved:
        lines.append("LEARNED PREFERENCES (0 = low, 1 = high):")
        for k, v in sorted(moved.items(), key=lambda x: -abs(x[1] - 0.5)):
            lines.append(f"  {k}: {v:.2f}")
    else:
        lines.append("LEARNED PREFERENCES: none yet — use a balanced layout.")

    if skill:
        # The dimensions say HOW MUCH; this says WHAT ABOUT. "Returns to the
        # fees section every quarter" is actionable in a way that
        # "numeric_precision: 0.80" is not.
        lines.append("\nWHAT THIS CLIENT'S OWN BEHAVIOUR HAS TAUGHT US:\n"
                     + skill)

    lines.append(f"\nDATA AVAILABLE: {len(snapshot.allocations)} asset "
                 f"classes, {len(snapshot.holdings or [])} holdings, "
                 f"{len(snapshot.history or [])} periods of history")
    lines.append(f"\nBLOCK CATALOGUE (choose only from these):\n"
                 f"{catalogue_flat(snapshot)}")
    lines.append(f"\nReturn between {MIN_BLOCKS} and {MAX_BLOCKS} blocks.")
    return "\n".join(lines)


def _parse(text: str) -> Optional[dict]:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        return None


def compose_template(
    snapshot: ClientSnapshot,
    report_type: str,
    dimensions: Optional[Dict[str, float]] = None,
    strategy_label: str = "composed",
    skill: str = "",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Ask the model to design a template. Returns (template, diagnostics).

    Diagnostics carry what was rejected and why, so a composed layout can
    be judged rather than merely trusted.
    """
    # `skill_used` records whether a learned brief was actually in the
    # prompt. Without it there is no way to tell a composition that ignored
    # the brief from one that never received it, and those are different
    # problems with different fixes.
    diag: Dict[str, Any] = {"mode": "llm_composed", "rejected": [],
                            "reasoning": "", "error": "",
                            "skill_used": bool(skill and skill.strip()),
                            "skill": (skill or "")[:600]}

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        diag["error"] = "no ANTHROPIC_API_KEY"
        return _fallback(report_type, strategy_label), diag

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=700, system=_SYSTEM,
            messages=[{"role": "user",
                       "content": _prompt(snapshot, report_type, dimensions,
                                          skill)}])
        data = _parse(resp.content[0].text)
    except Exception as exc:
        diag["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return _fallback(report_type, strategy_label), diag

    if not data or not isinstance(data.get("blocks"), list):
        diag["error"] = "model returned no usable block list"
        return _fallback(report_type, strategy_label), diag

    diag["reasoning"] = str(data.get("reasoning", ""))[:200]

    kept, seen = [], set()
    for spec in data["blocks"]:
        spec = str(spec).strip()
        if spec in seen:
            continue
        if not is_valid(spec, snapshot):
            # Named rather than dropped: a hallucinated block silently
            # discarded looks exactly like one never requested.
            diag["rejected"].append(spec)
            continue
        seen.add(spec)
        kept.append(spec)

    if len(kept) < MIN_BLOCKS:
        diag["error"] = (f"only {len(kept)} valid blocks "
                         f"(rejected {diag['rejected']})")
        return _fallback(report_type, strategy_label), diag

    diag["blocks"] = kept[:MAX_BLOCKS]
    return ({"template_id": f"composed__{report_type}",
             "strategy": strategy_label,
             "label": "Composed",
             "brief": "",
             "required_blocks": kept[:MAX_BLOCKS]}, diag)


def _fallback(report_type: str, strategy_label: str) -> Dict[str, Any]:
    """A safe layout when composition fails. Deliberately plain: the point
    of falling back is to ship a correct report, not a clever one."""
    return {"template_id": f"composed_fallback__{report_type}",
            "strategy": strategy_label, "label": "Composed (fallback)",
            "brief": "",
            "required_blocks": ["kpi_grid", "callout", "narrative",
                                "allocation_donut", "comparison_table",
                                "fees_table", "key_takeaways", "disclosures"]}
