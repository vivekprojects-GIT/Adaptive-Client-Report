"""Translations for the labels the CODE writes, not the model.

WHY THIS IS SEPARATE FROM THE PROSE
-----------------------------------
The narrative is written by the model, natively in the client's language.
But tables, charts and KPI tiles are built in code, and their labels were
English string literals. So a Dutch report came out as Dutch prose wrapped
around English furniture — "US Equity", "Advisory fee", "At a glance" —
which reads as a half-finished translation rather than a Dutch document.

These are a closed set. There are perhaps forty of them, they change only
when a block type is added, and they must render identically every time —
so they are a dictionary, not a model call. Sending "Fixed Income" to an
LLM per report would be slower, cost money, and introduce variation into
the one part of the document that should never vary.

THE RULE THAT MATTERS
---------------------
A LABEL IS NOT A KEY. The same string does both jobs in the report
structure:

    {"label": "US Equity", ...}                 <- display, translate this
    "source_refs": ["alloc.US Equity"]          <- fact key, NEVER translate

Translating the second breaks the grounding gate's lookup, and the failure
is quiet: facts stop resolving, blocks get dropped, and the client is
handed a thinner report with no error anywhere. `localise` below touches
display fields only and is deliberately explicit about which ones.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

# key -> {locale: text}. English is the key itself, so an untranslated
# string falls through unchanged rather than rendering blank.
LABELS: Dict[str, Dict[str, str]] = {
    # ── asset classes ────────────────────────────────────────────────────
    "US Equity":        {"nl": "Amerikaanse aandelen", "de": "US-Aktien",
                         "fr": "Actions américaines",  "es": "Renta variable EE.UU.",
                         "it": "Azioni USA"},
    "Intl Equity":      {"nl": "Internationale aandelen", "de": "Internationale Aktien",
                         "fr": "Actions internationales", "es": "Renta variable internacional",
                         "it": "Azioni internazionali"},
    "Fixed Income":     {"nl": "Vastrentende waarden", "de": "Anleihen",
                         "fr": "Obligations", "es": "Renta fija",
                         "it": "Obbligazioni"},
    "Alternatives":     {"nl": "Alternatieve beleggingen", "de": "Alternative Anlagen",
                         "fr": "Investissements alternatifs", "es": "Inversiones alternativas",
                         "it": "Investimenti alternativi"},
    "Real Assets":      {"nl": "Reële activa", "de": "Sachwerte",
                         "fr": "Actifs réels", "es": "Activos reales",
                         "it": "Attività reali"},
    "Cash":             {"nl": "Liquide middelen", "de": "Barmittel",
                         "fr": "Liquidités", "es": "Efectivo", "it": "Liquidità"},

    # ── block titles ─────────────────────────────────────────────────────
    "Asset allocation": {"nl": "Vermogensverdeling", "de": "Vermögensaufteilung",
                         "fr": "Répartition des actifs", "es": "Distribución de activos",
                         "it": "Allocazione del patrimonio"},
    "Allocation detail": {"nl": "Verdeling in detail", "de": "Aufteilung im Detail",
                         "fr": "Détail de la répartition", "es": "Detalle de la distribución",
                         "it": "Dettaglio dell'allocazione"},
    "Allocation vs strategic target":
                        {"nl": "Verdeling versus strategisch doel",
                         "de": "Aufteilung gegenüber Zielallokation",
                         "fr": "Répartition par rapport à l'objectif",
                         "es": "Distribución frente al objetivo",
                         "it": "Allocazione rispetto all'obiettivo"},
    "Fees and costs":   {"nl": "Kosten", "de": "Gebühren und Kosten",
                         "fr": "Frais et coûts", "es": "Comisiones y costes",
                         "it": "Commissioni e costi"},
    "What you paid":    {"nl": "Wat u heeft betaald", "de": "Was Sie gezahlt haben",
                         "fr": "Ce que vous avez payé", "es": "Lo que ha pagado",
                         "it": "Quanto ha pagato"},
    "At a glance":      {"nl": "In één oogopslag", "de": "Auf einen Blick",
                         "fr": "En un coup d'œil", "es": "De un vistazo",
                         "it": "In sintesi"},
    "Performance vs benchmark":
                        {"nl": "Rendement versus benchmark",
                         "de": "Wertentwicklung gegenüber Benchmark",
                         "fr": "Performance par rapport à l'indice",
                         "es": "Rentabilidad frente al índice",
                         "it": "Rendimento rispetto al benchmark"},
    "Contribution to return":
                        {"nl": "Bijdrage aan het rendement",
                         "de": "Beitrag zur Wertentwicklung",
                         "fr": "Contribution à la performance",
                         "es": "Contribución a la rentabilidad",
                         "it": "Contributo al rendimento"},
    "Return by period": {"nl": "Rendement per periode", "de": "Rendite nach Periode",
                         "fr": "Performance par période", "es": "Rentabilidad por periodo",
                         "it": "Rendimento per periodo"},
    "Return over time": {"nl": "Rendement in de tijd", "de": "Rendite im Zeitverlauf",
                         "fr": "Performance dans le temps", "es": "Rentabilidad en el tiempo",
                         "it": "Rendimento nel tempo"},
    "Return this period": {"nl": "Rendement deze periode", "de": "Rendite in dieser Periode",
                         "fr": "Performance sur la période", "es": "Rentabilidad del periodo",
                         "it": "Rendimento del periodo"},
    "Ahead of benchmark": {"nl": "Voor op de benchmark", "de": "Vor der Benchmark",
                         "fr": "En avance sur l'indice", "es": "Por delante del índice",
                         "it": "In vantaggio sul benchmark"},
    "Risk":             {"nl": "Risico", "de": "Risiko", "fr": "Risque",
                         "es": "Riesgo", "it": "Rischio"},
    "Top contributors to return":
                        {"nl": "Grootste bijdragen aan het rendement",
                         "de": "Größte Renditebeiträge",
                         "fr": "Principaux contributeurs à la performance",
                         "es": "Mayores contribuciones a la rentabilidad",
                         "it": "Principali contributi al rendimento"},
    "Top detractors from return":
                        {"nl": "Grootste negatieve bijdragen",
                         "de": "Größte Renditebelastungen",
                         "fr": "Principaux détracteurs de la performance",
                         "es": "Mayores detracciones de la rentabilidad",
                         "it": "Principali detrattori del rendimento"},
    "Behind benchmark": {"nl": "Achter op de benchmark", "de": "Hinter der Benchmark",
                         "fr": "En retard sur l'indice", "es": "Por detrás del índice",
                         "it": "In ritardo sul benchmark"},
    "Portfolio Growth": {"nl": "Groei van de portefeuille", "de": "Portfoliowachstum",
                         "fr": "Croissance du portefeuille", "es": "Crecimiento de la cartera",
                         "it": "Crescita del portafoglio"},
    "Portfolio value and recent performance":
                        {"nl": "Portefeuillewaarde en recent rendement",
                         "de": "Portfoliowert und jüngste Wertentwicklung",
                         "fr": "Valeur du portefeuille et performance récente",
                         "es": "Valor de la cartera y rentabilidad reciente",
                         "it": "Valore del portafoglio e rendimento recente"},
    "Key takeaways":    {"nl": "Belangrijkste punten", "de": "Wichtigste Erkenntnisse",
                         "fr": "Points clés", "es": "Puntos clave",
                         "it": "Punti chiave"},
    "What these terms mean":
                        {"nl": "Wat deze termen betekenen",
                         "de": "Was diese Begriffe bedeuten",
                         "fr": "Ce que signifient ces termes",
                         "es": "Qué significan estos términos",
                         "it": "Cosa significano questi termini"},

    # ── row and tile labels ──────────────────────────────────────────────
    "Advisory fee":     {"nl": "Advieskosten", "de": "Beratungsgebühr",
                         "fr": "Frais de conseil", "es": "Comisión de asesoramiento",
                         "it": "Commissione di consulenza"},
    "Fund expenses":    {"nl": "Fondskosten", "de": "Fondskosten",
                         "fr": "Frais de fonds", "es": "Gastos del fondo",
                         "it": "Spese del fondo"},
    "Total":            {"nl": "Totaal", "de": "Gesamt", "fr": "Total",
                         "es": "Total", "it": "Totale"},
    "Portfolio value":  {"nl": "Portefeuillewaarde", "de": "Portfoliowert",
                         "fr": "Valeur du portefeuille", "es": "Valor de la cartera",
                         "it": "Valore del portafoglio"},
    "Portfolio return": {"nl": "Portefeuillerendement", "de": "Portfoliorendite",
                         "fr": "Performance du portefeuille",
                         "es": "Rentabilidad de la cartera",
                         "it": "Rendimento del portafoglio"},
    "Portfolio":        {"nl": "Portefeuille", "de": "Portfolio",
                         "fr": "Portefeuille", "es": "Cartera", "it": "Portafoglio"},
    "Benchmark":        {"nl": "Benchmark", "de": "Benchmark", "fr": "Indice de référence",
                         "es": "Índice de referencia", "it": "Benchmark"},
    "Return":           {"nl": "Rendement", "de": "Rendite", "fr": "Performance",
                         "es": "Rentabilidad", "it": "Rendimento"},
    "Risk level":       {"nl": "Risiconiveau", "de": "Risikoniveau",
                         "fr": "Niveau de risque", "es": "Nivel de riesgo",
                         "it": "Livello di rischio"},
    "Target":           {"nl": "Doel", "de": "Ziel", "fr": "Objectif",
                         "es": "Objetivo", "it": "Obiettivo"},
    "Actual":           {"nl": "Werkelijk", "de": "Ist", "fr": "Réel",
                         "es": "Real", "it": "Effettivo"},
    "Contribution":     {"nl": "Bijdrage", "de": "Beitrag", "fr": "Contribution",
                         "es": "Contribución", "it": "Contributo"},
    "Cumulative":       {"nl": "Cumulatief", "de": "Kumuliert", "fr": "Cumulé",
                         "es": "Acumulado", "it": "Cumulativo"},
    "Fees":             {"nl": "Kosten", "de": "Gebühren", "fr": "Frais",
                         "es": "Comisiones", "it": "Commissioni"},

    # ── risk levels ──────────────────────────────────────────────────────
    "Conservative":     {"nl": "Defensief", "de": "Konservativ", "fr": "Prudent",
                         "es": "Conservador", "it": "Conservativo"},
    "Moderate":         {"nl": "Neutraal", "de": "Ausgewogen", "fr": "Modéré",
                         "es": "Moderado", "it": "Moderato"},
    "Growth":           {"nl": "Groei", "de": "Wachstum", "fr": "Croissance",
                         "es": "Crecimiento", "it": "Crescita"},
    "Aggressive":       {"nl": "Offensief", "de": "Offensiv", "fr": "Dynamique",
                         "es": "Agresivo", "it": "Aggressivo"},
}


# Deliberately NOT translated, and this is a decision rather than an
# omission:
#
#   Fund and index names   "US Dividend Leaders", "Aggregate Bond Index"
#       Proper names of real instruments. A fund is called the same thing in
#       every language, and renaming one in a client's report would misname
#       an actual holding they own.
#
#   Period codes           "2026Q2"
#       Identifiers, not words.
#
#   Narrative and callout text
#       Written by the model, already in the client's language. Passing it
#       through a dictionary would be a second, worse translation of text
#       that is already correct.
#
# All three fall through `t` unchanged because they are simply absent from
# LABELS — no special-casing needed, which is why the fall-through default
# matters more than it looks.


def t(text: Optional[str], locale: Optional[str]) -> Optional[str]:
    """Translate one label. Unknown text and English pass through unchanged.

    Falling through rather than raising or blanking is deliberate: a label
    we forgot to add renders in English, which is visibly imperfect and
    gets reported. A blank renders as a nameless column, which does not.
    """
    if not text or not locale or locale == "en":
        return text
    entry = LABELS.get(text)
    if not entry:
        return text
    return entry.get(locale, text)


# Display fields only. Everything absent from this list — source_refs,
# block_id, block_type, format, unit, tone — is structural and must survive
# untouched. Adding a key here is a deliberate act, which is the point.
_TEXT_FIELDS = ("title", "label", "name", "asset_class")
_LIST_FIELDS = ("segments", "items", "rows", "bars", "points", "series")


def localise(report: Dict[str, Any], locale: Optional[str]) -> Dict[str, Any]:
    """Return a copy of the report with its CODE-WRITTEN labels translated.

    A copy, not a mutation: the caller may still need the English original
    (the grounding allowlist is built from English fact keys), and quietly
    rewriting the object it validated against would be a nasty surprise.

    Narrative prose is left alone — the model already wrote it in the right
    language, and re-translating it here would be a second, worse pass over
    text that is already correct.
    """
    if not locale or locale == "en":
        return report

    out = copy.deepcopy(report)
    for block in out.get("blocks", []):
        if not isinstance(block, dict):
            continue
        if block.get("title"):
            block["title"] = t(block["title"], locale)
        data = block.get("content_json") or block.get("data")
        if isinstance(data, dict):
            _localise_data(data, locale)
    return out


def _localise_data(data: Dict[str, Any], locale: str) -> None:
    for field in _TEXT_FIELDS:
        if isinstance(data.get(field), str):
            data[field] = t(data[field], locale)
    for field in _LIST_FIELDS:
        rows = data.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                for f in _TEXT_FIELDS:
                    if isinstance(row.get(f), str):
                        row[f] = t(row[f], locale)
