"""A full custody statement: the shape a real private-bank report takes.

WHY THIS EXISTS
════════════════════════════════════════════════════════════════════════════

The demo reports in this system are ten blocks of headline figures. A real
private-bank statement is fifty-plus pages, and it is a different KIND of
document:

  - every position listed individually, with cost price, current price,
    both FX rates, unrealised result and performance
  - the SAME positions listed twice, grouped once by sector and again by
    region, so a weight from one grouping must never be added to a weight
    from the other
  - four simultaneous breakdowns: asset class, sector, region, currency
  - eight currencies, each position carrying its own
  - derivatives with negative nominal (written puts)

Building a template that matches it is worth doing before any ingestion
work, because it shows what the renderer, the grounding gate and the media
budgets have to survive, using data we control.

WRITTEN IN ENGLISH, TRANSLATED LIKE EVERYTHING ELSE
────────────────────────────────────────────────────────────────────────────

The report this is modelled on is German, and the first draft hardcoded its
German headings. That was wrong for this system: the language of a report is
a per-client setting, and every other block writes English and lets the
label table translate it. Hardcoding one language here would make this the
single template that ignores the client's own.

So every heading below goes through `_T`, and every figure through the
locale-aware formatter - which is what puts thousands separators and decimal
commas in the right places for a German reader without a German source file.

WHAT IS REAL HERE AND WHAT IS NOT
────────────────────────────────────────────────────────────────────────────

The HEADLINE figures come from the snapshot, as everywhere else: portfolio
value, return, benchmark, fees.

The POSITION-LEVEL detail is generated, deterministically from the client
id, because our snapshot schema has no positions in it. That is stated here
rather than hidden, and it is this template's honest limit: it demonstrates
the LAYOUT a custody feed would fill, not a custody feed. Everything
generated ties back to the snapshot's real portfolio value and allocation
weights, so the totals reconcile the way a real statement's do.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Callable, Dict, List, Optional

SECTORS = [
    "Energy", "Materials", "Industrials", "Consumer Discretionary",
    "Consumer Staples", "Health Care", "Financials", "Technology",
    "Communication Services", "Utilities", "Real Estate",
]

# Currency, and the share of the book held in it. Eight currencies is the
# fact that makes a single hardcoded symbol untenable elsewhere.
CURRENCIES = [
    ("EUR", 46.72), ("USD", 24.86), ("CHF", 22.61), ("GBP", 3.68),
    ("HKD", 1.21), ("DKK", 0.80), ("SEK", 0.30), ("JPY", 0.45),
]

REGIONS = [("Developed markets", 97.83), ("Emerging markets", 2.17)]

# INVENTED COMPANIES, DELIBERATELY.
#
# An earlier draft used the real holdings from a photographed statement.
# Those are somebody's actual positions, and listing them in a demo both
# reproduces a real portfolio and reads as a recommendation. What the layout
# actually needs is names of realistic SHAPE - long, multilingual, trailing
# share classes and nominal values - and invented ones do that just as well.
#
# The ISINs are constructed too: a real-looking country prefix over digits
# that belong to no issuer. Nothing here resolves to a traded security.
INSTRUMENTS = [
    ("Vantera Retail Group Inc. Registered Shares DL -,01", "US4417382051", "Consumer Discretionary", "USD"),
    ("Maison Laroque S.C.A. Actions au Porteur o.N.", "FR0000731884", "Consumer Discretionary", "EUR"),
    ("Corvane Luxe Holding SE Actions Port. (C.R.) EO 0,3", "FR0000918342", "Consumer Discretionary", "EUR"),
    ("Helvora Timepieces AG Inhaber-Aktien SF 2,25", "CH0071559204", "Consumer Discretionary", "CHF"),
    ("Kitano Motor Corp. Registered Shares o.N.", "JP3810774002", "Consumer Discretionary", "JPY"),
    ("Aurelia Personal Care S.A. Actions Port. EO 0,2", "FR0000664190", "Consumer Staples", "EUR"),
    ("Alpvale Foods AG Namens-Aktien SF -,10", "CH0094428173", "Consumer Staples", "CHF"),
    ("Greenfurrow Markets Inc. Registered Shares DL -,001", "US67310M4482", "Consumer Staples", "USD"),
    ("Rheinsted Pharma AG Namens-Aktien o.N.", "DE000RHP4417", "Health Care", "EUR"),
    ("Novexa Biosciences SE Nam.-Akt.(sp.ADRs)/1 o.N.", "US61802V7734", "Health Care", "USD"),
    ("Precisio Surgical Inc. Registered Shares DL -,001", "US72941E8806", "Health Care", "USD"),
    ("Delft Medical N.V. Shares of bearer EO 0,20", "NL0000471902", "Health Care", "EUR"),
    ("Cardiwell PLC Registered Shares DL -,0001", "IE00BQ42X118", "Health Care", "USD"),
    ("Basilea Kurhaus AG Namens-Aktien SF 0,49", "CH0038812740", "Health Care", "CHF"),
    ("Nordisk Care A/S Namens-Aktien B DK 0,1", "DK0071204518", "Health Care", "DKK"),
    ("Adlerstein Versicherung SE vink.Namens-Aktien o.N.", "DE000ADV7710", "Financials", "EUR"),
    ("Helvetia Union Bank AG Namens-Aktien SF -,10", "CH0180663421", "Financials", "CHF"),
    ("Zugsee Assurance Group AG Namens-Aktien SF 0,10", "CH0027741883", "Financials", "CHF"),
    ("Lithogra Systems N.V. Shares op naam EO -,09", "NL0011840226", "Technology", "EUR"),
    ("Northgate Software Corp. Registered Shares DL -,00000625", "US6483920174", "Technology", "USD"),
    ("Walldorf Enterprise SE Inhaber-Aktien o.N.", "DE000WLD6602", "Technology", "EUR"),
    ("Sinocom Search Ltd. Registered Shares Cl.A", "KYG884210773", "Communication Services", "HKD"),
    ("Pearl River Media Ltd. Registered Shares HD -,00002", "KYG441730829", "Communication Services", "HKD"),
    ("Rheinfunk Telekom AG Namens-Aktien o.N.", "DE000RFT2205", "Communication Services", "EUR"),
    ("Bavaria Industriewerke AG Namens-Aktien o.N.", "DE000BIW9931", "Industrials", "EUR"),
    ("Volt Systemes S.A. Actions Port. EO 4", "FR0000447126", "Industrials", "EUR"),
    ("Nordkompressor AB Namn-Aktier A SK -,637", "SE0019338004", "Industrials", "SEK"),
    ("Air Provence S.A. Actions Port. EO 5,50", "FR0000552018", "Materials", "EUR"),
    ("Corelinde PLC Registered Shares EO 0,001", "IE000K7T44Q9", "Materials", "EUR"),
    ("Britoil Energy PLC Registered Shares EO -,07", "GB00BM71ZL03", "Energy", "GBP"),
    ("Meridian Petrole SE Actions Port. EO 2,50", "FR0000806613", "Energy", "EUR"),
]

# Written puts. Negative nominal is not a rounding artefact - it is a short
# position, and every "sum the weights" assumption in this system was built
# without one in view.
DERIVATIVES = [
    ("Put option | Nominal 100 | Maison Laroque S.C.A.",
     "DE000P41MQR7", "Consumer Discretionary", "EUR", -5),
    ("Put option | Nominal 100 | Precisio Surgical Inc.",
     "DE000P82XKD4", "Health Care", "USD", -30),
    ("Put option | Nominal 100 | Pearl River Media Ltd.",
     "DE000P17LNB2", "Communication Services", "HKD", -100),
]

SUSTAIN = ["Values-aligned", "Responsible", "Impact", "ESG-neutral",
           "Not applicable"]
STANCE = ["buy", "hold", "sell"]


# ─────────────────────────────────────────────────────────────── the book

def _rng(seed_text: str) -> Callable[[], float]:
    """Deterministic pseudo-random from a string.

    Seeded per client so a statement regenerated tomorrow shows the same
    book. A demo whose positions change on every refresh is not
    demonstrating a statement, it is demonstrating a shuffle.
    """
    state = int.from_bytes(hashlib.sha256(seed_text.encode("utf-8")).digest()[:8], "big")

    def nxt() -> float:
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (2 ** 64)
        return (state >> 11) / float(1 << 53)
    return nxt


def positions(client_id: str, portfolio_value: float,
              equity_pct: float = 89.09) -> List[Dict[str, Any]]:
    """One row per instrument, reconciling to the equity book's value."""
    rnd = _rng(str(client_id) + "|positions")
    equity_value = portfolio_value * equity_pct / 100.0

    raw: List[Dict[str, Any]] = []
    for name, isin, sector, ccy in INSTRUMENTS:
        raw.append({"name": name, "isin": isin, "sector": sector,
                    "currency": ccy, "weight_raw": 0.4 + rnd() * 3.0,
                    "sustain": SUSTAIN[int(rnd() * len(SUSTAIN))],
                    "stance": STANCE[int(rnd() * len(STANCE))],
                    "qty": int(500 + rnd() * 130000),
                    "ytd_pct": round(-25 + rnd() * 55, 2), "short": False})
    for name, isin, sector, ccy, qty in DERIVATIVES:
        raw.append({"name": name, "isin": isin, "sector": sector,
                    "currency": ccy, "weight_raw": 0.02 + rnd() * 0.08,
                    "sustain": "Not applicable", "stance": "hold",
                    "qty": qty, "ytd_pct": round(-40 + rnd() * 60, 2),
                    "short": True})

    total_raw = sum(r["weight_raw"] for r in raw if not r["short"]) or 1.0
    for r in raw:
        mv = equity_value * (r["weight_raw"] / total_raw)
        if r["short"]:
            mv = -abs(mv)                     # a written put is a liability
        cost = mv / (1.0 + r["ytd_pct"] / 100.0) if r["ytd_pct"] > -99 else mv
        r["market_value"] = round(mv, 2)
        r["cost_value"] = round(cost, 2)
        r["unrealised"] = round(mv - cost, 2)
        r["weight_pct"] = round(100.0 * mv / portfolio_value, 2)
        r["price"] = round(abs(mv) / max(abs(r["qty"]), 1), 2)
        r["cost_price"] = round(abs(cost) / max(abs(r["qty"]), 1), 2)
        r["fx"] = 1.0 if r["currency"] == "EUR" else round(0.8 + rnd() * 0.7, 4)
    return raw


def by_sector(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sector subtotals, in the statement's own sector order."""
    out = []
    for sec in SECTORS:
        members = [r for r in rows if r["sector"] == sec]
        if not members:
            continue
        out.append({
            "sector": sec, "rows": members,
            "market_value": round(sum(r["market_value"] for r in members), 2),
            "cost_value": round(sum(r["cost_value"] for r in members), 2),
            "unrealised": round(sum(r["unrealised"] for r in members), 2),
            "weight_pct": round(sum(r["weight_pct"] for r in members), 2)})
    return out


# ───────────────────────────────────────────────────────── block builders

def cover(s, n: int) -> Dict[str, Any]:
    """The title page: mandate, valuation dates, and a contents list."""
    return {
        "block_id": f"wealth_cover_{n:02d}",
        "type": "wealth_cover",
        "title": "",
        "data": {
            "confidential": "Personal and confidential",
            "doc_title": "Wealth Statement",
            "mandate": "Advisory",
            "profile": getattr(s, "risk_level", "") or "Balanced",
            "client": s.display_name,
            "period": s.period,
            "as_of": str(getattr(s, "as_of", "") or ""),
            "portfolio_no": f"P{abs(hash(str(s.client_id))) % 900000000 + 100000000}",
            "contents": [
                ("Performance", 3), ("Portfolio analysis", 4),
                ("Holdings by sector", 5), ("Sector analysis", 13),
                ("Holdings by region", 14), ("Notes", 54)],
        },
        "source_refs": ["portfolio_value"],
    }


def asset_classes(s, n: int) -> Optional[Dict[str, Any]]:
    """Asset classes with the mandate's permitted band and a compliance mark.

    The band column is what makes this an ADVISORY document rather than a
    summary: it states what the mandate allows, and whether the book is
    inside it.
    """
    if not s.allocations:
        return None
    bands = {"Us Equity": (0, 100), "Intl Equity": (0, 100),
             "Fixed Income": (0, 120), "Alternatives": (0, 30),
             "Real Assets": (0, 30), "Cash": (0, 60)}
    rows = []
    for a in s.allocations:
        w = a["weight_pct"]
        lo, hi = bands.get(a["asset_class"], (0, 100))
        rows.append({"asset_class": a["asset_class"],
                     "value": round(s.portfolio_value * w / 100.0, 2),
                     "weight_pct": w, "lo": lo, "hi": hi,
                     "ok": lo <= w <= hi})
    return {
        "block_id": f"asset_class_table_{n:02d}",
        "type": "asset_class_table",
        "title": "Portfolio analysis",
        "subtitle": "How your portfolio is divided across asset classes, "
                    "against the ranges agreed for your mandate.",
        "data": {"rows": rows,
                 "total_value": round(s.portfolio_value, 2),
                 "total_pct": round(sum(r["weight_pct"] for r in rows), 2)},
        "source_refs": [f"alloc.{a['asset_class']}" for a in s.allocations]
                       + ["portfolio_value"],
    }


def currency_split(s, n: int) -> Dict[str, Any]:
    """Currency exposure — eight currencies, each position carrying its own."""
    return {
        "block_id": f"currency_split_{n:02d}",
        "extra_facts": {
            **{f"ccy.{c}": p for c, p in CURRENCIES},
            **{f"ccy_value.{c}": round(s.portfolio_value * p / 100.0, 2)
               for c, p in CURRENCIES},
        },
        "type": "currency_split",
        "title": "Currency exposure",
        "data": {"rows": [
            {"currency": c, "weight_pct": p,
             "value": round(s.portfolio_value * p / 100.0, 2)}
            for c, p in CURRENCIES]},
        "source_refs": ["portfolio_value"],
    }


def holdings_by_sector(s, n: int) -> Dict[str, Any]:
    """Every position, grouped by sector, with a subtotal per group.

    This is how the real statement is read: the client looks at their
    sector, not at fifty rows.
    """
    groups = by_sector(positions(s.client_id, s.portfolio_value))
    # Every figure this table draws, named. Without these the block shows
    # numbers it cannot account for, and the chat can only decline.
    facts = {}
    for g in groups:
        key = g["sector"].replace(" ", "_")
        facts[f"sector.{key}"] = g["weight_pct"]
        facts[f"sector_value.{key}"] = g["market_value"]
        facts[f"sector_cost.{key}"] = g["cost_value"]
        facts[f"sector_unrealised.{key}"] = g["unrealised"]
        for r in g["rows"]:
            pos = r["name"].split(" ")[0].replace(",", "")
            facts[f"pos_value.{pos}"] = r["market_value"]
            facts[f"pos_weight.{pos}"] = r["weight_pct"]
    return {
        "block_id": f"holdings_by_sector_{n:02d}",
        "extra_facts": facts,
        "type": "holdings_by_sector",
        "title": "Holdings by sector",
        "subtitle": "Every position held, grouped by sector. Market values "
                    "use the most recent available prices.",
        "data": {"groups": groups,
                 "total_market": round(sum(g["market_value"] for g in groups), 2),
                 "total_cost": round(sum(g["cost_value"] for g in groups), 2),
                 "total_unreal": round(sum(g["unrealised"] for g in groups), 2)},
        "source_refs": ["portfolio_value"],
    }


def sector_analysis(s, n: int) -> Dict[str, Any]:
    """The same book, one row per sector, split developed vs emerging."""
    groups = by_sector(positions(s.client_id, s.portfolio_value))
    facts = {}
    for g in groups:
        key = g["sector"].replace(" ", "_")
        facts[f"sector.{key}"] = g["weight_pct"]
        facts[f"sector_value.{key}"] = g["market_value"]
    for r, p in REGIONS:
        facts[f"region.{r.replace(' ', '_')}"] = p
    facts["equity_total"] = round(sum(g["market_value"] for g in groups), 2)
    return {
        "block_id": f"sector_analysis_{n:02d}",
        "extra_facts": facts,
        "type": "sector_analysis",
        "title": "Sector analysis",
        "subtitle": "Equity holdings analysed by sector.",
        "data": {"regions": [{"region": r, "weight_pct": p} for r, p in REGIONS],
                 "rows": [{"sector": g["sector"], "value": g["market_value"],
                           "weight_pct": g["weight_pct"]} for g in groups],
                 "total": round(sum(g["market_value"] for g in groups), 2)},
        "source_refs": ["portfolio_value"],
    }


# ────────────────────────────────────────────────────────────── renderers
#
# Kept here rather than in generate.py's if/elif: these five carry a whole
# document's worth of markup, and folding them in would bury the blocks
# every report uses under the ones only one template does.

def _esc(t: Any) -> str:
    import html
    return html.escape(str(t if t is not None else ""))


def _T(text: str) -> str:
    """Translate a heading into the report's language.

    The report this is modelled on is German; this module writes English and
    lets the label table translate, exactly as every other block does. That
    is why there is no German in this file.
    """
    from .generate import _T as _translate
    return _translate(text)


def _money(v: float) -> str:
    from .generate import _money as _m
    return _m(v)


def _pct(v: float) -> str:
    from .generate import _RENDER_LOCALE
    from .locales import format_number
    return format_number(float(v), _RENDER_LOCALE.get() or "en", 2) + "%"


def _num(v: float, dp: int = 2) -> str:
    from .generate import _RENDER_LOCALE
    from .locales import format_number
    return format_number(float(v), _RENDER_LOCALE.get() or "en", dp)


def r_cover(d: Dict[str, Any]) -> str:
    items = "".join(
        f'<li><span>{_esc(_T(label))}</span><b>{page}</b></li>'
        for label, page in d.get("contents", []))
    # The risk profile sits with the mandate metadata, labelled. It is what
    # the band column in the next block checks the portfolio against, so a
    # reader needs to know which profile they are being measured on - and an
    # unlabelled "Moderate" floating above a name tells them nothing.
    meta = "".join(
        f'<div><span>{_esc(_T(k))}</span><b>{_esc(v)}</b></div>'
        for k, v in (("Risk profile", d.get("profile")),
                     ("Period", d.get("period")),
                     ("Valuation date", d.get("as_of")),
                     ("Portfolio", d.get("portfolio_no"))) if v)
    return (
        f'<div class="wcover">'
        f'<div class="wc-conf">{_esc(_T(d.get("confidential", "")))}</div>'
        f'<div class="wc-band"><h1>{_esc(_T(d.get("doc_title", "")))}</h1>'
        f'<p>{_esc(_T(d.get("mandate", "")))}</p></div>'
        f'<div class="wc-who"><b>{_esc(d.get("client", ""))}</b></div>'
        f'<div class="wc-meta">{meta}</div>'
        f'<h4>{_esc(_T("Contents"))}</h4><ul class="wc-toc">{items}</ul>'
        f'</div>')


def r_asset_classes(d: Dict[str, Any]) -> str:
    body = "".join(
        f'<tr><td class="l">{_esc(_T(r["asset_class"]))}</td>'
        f'<td>{_money(r["value"])}</td><td>{_pct(r["weight_pct"])}</td>'
        f'<td>{_num(r["lo"], 0)}% - {_num(r["hi"], 0)}%</td>'
        f'<td class="{"wok" if r["ok"] else "wbad"}">'
        f'{"&#10004;" if r["ok"] else "&#10006;"}</td></tr>'
        for r in d.get("rows", []))
    return (
        f'<table class="wtab"><tr><th class="l">{_esc(_T("Asset class"))}</th>'
        f'<th>{_esc(_T("Amount"))}</th><th>{_esc(_T("Share"))}</th>'
        f'<th>{_esc(_T("Mandate range"))}</th>'
        f'<th>{_esc(_T("Within profile"))}</th></tr>{body}'
        f'<tr class="wtot"><td class="l">{_esc(_T("Total"))}</td>'
        f'<td>{_money(d.get("total_value", 0))}</td>'
        f'<td>{_pct(d.get("total_pct", 0))}</td><td></td><td></td></tr></table>')


_PIE = ["#1c6b62", "#4b8f88", "#7fb3ad", "#a9cbc7", "#cfe0de", "#8a9ba0",
        "#5b6b70", "#2f3e46"]


def r_currency_split(d: Dict[str, Any]) -> str:
    rows = d.get("rows", [])
    segs, legend, ang = [], [], -90.0
    for i, r in enumerate(rows):
        sweep = r["weight_pct"] / 100.0 * 360.0
        x1 = 60 + 52 * math.cos(math.radians(ang))
        y1 = 60 + 52 * math.sin(math.radians(ang))
        ang2 = ang + sweep
        x2 = 60 + 52 * math.cos(math.radians(ang2))
        y2 = 60 + 52 * math.sin(math.radians(ang2))
        segs.append(
            f'<path d="M60,60 L{x1:.2f},{y1:.2f} A52,52 0 '
            f'{1 if sweep > 180 else 0},1 {x2:.2f},{y2:.2f} Z" '
            f'fill="{_PIE[i % len(_PIE)]}" stroke="#fff" stroke-width="1"/>')
        legend.append(
            f'<li><i style="background:{_PIE[i % len(_PIE)]}"></i>'
            f'{_esc(r["currency"])} &middot; {_pct(r["weight_pct"])}</li>')
        ang = ang2
    return (f'<div class="wccy"><svg viewBox="0 0 120 120">{"".join(segs)}</svg>'
            f'<ul>{"".join(legend)}</ul></div>')


def r_holdings_by_sector(d: Dict[str, Any]) -> str:
    out = [f'<table class="wtab wpos"><tr>'
           f'<th class="l">{_esc(_T("Holding"))}</th>'
           f'<th>{_esc(_T("Quantity"))}</th><th>{_esc(_T("Currency"))}</th>'
           f'<th>{_esc(_T("Cost price"))}</th><th>{_esc(_T("Price"))}</th>'
           f'<th>{_esc(_T("Cost value"))}</th><th>{_esc(_T("Market value"))}</th>'
           f'<th>{_esc(_T("Unrealised"))}</th><th>{_esc(_T("Share"))}</th></tr>']
    for g in d.get("groups", []):
        out.append(
            f'<tr class="wgrp"><td class="l">{_esc(_T(g["sector"]))}</td>'
            f'<td colspan="4"></td><td>{_money(g["cost_value"])}</td>'
            f'<td>{_money(g["market_value"])}</td>'
            f'<td>{_money(g["unrealised"])}</td>'
            f'<td>{_pct(g["weight_pct"])}</td></tr>')
        for r in g.get("rows", []):
            up = (100.0 * r["unrealised"] / abs(r["cost_value"])
                  if r["cost_value"] else 0.0)
            neg = ' class="wneg"' if r["unrealised"] < 0 else ""
            out.append(
                f'<tr><td class="l"><b>{_esc(r["name"])}</b>'
                f'<span class="wsub">{_esc(r["isin"])} &middot; '
                f'{_esc(_T(r["sustain"]))} &middot; {_esc(_T(r["stance"]))}</span></td>'
                f'<td>{_num(r["qty"], 0)}</td><td>{_esc(r["currency"])}</td>'
                f'<td>{_num(r["cost_price"])}<span class="wsub">'
                f'{_num(r["fx"], 4)}</span></td>'
                f'<td>{_num(r["price"])}<span class="wsub">{_num(r["fx"], 4)}</span></td>'
                f'<td>{_money(r["cost_value"])}</td>'
                f'<td>{_money(r["market_value"])}<span class="wsub">'
                f'{_pct(r["ytd_pct"])}</span></td>'
                f'<td{neg}>{_money(r["unrealised"])}<span class="wsub">'
                f'{_pct(up)}</span></td>'
                f'<td>{_pct(r["weight_pct"])}</td></tr>')
    out.append(
        f'<tr class="wtot"><td class="l">{_esc(_T("Total equities"))}</td>'
        f'<td colspan="4"></td><td>{_money(d.get("total_cost", 0))}</td>'
        f'<td>{_money(d.get("total_market", 0))}</td>'
        f'<td>{_money(d.get("total_unreal", 0))}</td><td></td></tr></table>')
    return "".join(out)


def r_sector_analysis(d: Dict[str, Any]) -> str:
    rows = d.get("rows", [])
    mx = max((r["weight_pct"] for r in rows), default=1) or 1
    bars = "".join(
        f'<text x="150" y="{12 + i * 20 + 8}" font-size="8" text-anchor="end" '
        f'fill="#4b5563">{_esc(_T(r["sector"]))}</text>'
        f'<rect x="156" y="{12 + i * 20}" width="{r["weight_pct"] / mx * 150:.1f}" '
        f'height="11" fill="#2f3e46"/>'
        for i, r in enumerate(rows))
    body = "".join(
        f'<tr><td class="l">{_esc(_T(r["sector"]))}</td>'
        f'<td>{_money(r["value"])}</td><td>{_pct(r["weight_pct"])}</td></tr>'
        for r in rows)
    regions = "".join(
        f'<tr class="wgrp"><td class="l">{_esc(_T(r["region"]))}</td>'
        f'<td>{_money(d.get("total", 0) * r["weight_pct"] / 100.0)}</td>'
        f'<td>{_pct(r["weight_pct"])}</td></tr>'
        for r in d.get("regions", [])[:1])
    return (
        f'<div class="wsplit">'
        f'<svg viewBox="0 0 320 {max(60, 12 + len(rows) * 20 + 10)}">{bars}</svg>'
        f'<table class="wtab"><tr><th class="l">{_esc(_T("Sector"))}</th>'
        f'<th>{_esc(_T("Value"))}</th><th>{_esc(_T("Share"))}</th></tr>'
        f'{regions}{body}'
        f'<tr class="wtot"><td class="l">{_esc(_T("Total equities"))}</td>'
        f'<td>{_money(d.get("total", 0))}</td><td></td></tr></table></div>')


RENDERERS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "wealth_cover": r_cover,
    "asset_class_table": r_asset_classes,
    "currency_split": r_currency_split,
    "holdings_by_sector": r_holdings_by_sector,
    "sector_analysis": r_sector_analysis,
}
