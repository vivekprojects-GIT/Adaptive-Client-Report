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
    "Period":           {"nl": "Periode", "de": "Zeitraum", "fr": "Période",
                         "es": "Periodo", "it": "Periodo"},
    "Difference":       {"nl": "Verschil", "de": "Differenz", "fr": "Écart",
                         "es": "Diferencia", "it": "Differenza"},
    "Others":           {"nl": "Overige", "de": "Sonstige", "fr": "Autres",
                         "es": "Otros", "it": "Altri"},
    "Asset class":      {"nl": "Beleggingscategorie", "de": "Anlageklasse",
                         "fr": "Classe d'actifs", "es": "Clase de activo",
                         "it": "Classe di attività"},
    "Weight":           {"nl": "Gewicht", "de": "Gewichtung", "fr": "Pondération",
                         "es": "Peso", "it": "Peso"},
    "Value":            {"nl": "Waarde", "de": "Wert", "fr": "Valeur",
                         "es": "Valor", "it": "Valore"},
    "Fees":             {"nl": "Kosten", "de": "Gebühren", "fr": "Frais",
                         "es": "Comisiones", "it": "Commissioni"},

    # ── explainer terms, disclosures and source lines ────────────────────
    "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
        {"nl": "Een referentiemix waarmee het rendement wordt beoordeeld. Deze verslaan "
               "betekent dat uw portefeuille het beter deed dan de markt bij dat risiconiveau.",
         "de": "Eine Vergleichsmischung zur Beurteilung der Wertentwicklung. Sie zu schlagen "
               "bedeutet, dass Ihr Portfolio besser abschnitt als der Markt bei diesem Risiko.",
         "fr": "Un panier de référence servant à juger la performance. Le battre signifie que "
               "votre portefeuille a fait mieux que le marché à ce niveau de risque.",
         "es": "Una combinación de referencia para juzgar la rentabilidad. Superarla significa "
               "que su cartera lo hizo mejor que el mercado a ese nivel de riesgo.",
         "it": "Un paniere di riferimento per valutare il rendimento. Batterlo significa che il "
               "suo portafoglio ha fatto meglio del mercato a quel livello di rischio."},
    "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
        {"nl": "Hoeveel elk onderdeel van de portefeuille heeft bijgedragen aan of afgehaald van "
               "het totale rendement. De bijdragen tellen op tot het rendement dat u werkelijk kreeg.",
         "de": "Wie viel jeder Teil des Portfolios zur Gesamtrendite beigetragen oder ihr entzogen "
               "hat. Die Beiträge ergeben zusammen die tatsächlich erzielte Rendite.",
         "fr": "Ce que chaque partie du portefeuille a ajouté à la performance totale ou lui a "
               "retiré. Les contributions s'additionnent pour donner la performance réellement obtenue.",
         "es": "Cuánto aportó o restó cada parte de la cartera a la rentabilidad total. Las "
               "contribuciones suman la rentabilidad que realmente obtuvo.",
         "it": "Quanto ogni parte del portafoglio ha aggiunto o sottratto al rendimento totale. "
               "I contributi sommati danno il rendimento effettivamente ottenuto."},
    "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
        {"nl": "De langetermijnverdeling die is afgesproken voor uw risicoprofiel. Posities wijken "
               "hiervan af als markten bewegen en worden bij herbalancering teruggebracht.",
         "de": "Die langfristige Aufteilung für Ihr Risikoprofil. Positionen weichen davon ab, wenn "
               "sich Märkte bewegen, und werden beim Rebalancing zurückgeführt.",
         "fr": "La répartition à long terme convenue pour votre profil de risque. Les positions s'en "
               "écartent avec les marchés et y sont ramenées lors du rééquilibrage.",
         "es": "La combinación a largo plazo acordada para su perfil de riesgo. Las posiciones se "
               "desvían con los mercados y se devuelven en el reequilibrio.",
         "it": "La composizione di lungo periodo concordata per il suo profilo di rischio. Le "
               "posizioni se ne allontanano con i mercati e vi tornano al ribilanciamento."},
    "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
        {"nl": "Elk getoond rendement is na aftrek van kosten en weerspiegelt dus wat u werkelijk verdiende.",
         "de": "Jede gezeigte Rendite versteht sich nach Abzug der Gebühren und spiegelt damit Ihren tatsächlichen Ertrag.",
         "fr": "Chaque performance affichée est nette de frais et reflète donc ce que vous avez réellement gagné.",
         "es": "Cada rentabilidad mostrada es neta de comisiones, por lo que refleja lo que realmente ganó.",
         "it": "Ogni rendimento mostrato è al netto delle commissioni e riflette quindi quanto ha realmente guadagnato."},

    # Full sentences, but still a CLOSED set written by code, so the same
    # dictionary rule applies: fixed wording, rendered identically every
    # time. A real deployment replaces the disclosure text per jurisdiction
    # rather than translating ours — the words a regulator requires are not
    # a translation of the words another regulator requires.
    "Valuations":       {"nl": "Waarderingen", "de": "Bewertungen",
                         "fr": "Valorisations", "es": "Valoraciones",
                         "it": "Valutazioni"},
    "as at":            {"nl": "per", "de": "zum", "fr": "au",
                         "es": "a fecha de", "it": "al"},
    "Portfolio vs benchmark":
                        {"nl": "Portefeuille versus benchmark",
                         "de": "Portfolio gegenüber Benchmark",
                         "fr": "Portefeuille contre indice",
                         "es": "Cartera frente al índice",
                         "it": "Portafoglio contro benchmark"},
    "last column is drift from target":
                        {"nl": "laatste kolom is de afwijking van het doel",
                         "de": "letzte Spalte ist die Abweichung vom Ziel",
                         "fr": "la dernière colonne est l'écart par rapport à l'objectif",
                         "es": "la última columna es la desviación del objetivo",
                         "it": "l'ultima colonna è lo scostamento dall'obiettivo"},
    "Strategic target": {"nl": "Strategisch doel", "de": "Strategisches Ziel",
                         "fr": "Objectif stratégique", "es": "Objetivo estratégico",
                         "it": "Obiettivo strategico"},
    "Net of fees":      {"nl": "Na aftrek van kosten", "de": "Nach Gebühren",
                         "fr": "Net de frais", "es": "Neto de comisiones",
                         "it": "Al netto delle commissioni"},
    "Contribution":     {"nl": "Bijdrage", "de": "Beitrag", "fr": "Contribution",
                         "es": "Contribución", "it": "Contributo"},
    "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
                        {"nl": "Resultaten uit het verleden bieden geen garantie voor de toekomst. "
                               "Bedragen zijn na aftrek van kosten, tenzij anders vermeld.",
                         "de": "Die frühere Wertentwicklung ist kein Indikator für künftige Ergebnisse. "
                               "Beträge verstehen sich nach Gebühren, sofern nicht anders angegeben.",
                         "fr": "Les performances passées ne préjugent pas des performances futures. "
                               "Les montants sont nets de frais, sauf indication contraire.",
                         "es": "Las rentabilidades pasadas no garantizan resultados futuros. "
                               "Los importes son netos de comisiones, salvo indicación en contrario.",
                         "it": "I rendimenti passati non sono indicativi dei risultati futuri. "
                               "Gli importi sono al netto delle commissioni, salvo diversa indicazione."},
    "Give me a quick summary of this report.":
        {"nl": "Geef mij een korte samenvatting van dit rapport.",
         "de": "Gib mir eine kurze Zusammenfassung dieses Berichts.",
         "fr": "Donne-moi un bref résumé de ce rapport.",
         "es": "Dame un breve resumen de este informe.",
         "it": "Dammi un breve riassunto di questo rapporto."},
    "Explain the fees I paid this period.":
        {"nl": "Leg de kosten uit die ik deze periode heb betaald.",
         "de": "Erkläre die Gebühren, die ich in dieser Periode gezahlt habe.",
         "fr": "Explique les frais que j'ai payés sur cette période.",
         "es": "Explica las comisiones que pagué en este periodo.",
         "it": "Spiega le commissioni che ho pagato in questo periodo."},
    "How did I do against the benchmark?":
        {"nl": "Hoe deed ik het ten opzichte van de benchmark?",
         "de": "Wie habe ich im Vergleich zur Benchmark abgeschnitten?",
         "fr": "Comment me suis-je situé par rapport à l'indice ?",
         "es": "¿Cómo lo hice frente al índice de referencia?",
         "it": "Come sono andato rispetto al benchmark?"},
    # ── chart chips: the label shown, and the question a click sends ─────
    # Both translate. A chip whose LABEL is Dutch but whose QUESTION is
    # English sends an English question when clicked, and the thread drifts
    # back to English one click at a time.
    "Allocation donut": {"nl": "Verdeling (donut)", "de": "Aufteilung (Donut)",
                         "fr": "Répartition (donut)", "es": "Distribución (donut)",
                         "it": "Allocazione (donut)"},
    "Actual vs target": {"nl": "Werkelijk versus doel", "de": "Ist gegen Ziel",
                         "fr": "Réel contre objectif", "es": "Real frente a objetivo",
                         "it": "Effettivo contro obiettivo"},
    "Return drivers":   {"nl": "Wat het rendement bepaalde", "de": "Renditetreiber",
                         "fr": "Moteurs de performance", "es": "Motores de rentabilidad",
                         "it": "Motori del rendimento"},
    "Holdings treemap": {"nl": "Posities (boomkaart)", "de": "Positionen (Baumkarte)",
                         "fr": "Positions (treemap)", "es": "Posiciones (treemap)",
                         "it": "Posizioni (treemap)"},
    "You vs benchmark": {"nl": "U versus benchmark", "de": "Sie gegen Benchmark",
                         "fr": "Vous contre l'indice", "es": "Usted frente al índice",
                         "it": "Lei contro il benchmark"},
    "Fee breakdown":    {"nl": "Kostenverdeling", "de": "Gebührenaufteilung",
                         "fr": "Détail des frais", "es": "Desglose de comisiones",
                         "it": "Dettaglio delle commissioni"},
    "Money in and out": {"nl": "Geld in en uit", "de": "Zu- und Abflüsse",
                         "fr": "Entrées et sorties", "es": "Entradas y salidas",
                         "it": "Entrate e uscite"},

    "Show me my asset allocation as a donut chart.":
        {"nl": "Laat mijn vermogensverdeling zien als een donutdiagram.",
         "de": "Zeig mir meine Vermögensaufteilung als Tortendiagramm.",
         "fr": "Montre-moi ma répartition d'actifs en donut.",
         "es": "Muestra mi distribución de activos en un gráfico de donut.",
         "it": "Mostra la mia allocazione come grafico a donut."},
    "Show me my allocation against target as a bar chart.":
        {"nl": "Laat mijn verdeling versus doel zien als een staafdiagram.",
         "de": "Zeig mir meine Aufteilung gegenüber dem Ziel als Balkendiagramm.",
         "fr": "Montre-moi ma répartition par rapport à l'objectif en histogramme.",
         "es": "Muestra mi distribución frente al objetivo en un gráfico de barras.",
         "it": "Mostra la mia allocazione rispetto all'obiettivo come grafico a barre."},
    "Show me what drove my return as a waterfall chart.":
        {"nl": "Laat zien wat mijn rendement bepaalde als een watervaldiagram.",
         "de": "Zeig mir als Wasserfalldiagramm, was meine Rendite bestimmt hat.",
         "fr": "Montre-moi ce qui a déterminé ma performance en cascade.",
         "es": "Muestra qué impulsó mi rentabilidad en un gráfico de cascada.",
         "it": "Mostra cosa ha determinato il mio rendimento come grafico a cascata."},
    "Show me my largest holdings as a treemap.":
        {"nl": "Laat mijn grootste posities zien als een boomkaart.",
         "de": "Zeig mir meine größten Positionen als Baumkarte.",
         "fr": "Montre-moi mes principales positions en treemap.",
         "es": "Muestra mis mayores posiciones en un treemap.",
         "it": "Mostra le mie posizioni principali come treemap."},
    "Plot my return over time as a line chart.":
        {"nl": "Toon mijn rendement in de tijd als een lijndiagram.",
         "de": "Zeig meine Rendite im Zeitverlauf als Liniendiagramm.",
         "fr": "Trace ma performance dans le temps en courbe.",
         "es": "Traza mi rentabilidad en el tiempo en un gráfico de líneas.",
         "it": "Traccia il mio rendimento nel tempo come grafico a linee."},
    "Chart my return against the benchmark as a bar chart.":
        {"nl": "Toon mijn rendement versus de benchmark als een staafdiagram.",
         "de": "Zeig meine Rendite gegenüber der Benchmark als Balkendiagramm.",
         "fr": "Trace ma performance contre l'indice en histogramme.",
         "es": "Traza mi rentabilidad frente al índice en un gráfico de barras.",
         "it": "Traccia il mio rendimento contro il benchmark come grafico a barre."},
    "Show me what I paid as a donut chart.":
        {"nl": "Laat zien wat ik betaald heb als een donutdiagram.",
         "de": "Zeig mir als Tortendiagramm, was ich gezahlt habe.",
         "fr": "Montre-moi ce que j'ai payé en donut.",
         "es": "Muestra lo que he pagado en un gráfico de donut.",
         "it": "Mostra quanto ho pagato come grafico a donut."},
    "Show me my cash flow in and out as a donut chart.":
        {"nl": "Laat mijn geldstromen in en uit zien als een donutdiagram.",
         "de": "Zeig mir Zu- und Abflüsse als Tortendiagramm.",
         "fr": "Montre-moi mes flux entrants et sortants en donut.",
         "es": "Muestra mis entradas y salidas en un gráfico de donut.",
         "it": "Mostra i miei flussi in entrata e uscita come grafico a donut."},

    # ── chat chart titles ────────────────────────────────────────────────
    "How your portfolio is invested":
                        {"nl": "Hoe uw portefeuille is belegd",
                         "de": "Wie Ihr Portfolio investiert ist",
                         "fr": "Comment votre portefeuille est investi",
                         "es": "Cómo está invertida su cartera",
                         "it": "Come è investito il suo portafoglio"},
    "Where you sit against your target":
                        {"nl": "Uw positie ten opzichte van uw doel",
                         "de": "Ihre Position gegenüber dem Ziel",
                         "fr": "Votre position par rapport à votre objectif",
                         "es": "Su posición frente a su objetivo",
                         "it": "La sua posizione rispetto all'obiettivo"},
    "What drove your return":
                        {"nl": "Wat uw rendement bepaalde",
                         "de": "Was Ihre Rendite bestimmt hat",
                         "fr": "Ce qui a déterminé votre performance",
                         "es": "Qué impulsó su rentabilidad",
                         "it": "Cosa ha determinato il suo rendimento"},
    "Your largest holdings":
                        {"nl": "Uw grootste posities", "de": "Ihre größten Positionen",
                         "fr": "Vos principales positions", "es": "Sus mayores posiciones",
                         "it": "Le sue posizioni principali"},
    "Your return over time":
                        {"nl": "Uw rendement in de tijd",
                         "de": "Ihre Rendite im Zeitverlauf",
                         "fr": "Votre performance dans le temps",
                         "es": "Su rentabilidad en el tiempo",
                         "it": "Il suo rendimento nel tempo"},
    "You against your benchmark":
                        {"nl": "U versus uw benchmark",
                         "de": "Sie gegenüber Ihrer Benchmark",
                         "fr": "Vous par rapport à votre indice",
                         "es": "Usted frente a su índice",
                         "it": "Lei rispetto al suo benchmark"},
    # ── small chrome words the renderer writes inline ────────────────────
    "since":            {"nl": "sinds", "de": "seit", "fr": "depuis",
                         "es": "desde", "it": "da"},
    "vs":               {"nl": "t.o.v.", "de": "ggü.", "fr": "vs",
                         "es": "frente a", "it": "vs"},
    "benchmark":        {"nl": "benchmark", "de": "Benchmark",
                         "fr": "indice de référence", "es": "índice de referencia",
                         "it": "benchmark"},
    "Quarterly Portfolio Review":
                        {"nl": "Kwartaaloverzicht portefeuille",
                         "de": "Quartalsbericht Portfolio",
                         "fr": "Revue trimestrielle du portefeuille",
                         "es": "Revisión trimestral de la cartera",
                         "it": "Revisione trimestrale del portafoglio"},
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


_AS_AT = None


def _translate_composed(text: str, locale: str) -> Optional[str]:
    """Strings the code BUILDS around a value, e.g. "as at 2026-06-30".

    A dictionary cannot hold these because the date differs every quarter,
    so the fixed half is translated and the value is left exactly as it
    was — dates are data, not language.
    """
    global _AS_AT
    if _AS_AT is None:
        import re as _re
        _AS_AT = _re.compile(r"^(Valuations )?as at (.+?)(\. Source:.*)?$")
    m = _AS_AT.match(text)
    if not m:
        return None
    lead = "Valuations " if m.group(1) else ""
    out = (t("Valuations", locale) + " " if lead else "") +           t("as at", locale) + " " + m.group(2)
    if m.group(3):
        out += m.group(3)
    return out


def t(text: Optional[str], locale: Optional[str]) -> Optional[str]:
    """Translate one label. Unknown text and English pass through unchanged.

    Falling through rather than raising or blanking is deliberate: a label
    we forgot to add renders in English, which is visibly imperfect and
    gets reported. A blank renders as a nameless column, which does not.
    """
    if not text or not locale or locale == "en":
        return text
    entry = LABELS.get(text)
    if entry:
        return entry.get(locale, text)
    composed = _translate_composed(text, locale)
    return composed if composed is not None else text


# Display fields only. Everything absent from this list — source_refs,
# block_id, block_type, format, unit, tone — is structural and must survive
# untouched. Adding a key here is a deliberate act, which is the point.
# `text` and `source` are included for the DISCLOSURE and EXPLAINER blocks,
# whose wording is code-written and fixed. Model-written narrative also has
# a `text` field, but it is already in the right language and simply falls
# through the dictionary unchanged — there is no entry for a sentence the
# model composed, so nothing matches and nothing is rewritten.
# The drafted languages are folded in here rather than written above, so the
# reviewed five and the unreviewed fifteen stay separable. setdefault means a
# language promoted into LABELS after review beats its draft automatically.
from .labels_extra import merge_into as _merge_drafts   # noqa: E402
_merge_drafts(LABELS)


# Axis category lists, held as bare strings rather than {"label": ...}.
# These feed the x-axis of the INTERACTIVE chart, which is why an Arabic
# report was rendering its attribution chart labelled "US Equity, Fixed
# Income, Cash" while the static SVG beside it was correct.
_STRING_LIST_FIELDS = ("x_categories", "categories", "labels")

_TEXT_FIELDS = ("title", "label", "name", "asset_class", "term",
                "subtitle", "text", "source")
_LIST_FIELDS = ("segments", "items", "rows", "bars", "points",
                "series", "terms")


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
        for f in ("title", "subtitle"):
            if isinstance(block.get(f), str):
                block[f] = t(block[f], locale)
        data = block.get("content_json") or block.get("data")
        if isinstance(data, dict):
            _localise_data(data, locale)
    return out


def _localise_data(data: Dict[str, Any], locale: str) -> None:
    """Translate display text in a block's data, at any depth.

    RECURSION IS THE POINT. This used to walk one level — the fields on
    `data`, then the fields on each row of a list — and stop. But a line
    chart keeps its x-axis categories at series[].points[].label, two levels
    down, so those labels were never translated. They then became the axis
    labels of the INTERACTIVE chart, and an Arabic report rendered its
    attribution chart reading "US Equity, Fixed Income, Cash".

    It was invisible in review because the STATIC SVG fallback beside it was
    correct: the two are built from different code paths, and only one of
    them was reading translated data.

    Depth is bounded by _LIST_FIELDS — the walk only follows containers we
    named, never arbitrary keys — so this cannot wander into source_refs or
    any other structural field. A label is still not a key.
    """
    for field in _TEXT_FIELDS:
        if isinstance(data.get(field), str):
            data[field] = t(data[field], locale)
    # Lists of BARE STRINGS that are display text.
    #
    # Named one by one, never inferred. source_refs is also a list of bare
    # strings — "attr.US Equity", "alloc.Cash" — and those are KEYS the
    # grounding gate matches on. Translating them would not merely look
    # wrong, it would break the link between a figure and its source. So the
    # rule from the top of this module applies at its sharpest here: a label
    # is not a key, and the only safe way to tell them apart is a whitelist.
    for field in _STRING_LIST_FIELDS:
        vals = data.get(field)
        if isinstance(vals, list) and all(isinstance(v, str) for v in vals):
            data[field] = [t(v, locale) for v in vals]

    for field in _LIST_FIELDS:
        rows = data.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                _localise_data(row, locale)
