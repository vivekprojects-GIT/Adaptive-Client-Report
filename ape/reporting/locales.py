"""Locale rules: how a language writes numbers, and what to call things.

WHY THIS EXISTS AT ALL
----------------------
Translating a report is not a text problem. It is a NUMBER problem, and the
number problem is the dangerous half.

English writes one-point-two-million as   1,234,567.89
Dutch writes the same value as            1.234.567,89

The separators are swapped. Feed a Dutch figure to a parser that assumes
English and "1.234.567,89" reads as 1.234 — three orders of magnitude wrong,
silently. The grounding gate is the one thing standing between a client and
an invented figure, so a locale bug there is not a formatting annoyance; it
is the gate failing open.

So locale is resolved ONCE, here, and every part of the system that reads or
writes a number asks this module rather than assuming a convention.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
No translation of the FIGURES themselves. A number means the same thing in
every language; only its rendering changes. `format_number` re-renders a
float, it never re-computes one — so a translated report cannot drift from
the English one by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Locale:
    """One language's conventions.

    `code` is the short tag used everywhere else in the system (stored on
    the client row, passed to the composer, sent to the model).
    """
    code: str
    label: str            # shown in the admin UI
    endonym: str          # what speakers call it, for the client-facing side
    thousands: str
    decimal: str
    # What the model is told to write in. Kept as a full phrase rather than
    # a bare code because "write in nl" is a weaker instruction than
    # "write in Dutch (Nederlands)".
    prompt_name: str


LOCALES: Dict[str, Locale] = {
    "en": Locale("en", "English", "English", ",", ".", "English"),
    "nl": Locale("nl", "Dutch", "Nederlands", ".", ",", "Dutch (Nederlands)"),
    "de": Locale("de", "German", "Deutsch", ".", ",", "German (Deutsch)"),
    "fr": Locale("fr", "French", "Français", " ", ",",
                 "French (Français)"),
    "es": Locale("es", "Spanish", "Español", ".", ",", "Spanish (Español)"),
    "it": Locale("it", "Italian", "Italiano", ".", ",", "Italian (Italiano)"),
}

DEFAULT_LOCALE = "en"


# Country -> the language a report for that country defaults to.
#
# A DEFAULT, never a rule. Belgium reads Dutch or French depending on the
# client, Switzerland three ways, and plenty of Dutch clients want their
# reporting in English. So the advisor picks a country and the language
# fills itself in, and they can still change it — auto-selection that
# cannot be overridden would be worse than no auto-selection at all.
COUNTRIES: Dict[str, Dict[str, str]] = {
    # ── English-speaking ─────────────────────────────────────────────────
    "GB": {"label": "United Kingdom",   "language": "en", "currency": "£"},
    "IE": {"label": "Ireland",          "language": "en", "currency": "€"},
    "US": {"label": "United States",    "language": "en", "currency": "$"},
    "CA": {"label": "Canada",           "language": "en", "currency": "$"},
    "AU": {"label": "Australia",        "language": "en", "currency": "$"},
    "NZ": {"label": "New Zealand",      "language": "en", "currency": "$"},
    "SG": {"label": "Singapore",        "language": "en", "currency": "$"},
    "HK": {"label": "Hong Kong SAR",    "language": "en", "currency": "$"},
    "ZA": {"label": "South Africa",     "language": "en", "currency": "R"},
    "AE": {"label": "United Arab Emirates", "language": "en", "currency": "AED"},
    "IN": {"label": "India",            "language": "en", "currency": "₹"},
    "MT": {"label": "Malta",            "language": "en", "currency": "€"},
    "CY": {"label": "Cyprus",           "language": "en", "currency": "€"},
    "JE": {"label": "Jersey",           "language": "en", "currency": "£"},
    "GG": {"label": "Guernsey",         "language": "en", "currency": "£"},
    "IM": {"label": "Isle of Man",      "language": "en", "currency": "£"},

    # ── Dutch ────────────────────────────────────────────────────────────
    "NL": {"label": "Netherlands",      "language": "nl", "currency": "€"},
    # Belgium reads Dutch OR French depending on the client, so the default
    # here is a coin toss that the advisor is expected to override. That is
    # exactly why the language dropdown is not read-only.
    "BE": {"label": "Belgium",          "language": "nl", "currency": "€"},
    "SR": {"label": "Suriname",         "language": "nl", "currency": "$"},

    # ── German ───────────────────────────────────────────────────────────
    "DE": {"label": "Germany",          "language": "de", "currency": "€"},
    "AT": {"label": "Austria",          "language": "de", "currency": "€"},
    "CH": {"label": "Switzerland",      "language": "de", "currency": "CHF"},
    "LI": {"label": "Liechtenstein",    "language": "de", "currency": "CHF"},

    # ── French ───────────────────────────────────────────────────────────
    "FR": {"label": "France",           "language": "fr", "currency": "€"},
    "LU": {"label": "Luxembourg",       "language": "fr", "currency": "€"},
    "MC": {"label": "Monaco",           "language": "fr", "currency": "€"},

    # ── Spanish ──────────────────────────────────────────────────────────
    "ES": {"label": "Spain",            "language": "es", "currency": "€"},
    "MX": {"label": "Mexico",           "language": "es", "currency": "$"},
    "AR": {"label": "Argentina",        "language": "es", "currency": "$"},
    "CL": {"label": "Chile",            "language": "es", "currency": "$"},
    "CO": {"label": "Colombia",         "language": "es", "currency": "$"},
    "PE": {"label": "Peru",             "language": "es", "currency": "S/"},
    "UY": {"label": "Uruguay",          "language": "es", "currency": "$"},

    # ── Italian ──────────────────────────────────────────────────────────
    "IT": {"label": "Italy",            "language": "it", "currency": "€"},
    "SM": {"label": "San Marino",       "language": "it", "currency": "€"},

    # ── Markets whose primary language is NOT yet supported ──────────────
    # Listed deliberately rather than omitted. An advisor with a client in
    # Tokyo needs to be able to pick Japan; defaulting them to English is
    # honest and correct, whereas leaving the country out of the list looks
    # like the platform cannot serve them at all. Add the language to
    # LOCALES and these switch over with no other change.
    "PT": {"label": "Portugal",         "language": "en", "currency": "€"},
    "BR": {"label": "Brazil",           "language": "en", "currency": "R$"},
    "SE": {"label": "Sweden",           "language": "en", "currency": "kr"},
    "NO": {"label": "Norway",           "language": "en", "currency": "kr"},
    "DK": {"label": "Denmark",          "language": "en", "currency": "kr"},
    "FI": {"label": "Finland",          "language": "en", "currency": "€"},
    "PL": {"label": "Poland",           "language": "en", "currency": "zł"},
    "CZ": {"label": "Czechia",          "language": "en", "currency": "Kč"},
    "GR": {"label": "Greece",           "language": "en", "currency": "€"},
    "JP": {"label": "Japan",            "language": "en", "currency": "¥"},
    "CN": {"label": "China",            "language": "en", "currency": "¥"},
    "KR": {"label": "South Korea",      "language": "en", "currency": "₩"},
    "SA": {"label": "Saudi Arabia",     "language": "en", "currency": "SAR"},
    "IL": {"label": "Israel",           "language": "en", "currency": "₪"},
    "TR": {"label": "Türkiye",          "language": "en", "currency": "₺"},
}

DEFAULT_COUNTRY = "GB"


def language_for_country(country: Optional[str]) -> str:
    """The language to preselect when an advisor picks a country."""
    if not country:
        return DEFAULT_LOCALE
    row = COUNTRIES.get(str(country).strip().upper())
    return row["language"] if row else DEFAULT_LOCALE


def currency_for_country(country: Optional[str]) -> str:
    row = COUNTRIES.get(str(country or "").strip().upper())
    return row["currency"] if row else "£"


def countries() -> list:
    """For the advisor dropdown, alphabetical by label."""
    return sorted(
        ({"code": c, "label": v["label"], "language": v["language"],
          "currency": v["currency"]} for c, v in COUNTRIES.items()),
        key=lambda r: r["label"])


def get(code: Optional[str]) -> Locale:
    """Resolve a code to a Locale, falling back to English.

    Falls back rather than raising: an unknown code on one client's row must
    not take down report generation for everyone. The fallback is the
    safe direction — English formatting on a Dutch report is visibly odd and
    gets reported; a crash mid-batch is worse and a wrong number is worst.
    """
    if not code:
        return LOCALES[DEFAULT_LOCALE]
    return LOCALES.get(str(code).strip().lower()[:2], LOCALES[DEFAULT_LOCALE])


def supported() -> list:
    return [{"code": l.code, "label": l.label, "endonym": l.endonym}
            for l in LOCALES.values()]


# ---------------------------------------------------------------- parsing

def to_float(raw: str, code: Optional[str] = None) -> Optional[float]:
    """Read a locale-formatted number string into a float.

    Returns None when the string is not a number in this locale, rather
    than guessing. A caller that cannot parse a figure must treat it as
    unverified, never as zero.

    The order matters: strip the thousands separator FIRST, then swap the
    decimal separator to a period. Doing it the other way round on Dutch
    turns "1.234,56" into "1234.56" only by luck of ordering, and breaks
    outright on locales where the two characters differ from these.
    """
    loc = get(code)
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Currency symbols and spaces are not part of the value.
    for ch in "£$€   ":
        s = s.replace(ch, "")
    s = s.replace(loc.thousands, "")
    if loc.decimal != ".":
        s = s.replace(loc.decimal, ".")
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------- rendering

def format_number(value: float, code: Optional[str] = None,
                  dp: int = 2) -> str:
    """Render a float using this locale's separators.

    Never re-computes: the caller supplies the value, this only chooses how
    it looks. That is what keeps a translated report numerically identical
    to the English one.
    """
    loc = get(code)
    neg = value < 0
    s = f"{abs(float(value)):,.{dp}f}"        # always English first
    whole, _, frac = s.partition(".")
    whole = whole.replace(",", "\x00")        # placeholder, then substitute
    whole = whole.replace("\x00", loc.thousands)
    out = whole + (loc.decimal + frac if frac else "")
    return ("-" + out) if neg else out


def format_currency(value: float, symbol: str = "£",
                    code: Optional[str] = None, dp: int = 2) -> str:
    return f"{symbol}{format_number(value, code, dp)}"
