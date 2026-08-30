"""Translation of the labels the CODE writes.

The dangerous property here is not whether a word is translated well. It is
whether translating a DISPLAY label accidentally translates a FACT KEY. The
same string does both jobs in the report structure, and getting it wrong
fails silently: facts stop resolving, blocks get dropped, and the client is
handed a thinner report with nothing logged.
"""

from __future__ import annotations

import copy

import pytest

from ape.reporting.labels import LABELS, localise, t


def _report():
    """A report shaped like the real ones — display labels and fact keys
    carrying the SAME string, which is the whole hazard."""
    return {
        "report_id": "R_TEST",
        "blocks": [
            {
                "block_id": "b1",
                "block_type": "allocation_donut",
                "title": "Asset allocation",
                "content_json": {
                    "segments": [
                        {"label": "US Equity", "value_pct": 62.8},
                        {"label": "Fixed Income", "value_pct": 8.2},
                    ]
                },
                "source_refs": ["alloc.US Equity", "alloc.Fixed Income"],
            },
            {
                "block_id": "b2",
                "block_type": "narrative",
                "content_json": {"text": "Your portfolio returned 4.74%."},
                "source_refs": ["quarter_return_pct"],
            },
        ],
    }


# ------------------------------------------------------- the dangerous one

def test_fact_keys_are_never_translated():
    """source_refs must survive a translation byte for byte.

    "US Equity" is both a chart label and the key `alloc.US Equity`.
    Translating the key breaks every lookup that depends on it, and does so
    without raising anything.
    """
    src = _report()
    out = localise(src, "nl")
    for a, b in zip(src["blocks"], out["blocks"]):
        assert a["source_refs"] == b["source_refs"]
    assert out["blocks"][0]["source_refs"] == ["alloc.US Equity",
                                               "alloc.Fixed Income"]


def test_display_label_is_translated_while_its_key_is_not():
    """The two must diverge — that divergence IS the feature."""
    out = localise(_report(), "nl")
    seg = out["blocks"][0]["content_json"]["segments"][0]
    assert seg["label"] == "Amerikaanse aandelen"
    assert out["blocks"][0]["source_refs"][0] == "alloc.US Equity"


def test_original_is_not_mutated():
    """localise returns a copy.

    The caller still needs the English original: the grounding allowlist is
    built from English fact names, and quietly rewriting the object it
    validated against would be a nasty surprise.
    """
    src = _report()
    before = copy.deepcopy(src)
    localise(src, "nl")
    assert src == before


# ----------------------------------------------------------- pass-through

def test_english_is_a_no_op():
    src = _report()
    assert localise(src, "en") is src
    assert localise(src, "") is src
    assert localise(src, None) is src


@pytest.mark.parametrize("name", [
    "US Dividend Leaders", "Aggregate Bond Index", "Emerging Markets Fund",
])
def test_fund_names_pass_through_untranslated(name):
    """Proper names of real instruments must not be renamed.

    A fund is called the same thing in every language; translating one
    would misname a holding the client actually owns.
    """
    assert t(name, "nl") == name


@pytest.mark.parametrize("code", ["2026Q2", "2025Q4"])
def test_period_codes_pass_through(code):
    assert t(code, "nl") == code


def test_unknown_label_falls_through_rather_than_blanking():
    """A label we forgot renders in English, not empty.

    English is visibly imperfect and gets reported. A blank renders as a
    nameless column and does not.
    """
    assert t("Some Label We Forgot", "nl") == "Some Label We Forgot"
    assert t("", "nl") == ""
    assert t(None, "nl") is None


# -------------------------------------------------------------- coverage

@pytest.mark.parametrize("locale", ["nl", "de", "fr", "es", "it"])
def test_every_label_covers_every_locale(locale):
    """A half-filled dictionary silently renders mixed-language reports."""
    missing = [k for k, v in LABELS.items() if locale not in v]
    assert not missing, f"{locale} missing: {missing}"


def test_asset_classes_are_all_covered():
    """These appear in every report, so a gap here is always visible."""
    for asset in ("US Equity", "Intl Equity", "Fixed Income",
                  "Alternatives", "Cash", "Real Assets"):
        assert asset in LABELS, f"{asset} has no translation"
        assert t(asset, "nl") != asset, f"{asset} not translated to Dutch"


def test_axis_categories_are_translated_but_source_refs_are_not():
    """The interactive chart's x-axis is a list of BARE STRINGS.

    localise() only ever walked lists of dicts, so an Arabic report rendered
    its attribution chart labelled "US Equity, Fixed Income, Cash" while the
    static SVG beside it was correct — two code paths, one reading
    translated data and one not.

    source_refs is also a list of bare strings, and those are grounding
    KEYS. This asserts both halves at once, because a fix that translated
    every string list would break the link between a figure and its source.
    """
    from ape.reporting.labels import localise

    report = {
        "language": "ar",
        "blocks": [{
            "block_id": "chart_02",
            "type": "chart",
            "data": {
                "kind": "bar",
                "x_categories": ["US Equity", "Fixed Income", "Cash"],
                "series": [{"label": "Contribution", "values": [1.94, 0.08, 0.07]}],
            },
            "source_refs": ["attr.US Equity", "attr.Fixed Income", "attr.Cash"],
        }],
    }
    out = localise(report, "ar")
    block = out["blocks"][0]

    cats = block["data"]["x_categories"]
    assert cats != ["US Equity", "Fixed Income", "Cash"], "axis was not translated"
    assert all(any("\u0600" <= ch <= "\u06ff" for ch in c) for c in cats)

    # Keys must survive untouched, or grounding stops resolving.
    assert block["source_refs"] == ["attr.US Equity", "attr.Fixed Income", "attr.Cash"]
    # Figures are never re-rendered by translation.
    assert block["data"]["series"][0]["values"] == [1.94, 0.08, 0.07]
    # And the caller's dict is not mutated.
    assert report["blocks"][0]["data"]["x_categories"] == ["US Equity", "Fixed Income", "Cash"]


def test_nested_list_labels_are_translated():
    """series[].points[].label is two levels down and used as axis text."""
    from ape.reporting.labels import localise

    report = {"language": "de", "blocks": [{
        "block_id": "c", "type": "chart",
        "data": {"series": [{"label": "Portfolio",
                             "points": [{"label": "Cash", "value": 1.0}]}]},
    }]}
    pts = localise(report, "de")["blocks"][0]["data"]["series"][0]["points"]
    assert pts[0]["label"] != "Cash", "nested label was not translated"
    assert pts[0]["value"] == 1.0
