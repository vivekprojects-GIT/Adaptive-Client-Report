"""The block registry — what a composer is allowed to choose from.

Every entry names what the block SHOWS, which fact category it covers, and
what data it needs. The last part matters most: a composer that picks
`top_contributors` for a client with no holdings produces a block that
silently returns None, and the report quietly loses a section. So the
registry is filtered against the actual snapshot before the composer ever
sees it — it chooses from what can genuinely be drawn for THIS client,
not from a catalogue of everything the system can theoretically render.

This is also the allowlist for validating what comes back. A composed
template naming a block that is not here is rejected rather than dropped,
because a silently ignored block is indistinguishable from one the
composer never asked for.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ape.reporting.csv_source import ClientSnapshot

# name -> (category, needs, one-line description for the composer)
#
# `needs` is checked against the snapshot; blocks whose data is missing are
# withheld from the composer entirely.
REGISTRY: Dict[str, Dict[str, Any]] = {
    "kpi_grid": dict(
        category="headline", needs=None,
        shows="Four headline figures: value, return, benchmark, risk level."),
    "callout": dict(
        category="headline", needs=None,
        shows="One-sentence banner stating the single most important thing."),
    "narrative": dict(
        category="prose", needs=None,
        shows="Opening prose: what happened this period and why."),
    "key_takeaways": dict(
        category="prose", needs=None,
        shows="Three or four cards, each a claim plus the figure behind it."),
    "explainer": dict(
        category="prose", needs=None,
        shows="Plain-English definitions of benchmark, contribution, drift."),
    "disclosures": dict(
        category="smallprint", needs=None,
        shows="Past-performance wording and the valuation source."),

    "performance_history": dict(
        category="performance", needs="history",
        shows="Line series of return vs benchmark across every period held."),
    "returns_table": dict(
        category="performance", needs="history",
        shows="Return per period with benchmark and difference, plus the "
              "compounded total."),
    "performance_line": dict(
        category="performance", needs=None,
        shows="This period's return against benchmark, single point."),
    "comparison_chart": dict(
        category="performance", needs=None,
        shows="Two bars: portfolio return vs benchmark return."),

    "allocation_donut": dict(
        category="allocation", needs="allocations",
        shows="Asset-class weights as proportional bars."),
    "allocation_vs_target": dict(
        category="allocation", needs="targets",
        shows="Actual weight against strategic target, with drift."),
    "holdings_table": dict(
        category="allocation", needs="allocations",
        shows="Each asset class with its weight and money value."),

    "comparison_table": dict(
        category="attribution", needs="attribution",
        shows="What each driver contributed to the total return."),
    "top_contributors": dict(
        category="attribution", needs="holdings",
        shows="The five holdings that added most, with impact bars."),
    "top_detractors": dict(
        category="attribution", needs="holdings",
        shows="The five holdings that cost most, with impact bars."),

    "fees_table": dict(
        category="costs", needs=None,
        shows="Advisory fee, fund expenses and the total."),
    "risk_card": dict(
        category="risk", needs=None,
        shows="The client's stated risk level."),
}

# Chart kinds the generic `chart` block can render, as "chart:<kind>".
CHART_KINDS = {
    "donut":     ("allocation", "Asset allocation as a ring."),
    "pie":       ("allocation", "Asset allocation as a pie."),
    "treemap":   ("allocation", "Asset allocation as nested rectangles."),
    "bar":       ("allocation", "Asset-class weights as vertical bars."),
    "hbar":      ("attribution", "Contribution per driver, horizontal bars."),
    "waterfall": ("attribution", "How each driver builds to the total return."),
    "line":      ("performance", "Return trend as a line."),
    "gauge":     ("risk", "A single figure against its range."),
}


def _has(snapshot: ClientSnapshot, need: str) -> bool:
    if need is None:
        return True
    if need == "history":
        return len(snapshot.history or []) >= 2
    if need == "holdings":
        return bool(snapshot.holdings)
    if need == "targets":
        return bool(snapshot.targets)
    if need == "allocations":
        return bool(snapshot.allocations)
    if need == "attribution":
        return bool(snapshot.attribution)
    return True


def available_blocks(snapshot: ClientSnapshot) -> List[Dict[str, Any]]:
    """The registry filtered to what THIS client's data can actually draw."""
    out: List[Dict[str, Any]] = []
    for name, meta in REGISTRY.items():
        if _has(snapshot, meta["needs"]):
            out.append({"block": name, "category": meta["category"],
                        "shows": meta["shows"]})
    if snapshot.allocations:
        for kind, (cat, shows) in CHART_KINDS.items():
            if kind in ("hbar", "waterfall") and not snapshot.attribution:
                continue
            out.append({"block": f"chart:{kind}", "category": cat,
                        "shows": shows})
    return out


def is_valid(spec: str, snapshot: ClientSnapshot) -> bool:
    """Is this block name real, and drawable for this client?"""
    base, _, kind = str(spec).partition(":")
    if base == "chart":
        return bool(snapshot.allocations) and (kind or "donut") in CHART_KINDS
    meta = REGISTRY.get(base)
    return bool(meta) and _has(snapshot, meta["needs"])


def catalogue_text(snapshot: ClientSnapshot) -> str:
    """The registry rendered for a prompt, grouped by category."""
    by_cat: Dict[str, List[str]] = {}
    for item in available_blocks(snapshot):
        by_cat.setdefault(item["category"], []).append(
            f"  {item['block']:<22} {item['shows']}")
    return "\n".join(f"{cat.upper()}\n" + "\n".join(lines)
                     for cat, lines in by_cat.items())


def catalogue_flat(snapshot: ClientSnapshot) -> str:
    """The registry as a flat list, category shown in brackets AFTER each
    name.

    Bare uppercase category headings were being echoed back as if they were
    block names ("HEADLINE", "PERFORMANCE"), spending slots on entries the
    validator then had to reject. Nothing in this rendering can be mistaken
    for a block name, and the explicit roster at the end removes any doubt
    about what a valid one looks like.
    """
    items = available_blocks(snapshot)
    lines = [f"  {i['block']:<22} [{i['category']}] {i['shows']}"
             for i in items]
    names = ", ".join(i["block"] for i in items)
    return "\n".join(lines) + f"\n\nVALID NAMES, exactly as written: {names}"
