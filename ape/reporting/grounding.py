"""Numeric grounding validator.

═══════════════════════════════════════════════════════════════════════════
THE RULE
═══════════════════════════════════════════════════════════════════════════

Every number a client reads must trace to the frozen snapshot. Not "the
prompt told the model not to invent figures" — checked, mechanically, after
generation and before render.

A block that states a number we cannot account for is REJECTED. It is not
corrected, not flagged for later, not rendered with a warning. A plausible
wrong figure in a client document is worse than a missing section.

═══════════════════════════════════════════════════════════════════════════
WHY FORMATTING IS THE HARD PART
═══════════════════════════════════════════════════════════════════════════

The snapshot holds 1240000.0. A report may legitimately say any of:

    £1,240,000.00   $1.24M   1.24 million   1240000   £1,240,000

All are the same fact. So matching is done on NORMALISED values with a
tolerance that reflects how the figure was written — a number given to one
decimal place cannot be held to two.

Derived arithmetic is also allowed where it is unambiguous: a report may
state the sum of two fees, or a difference against a benchmark, without
those totals existing verbatim in the snapshot. Those are computed here and
added to the allowlist rather than being treated as fabrication.

WHAT IS DELIBERATELY NOT CHECKED
--------------------------------
Small integers used as ordinary language ("three asset classes", "the top 5")
and years. Grounding them produces constant false rejections and they carry
no financial claim. The threshold is documented in IGNORE_BELOW.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Integers below this are treated as prose, not financial claims. Percentages
# and any number with a decimal point are always checked regardless.
IGNORE_BELOW = 13
YEAR_RANGE = (1900, 2100)

# Tolerance is relative to how precisely the figure was written.
TOLERANCE_BY_DP = {0: 0.51, 1: 0.051, 2: 0.0051}
REL_TOLERANCE = 0.005          # 0.5% — covers rounded millions ("1.24M")

_NUMBER = re.compile(
    r"""
    # A leading minus is PART OF THE NUMBER: "-1.33%" is negative 1.33, and
    # reading it as positive 1.33 makes every loss-making report ungrounded.
    # The lookbehind keeps the hyphen in "2025-09-30" or "Q1-Q2" from being
    # read as a sign.
    (?P<sign>(?<![\dA-Za-z])[-−])?
    (?P<cur>[£$€])?\s*
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?   # 1,240,000.00
          | \d+\.\d+                        # 4.8
          | \d+)                            # 2150
    \s*(?P<suffix>%|bps|m\b|M\b|k\b|K\b|bn\b|billion\b|million\b|thousand\b)?
    """,
    re.VERBOSE,
)

# Written with a multiplier => deliberately rounded => relative tolerance.
_MULT_SUFFIX = re.compile(r"(m|M|k|K|bn|billion|million|thousand)\b")

_MULTIPLIER = {
    "m": 1e6, "M": 1e6, "million": 1e6,
    "k": 1e3, "K": 1e3, "thousand": 1e3,
    "bn": 1e9, "billion": 1e9,
}


@dataclass
class Finding:
    block_id: str
    kind: str            # "ungrounded_number" | "unknown_source_ref" | "no_source_refs"
    detail: str
    value: Optional[float] = None
    where: str = ""


@dataclass
class Verdict:
    ok: bool
    accepted: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    checked_numbers: int = 0

    def summary(self) -> str:
        return (f"{len(self.accepted)} accepted, {len(self.rejected)} rejected, "
                f"{self.checked_numbers} numbers checked")


# ---------------------------------------------------------------------------
# Extraction + normalisation
# ---------------------------------------------------------------------------

def extract_numbers(text: str) -> List[Tuple[float, int, str, int]]:
    """Return (value, decimal_places, raw) for every figure in prose.

    A percentage keeps its face value: "4.8%" is the number 4.8, because that
    is how the snapshot stores it. Multipliers are expanded, so "1.24M"
    becomes 1240000.
    """
    out: List[Tuple[float, int, str, int]] = []
    for m in _NUMBER.finditer(text or ""):
        raw_num = m.group("num")
        suffix = (m.group("suffix") or "").strip()
        try:
            val = float(raw_num.replace(",", ""))
        except ValueError:
            continue
        dp = len(raw_num.split(".")[1]) if "." in raw_num else 0
        if suffix in _MULTIPLIER:
            val *= _MULTIPLIER[suffix]
            dp = 0
        if m.group("sign"):
            val = -val
        out.append((val, dp, m.group(0).strip(), m.start()))
    return out


# A report may legitimately state the MAGNITUDE of a negative figure and put
# the direction in words: "declined by 1.33%" rather than "returned -1.33%".
# The magnitude is only accepted when one of these words sits just before it,
# so "returned 1.33%" for a quarter that actually fell 1.33% stays REJECTED —
# which is the misstatement that would matter to a client.
NEGATIVE_CUES = (
    "fell", "fall", "decline", "declined", "decrease", "decreased", "down",
    "loss", "losses", "lost", "lower", "behind", "below", "negative", "drag",
    "detract", "detracted", "drop", "dropped", "reduced", "shortfall",
    "trailed", "trailing", "under", "underperform", "underperformed", "less",
)
CUE_WINDOW = 80


def _has_negative_cue(text: str, start: int) -> bool:
    window = text[max(0, start - CUE_WINDOW):start].lower()
    return any(cue in window for cue in NEGATIVE_CUES)


def _is_prose_number(val: float, dp: int, raw: str) -> bool:
    """Small counting words and years carry no financial claim."""
    if dp > 0 or "%" in raw or any(c in raw for c in "£$€"):
        return False
    if val != int(val):
        return False
    if YEAR_RANGE[0] <= val <= YEAR_RANGE[1] and val == int(val):
        return True
    return abs(val) < IGNORE_BELOW


def _matches(value: float, dp: int, allowed: Iterable[float],
             rounded: bool = False) -> bool:
    """Does `value` correspond to any allowed fact?

    Two tolerances, and which applies depends on HOW THE NUMBER WAS WRITTEN:

      absolute  — always. Tight, scaled to the stated decimal places.
      relative  — only when `rounded`, i.e. the figure carried a multiplier
                  ("14.3K", "$1.24M"). Those are deliberately imprecise
                  renderings and need the slack.

    The relative band must NOT apply to a figure written out in full: 0.5%
    of £10,517.81 is ±£52, so "£10,518.81" would sail through despite being
    wrong. A number written to the penny is claiming that precision, and is
    held to it.
    """
    abs_tol = TOLERANCE_BY_DP.get(dp, 0.0051)
    for a in allowed:
        if abs(a - value) <= abs_tol:
            return True
        if rounded and a != 0 and abs(a - value) / abs(a) <= REL_TOLERANCE:
            return True
    return False


def derived_facts(facts: Dict[str, float]) -> Dict[str, float]:
    """Totals and differences a report may legitimately state.

    Without these, a correct sentence like "fees totalled £2,870" would be
    rejected because only the two component fees exist in the snapshot.
    """
    out = dict(facts)
    vals = list(facts.values())

    def put(key: str, v: Optional[float]) -> None:
        if v is not None:
            out[key] = round(v, 4)

    q = facts.get("quarter_return_pct")
    b = facts.get("benchmark_return_pct")
    if q is not None and b is not None:
        put("derived.excess", q - b)
        put("derived.excess_abs", abs(q - b))

    adv, fund = facts.get("fees.advisory"), facts.get("fees.fund")
    if adv is not None and fund is not None:
        put("derived.fees_total", adv + fund)

    # Return BEFORE fees. Standard in wealth reporting ("you earned 5.08%
    # gross, 4.74% after costs") and unambiguously derivable, but it existed
    # nowhere in the allowlist — so a model stating a correct gross figure
    # had its whole block rejected and replaced with plainer text.
    drag = facts.get("fees.drag_pct")
    if q is not None and drag is not None:
        put("derived.gross_return", q + drag)

    c, w = facts.get("flows.contributions"), facts.get("flows.withdrawals")
    if c is not None and w is not None:
        put("derived.net_flow", c - w)
        put("derived.net_flow_abs", abs(c - w))

    # Allocation and attribution totals.
    alloc = [v for k, v in facts.items() if k.startswith("alloc.")]
    if alloc:
        put("derived.alloc_total", sum(alloc))
    attr = [v for k, v in facts.items() if k.startswith("attr.")]
    if attr:
        put("derived.attr_total", sum(attr))

    # Contributor / detractor tables state a running subtotal ("top 5") and a
    # residual ("Others"). Neither exists verbatim in the snapshot, but both
    # are fully determined by it, so every prefix sum and its complement is
    # computed here rather than left to be rejected as fabrication.
    contribs = [v for k, v in facts.items()
                if k.startswith("hold.") and k.endswith(".contribution")]
    for arr, tag in ((sorted([v for v in contribs if v > 0], reverse=True), "pos"),
                     (sorted([v for v in contribs if v < 0]), "neg")):
        if not arr:
            continue
        group_total = sum(arr)
        put(f"derived.contrib_{tag}_total", group_total)
        running = 0.0
        for i, v in enumerate(arr, 1):
            running += v
            put(f"derived.contrib_{tag}_top{i}", running)
            put(f"derived.contrib_{tag}_rest{i}", group_total - running)

    cum = facts.get("hist.cumulative")
    cum_bm = facts.get("hist.cumulative_benchmark")
    if cum is not None and cum_bm is not None:
        put("derived.hist_cumulative_excess", cum - cum_bm)
        put("derived.hist_cumulative_excess_abs", abs(cum - cum_bm))

    # Per-period excess written as a magnitude ("2.10% behind in 2026Q1").
    for k, v in list(facts.items()):
        if k.startswith("hist.") and k.endswith(".excess"):
            put(f"derived.{k}_abs", abs(v))

    # Portfolio value x weight — the money in each sleeve, which a holdings
    # table states and a narrative may reference.
    pv = facts.get("portfolio_value")
    if pv is not None:
        for k, v in list(facts.items()):
            if k.startswith("alloc."):
                put(f"derived.value_{k}", pv * v / 100.0)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_block(
    block: Dict[str, Any],
    facts: Dict[str, float],
    prose_fields: Sequence[str] = ("text", "note"),
    labels: Sequence[str] = (),
) -> List[Finding]:
    """Check one block. Empty list means it is grounded."""
    bid = block.get("block_id", "?")
    findings: List[Finding] = []

    refs = block.get("source_refs") or []
    if not refs:
        findings.append(Finding(bid, "no_source_refs",
                                "block declares no source_refs"))
    for r in refs:
        if r not in facts:
            findings.append(Finding(bid, "unknown_source_ref",
                                    f"source_ref '{r}' is not in the snapshot",
                                    where="source_refs"))

    allowed = set(facts.values())
    data = block.get("data") or {}

    # Structured values: every number the widget will display.
    for path, val in _structured_numbers(block.get("type", ""), data):
        if not _matches(val, 2, allowed):
            findings.append(Finding(bid, "ungrounded_number",
                                    f"{val:g} at {path} is not in the snapshot",
                                    value=val, where=path))

    # Prose: scan free text for stated figures.
    for field_name, text in _prose_strings(data, prose_fields):
        exempt = _label_spans(text, labels)
        for val, dp, raw, start in extract_numbers(text):
            if _is_prose_number(val, dp, raw) or _inside(start, exempt):
                continue
            rounded = bool(_MULT_SUFFIX.search(raw))
            if _matches(val, dp, allowed, rounded):
                continue
            if (val > 0 and _matches(-val, dp, allowed, rounded)
                    and _has_negative_cue(text, start)):
                continue
            findings.append(Finding(bid, "ungrounded_number",
                                    f"'{raw}' in {field_name} is not in the snapshot",
                                    value=val, where=field_name))
    return findings


def _label_spans(text: str, labels: Sequence[str]) -> List[Tuple[int, int]]:
    """Character ranges occupied by proper names, which are exempt."""
    spans: List[Tuple[int, int]] = []
    low = text.lower()
    for label in labels:
        needle = label.lower()
        start = low.find(needle)
        while start != -1:
            spans.append((start, start + len(needle)))
            start = low.find(needle, start + 1)
    return spans


def _inside(pos: int, spans: Sequence[Tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def _prose_strings(data: Dict[str, Any],
                   prose_fields: Sequence[str]) -> List[Tuple[str, str]]:
    """Every free-text string a client will read in this block.

    Key takeaways and explainers keep their sentences in data["items"][i],
    not data["text"]. Those sentences are the interpretive claims a client
    acts on, so a top-level-only scan would leave the most consequential
    prose in the report unchecked.
    """
    out: List[Tuple[str, str]] = []
    for name in prose_fields:
        v = data.get(name)
        if isinstance(v, str) and v.strip():
            out.append((name, v))
    for i, item in enumerate(data.get("items") or []):
        if not isinstance(item, dict):
            continue
        for name in prose_fields:
            v = item.get(name)
            if isinstance(v, str) and v.strip():
                out.append((f"items[{i}].{name}", v))
    return out


def _structured_numbers(block_type: str, data: Dict[str, Any]) -> List[Tuple[str, float]]:
    """Numbers a client will actually read, by widget type.

    Structural extraction rather than a regex over the JSON: a blanket scan
    picks up array indices, chart geometry and axis bounds, then fails to
    ground them and rejects a perfectly good block.
    """
    out: List[Tuple[str, float]] = []

    def add(path: str, v: Any) -> None:
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            out.append((path, float(v)))

    if block_type == "kpi_grid":
        for i, it in enumerate(data.get("items", [])):
            add(f"items[{i}].value", it.get("value"))
    elif block_type in ("allocation_donut",):
        for i, s in enumerate(data.get("segments", [])):
            add(f"segments[{i}].value_pct", s.get("value_pct"))
    elif block_type == "comparison_chart":
        add("portfolio", data.get("portfolio"))
        add("benchmark", data.get("benchmark"))
    elif block_type == "comparison_table":
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].value", r.get("value"))
            add(f"rows[{i}].benchmark_value", r.get("benchmark_value"))
    elif block_type == "holdings_table":
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].weight_pct", r.get("weight_pct"))
            add(f"rows[{i}].value", r.get("value"))
    elif block_type == "fees_table":
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].amount", r.get("amount"))
        add("total", data.get("total"))
    elif block_type == "performance_line":
        for i, s in enumerate(data.get("series", [])):
            for j, p in enumerate(s.get("points", [])):
                add(f"series[{i}].points[{j}].value", p.get("value"))
    elif block_type in ("top_contributors", "top_detractors"):
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].contribution_pct", r.get("contribution_pct"))
            add(f"rows[{i}].return_pct", r.get("return_pct"))
            add(f"rows[{i}].weight_pct", r.get("weight_pct"))
        add("others_pct", data.get("others_pct"))
        add("total_pct", data.get("total_pct"))
    elif block_type == "allocation_vs_target":
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].value", r.get("value"))
            add(f"rows[{i}].benchmark_value", r.get("benchmark_value"))
            add(f"rows[{i}].drift_pct", r.get("drift_pct"))
    elif block_type == "returns_table":
        for i, r in enumerate(data.get("rows", [])):
            add(f"rows[{i}].value", r.get("value"))
            add(f"rows[{i}].benchmark_value", r.get("benchmark_value"))
            add(f"rows[{i}].excess_pct", r.get("excess_pct"))
    elif block_type == "chart":
        for i, it in enumerate(data.get("items", [])):
            add(f"items[{i}].value", it.get("value"))
        for i, s in enumerate(data.get("series", [])):
            for j, v in enumerate(s.get("values", [])):
                if isinstance(v, (int, float)):
                    add(f"series[{i}].values[{j}]", v)
        add("value", data.get("value"))
    return out


def validate_report(report: Dict[str, Any], facts: Dict[str, float],
                    labels: Sequence[str] = ()) -> Verdict:
    """Validate a whole report. Rejected blocks must not be rendered."""
    allowed = derived_facts(facts)
    v = Verdict(ok=True)
    for block in report.get("blocks", []):
        findings = validate_block(block, allowed, labels=labels)
        v.checked_numbers += len(_structured_numbers(
            block.get("type", ""), block.get("data") or {}))
        if findings:
            v.ok = False
            v.rejected.append(block)
            v.findings.extend(findings)
        else:
            v.accepted.append(block)
    return v
