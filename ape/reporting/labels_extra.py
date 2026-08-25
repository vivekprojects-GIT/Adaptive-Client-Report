"""Label translations added beyond the original five — DRAFTS, UNREVIEWED.

Kept separate from labels.py on purpose. The five languages there
(nl/de/fr/es/it) and the fifteen here are at different levels of assurance,
and a single merged dictionary would hide that. One import merges these in;
deleting a language is deleting its key.

═══════════════════════════════════════════════════════════════════════════
WHAT "UNREVIEWED" MEANS HERE
═══════════════════════════════════════════════════════════════════════════

No native speaker has read any of this. That is a real limitation and it is
worth being precise about which half it threatens.

It does NOT threaten the FIGURES. Nothing in this file can change a number.
Values are computed once, formatted per locale by locales.format_number,
and validated against the frozen snapshot. A mistranslated label renders the
wrong WORD next to the right VALUE.

It DOES threaten the WORDS, and in this domain some of those words carry
regulatory weight. "Fixed Income" mistranslated as the salary sense of
income is embarrassing; a disclosure sentence that does not say what the
local regulator requires it to say is a compliance problem. The disclosure
(and only the disclosure) should be replaced with wording supplied by
compliance for each jurisdiction rather than translated by anyone — us
included.

Terms carrying the most risk, flagged for the reviewer, are listed in
REVIEW_FIRST below. scripts/review_sheet.py prints them per language.
"""

from __future__ import annotations

from typing import Dict

# language -> {english label: translation}
DRAFTS: Dict[str, Dict[str, str]] = {
    # ── Portuguese ──────────────────────────────────────────────
    "pt": {
        "US Equity":
            "Ações EUA",
        "Intl Equity":
            "Ações internacionais",
        "Fixed Income":
            "Obrigações",
        "Alternatives":
            "Investimentos alternativos",
        "Real Assets":
            "Ativos reais",
        "Cash":
            "Liquidez",
        "Asset allocation":
            "Alocação de ativos",
        "Allocation detail":
            "Detalhe da alocação",
        "Allocation vs strategic target":
            "Alocação face ao objetivo estratégico",
        "Fees and costs":
            "Comissões e custos",
        "What you paid":
            "O que pagou",
        "At a glance":
            "Em resumo",
        "Performance vs benchmark":
            "Desempenho face ao índice de referência",
        "Contribution to return":
            "Contributo para a rendibilidade",
        "Return by period":
            "Rendibilidade por período",
        "Return over time":
            "Rendibilidade ao longo do tempo",
        "Return this period":
            "Rendibilidade do período",
        "Ahead of benchmark":
            "Acima do índice de referência",
        "Risk":
            "Risco",
        "Top contributors to return":
            "Principais contributos para a rendibilidade",
        "Top detractors from return":
            "Principais detratores da rendibilidade",
        "Behind benchmark":
            "Abaixo do índice de referência",
        "Portfolio Growth":
            "Evolução da carteira",
        "Portfolio value and recent performance":
            "Valor da carteira e desempenho recente",
        "Key takeaways":
            "Principais conclusões",
        "What these terms mean":
            "O que significam estes termos",
        "Advisory fee":
            "Comissão de gestão",
        "Fund expenses":
            "Encargos dos fundos",
        "Total":
            "Total",
        "Portfolio value":
            "Valor da carteira",
        "Portfolio return":
            "Rendibilidade da carteira",
        "Portfolio":
            "Carteira",
        "Benchmark":
            "Índice de referência",
        "Return":
            "Rendibilidade",
        "Risk level":
            "Nível de risco",
        "Target":
            "Objetivo",
        "Actual":
            "Efetivo",
        "Contribution":
            "Contributo",
        "Cumulative":
            "Acumulado",
        "Period":
            "Período",
        "Difference":
            "Diferença",
        "Others":
            "Outros",
        "Asset class":
            "Classe de ativos",
        "Weight":
            "Peso",
        "Value":
            "Valor",
        "Fees":
            "Comissões",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Uma combinação de referência usada para avaliar o desempenho. Superá-la significa que a sua carteira teve um desempenho melhor do que o mercado com esse nível de risco.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Quanto cada parte da carteira acrescentou ou retirou à rendibilidade total. Os contributos somam a rendibilidade que efetivamente recebeu.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "A combinação de longo prazo acordada para o seu perfil de risco. As posições afastam-se dela à medida que os mercados evoluem e são reajustadas no rebalanceamento.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Todas as rendibilidades apresentadas são líquidas de comissões, refletindo o que efetivamente ganhou.",
        "Valuations":
            "Avaliações",
        "as at":
            "em",
        "Portfolio vs benchmark":
            "Carteira face ao índice de referência",
        "last column is drift from target":
            "a última coluna indica o desvio face ao objetivo",
        "Strategic target":
            "Objetivo estratégico",
        "Net of fees":
            "Líquido de comissões",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "O desempenho passado não é indicativo de resultados futuros. Os valores são líquidos de comissões salvo indicação em contrário.",
        "Give me a quick summary of this report.":
            "Dê-me um resumo rápido deste relatório.",
        "Explain the fees I paid this period.":
            "Explique as comissões que paguei neste período.",
        "How did I do against the benchmark?":
            "Como me saí face ao índice de referência?",
        "Allocation donut":
            "Gráfico circular da alocação",
        "Actual vs target":
            "Efetivo face ao objetivo",
        "Return drivers":
            "Fatores da rendibilidade",
        "Holdings treemap":
            "Mapa de posições",
        "You vs benchmark":
            "A sua carteira face ao índice",
        "Fee breakdown":
            "Detalhe das comissões",
        "Money in and out":
            "Entradas e saídas",
        "Show me my asset allocation as a donut chart.":
            "Mostre-me a minha alocação de ativos num gráfico circular.",
        "Show me my allocation against target as a bar chart.":
            "Mostre-me a minha alocação face ao objetivo num gráfico de barras.",
        "Show me what drove my return as a waterfall chart.":
            "Mostre-me o que impulsionou a minha rendibilidade num gráfico de cascata.",
        "Show me my largest holdings as a treemap.":
            "Mostre-me as minhas maiores posições num mapa de árvore.",
        "Plot my return over time as a line chart.":
            "Represente a minha rendibilidade ao longo do tempo num gráfico de linhas.",
        "Chart my return against the benchmark as a bar chart.":
            "Represente a minha rendibilidade face ao índice num gráfico de barras.",
        "Show me what I paid as a donut chart.":
            "Mostre-me o que paguei num gráfico circular.",
        "Show me my cash flow in and out as a donut chart.":
            "Mostre-me as minhas entradas e saídas num gráfico circular.",
        "How your portfolio is invested":
            "Como está investida a sua carteira",
        "Where you sit against your target":
            "A sua posição face ao objetivo",
        "What drove your return":
            "O que impulsionou a sua rendibilidade",
        "Your largest holdings":
            "As suas maiores posições",
        "Your return over time":
            "A sua rendibilidade ao longo do tempo",
        "You against your benchmark":
            "A sua carteira face ao índice de referência",
        "since":
            "desde",
        "vs":
            "face a",
        "benchmark":
            "índice de referência",
        "Quarterly Portfolio Review":
            "Relatório trimestral da carteira",
        "Conservative":
            "Conservador",
        "Moderate":
            "Moderado",
        "Growth":
            "Crescimento",
        "Aggressive":
            "Agressivo",
    },

    # ── Swedish ─────────────────────────────────────────────────
    "sv": {
        "US Equity":
            "Amerikanska aktier",
        "Intl Equity":
            "Internationella aktier",
        "Fixed Income":
            "Räntebärande placeringar",
        "Alternatives":
            "Alternativa investeringar",
        "Real Assets":
            "Reala tillgångar",
        "Cash":
            "Likvida medel",
        "Asset allocation":
            "Tillgångsfördelning",
        "Allocation detail":
            "Fördelning i detalj",
        "Allocation vs strategic target":
            "Fördelning mot strategiskt mål",
        "Fees and costs":
            "Avgifter och kostnader",
        "What you paid":
            "Vad du betalade",
        "At a glance":
            "I korthet",
        "Performance vs benchmark":
            "Avkastning mot jämförelseindex",
        "Contribution to return":
            "Bidrag till avkastning",
        "Return by period":
            "Avkastning per period",
        "Return over time":
            "Avkastning över tid",
        "Return this period":
            "Avkastning denna period",
        "Ahead of benchmark":
            "Före jämförelseindex",
        "Risk":
            "Risk",
        "Top contributors to return":
            "Största bidrag till avkastningen",
        "Top detractors from return":
            "Största avdrag från avkastningen",
        "Behind benchmark":
            "Efter jämförelseindex",
        "Portfolio Growth":
            "Portföljutveckling",
        "Portfolio value and recent performance":
            "Portföljvärde och senaste utveckling",
        "Key takeaways":
            "Viktigaste slutsatser",
        "What these terms mean":
            "Vad dessa begrepp betyder",
        "Advisory fee":
            "Rådgivningsavgift",
        "Fund expenses":
            "Fondkostnader",
        "Total":
            "Totalt",
        "Portfolio value":
            "Portföljvärde",
        "Portfolio return":
            "Portföljavkastning",
        "Portfolio":
            "Portfölj",
        "Benchmark":
            "Jämförelseindex",
        "Return":
            "Avkastning",
        "Risk level":
            "Risknivå",
        "Target":
            "Mål",
        "Actual":
            "Faktisk",
        "Contribution":
            "Bidrag",
        "Cumulative":
            "Ackumulerat",
        "Period":
            "Period",
        "Difference":
            "Skillnad",
        "Others":
            "Övrigt",
        "Asset class":
            "Tillgångsslag",
        "Weight":
            "Vikt",
        "Value":
            "Värde",
        "Fees":
            "Avgifter",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "En referensmix som används för att bedöma avkastningen. Att slå den innebär att din portfölj gick bättre än marknaden vid den risknivån.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Hur mycket varje del av portföljen bidrog med till, eller drog ifrån, den totala avkastningen. Bidragen summerar till den avkastning du faktiskt fick.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Den långsiktiga fördelning som avtalats för din riskprofil. Innehaven glider ifrån den när marknaderna rör sig och återställs vid ombalansering.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "All avkastning som visas är efter avdrag för avgifter och speglar därmed vad du faktiskt tjänade.",
        "Valuations":
            "Värderingar",
        "as at":
            "per",
        "Portfolio vs benchmark":
            "Portfölj mot jämförelseindex",
        "last column is drift from target":
            "sista kolumnen visar avvikelsen från målet",
        "Strategic target":
            "Strategiskt mål",
        "Net of fees":
            "Efter avgifter",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Historisk avkastning är ingen garanti för framtida resultat. Siffrorna är efter avgifter om inget annat anges.",
        "Give me a quick summary of this report.":
            "Ge mig en kort sammanfattning av den här rapporten.",
        "Explain the fees I paid this period.":
            "Förklara avgifterna jag betalade den här perioden.",
        "How did I do against the benchmark?":
            "Hur gick det för mig mot jämförelseindex?",
        "Allocation donut":
            "Fördelningsdiagram",
        "Actual vs target":
            "Faktisk mot mål",
        "Return drivers":
            "Avkastningsdrivare",
        "Holdings treemap":
            "Innehavskarta",
        "You vs benchmark":
            "Du mot jämförelseindex",
        "Fee breakdown":
            "Avgiftsfördelning",
        "Money in and out":
            "In- och utflöden",
        "Show me my asset allocation as a donut chart.":
            "Visa min tillgångsfördelning som ett cirkeldiagram.",
        "Show me my allocation against target as a bar chart.":
            "Visa min fördelning mot målet som ett stapeldiagram.",
        "Show me what drove my return as a waterfall chart.":
            "Visa vad som drev min avkastning som ett vattenfallsdiagram.",
        "Show me my largest holdings as a treemap.":
            "Visa mina största innehav som en trädkarta.",
        "Plot my return over time as a line chart.":
            "Rita min avkastning över tid som ett linjediagram.",
        "Chart my return against the benchmark as a bar chart.":
            "Rita min avkastning mot jämförelseindex som ett stapeldiagram.",
        "Show me what I paid as a donut chart.":
            "Visa vad jag betalade som ett cirkeldiagram.",
        "Show me my cash flow in and out as a donut chart.":
            "Visa mina in- och utflöden som ett cirkeldiagram.",
        "How your portfolio is invested":
            "Så är din portfölj placerad",
        "Where you sit against your target":
            "Var du ligger mot ditt mål",
        "What drove your return":
            "Vad som drev din avkastning",
        "Your largest holdings":
            "Dina största innehav",
        "Your return over time":
            "Din avkastning över tid",
        "You against your benchmark":
            "Du mot ditt jämförelseindex",
        "since":
            "sedan",
        "vs":
            "mot",
        "benchmark":
            "jämförelseindex",
        "Quarterly Portfolio Review":
            "Kvartalsrapport för portföljen",
        "Conservative":
            "Försiktig",
        "Moderate":
            "Balanserad",
        "Growth":
            "Tillväxt",
        "Aggressive":
            "Offensiv",
    },

    # ── Danish ──────────────────────────────────────────────────
    "da": {
        "US Equity":
            "Amerikanske aktier",
        "Intl Equity":
            "Internationale aktier",
        "Fixed Income":
            "Obligationer",
        "Alternatives":
            "Alternative investeringer",
        "Real Assets":
            "Realaktiver",
        "Cash":
            "Kontanter",
        "Asset allocation":
            "Aktivfordeling",
        "Allocation detail":
            "Fordeling i detaljer",
        "Allocation vs strategic target":
            "Fordeling mod strategisk mål",
        "Fees and costs":
            "Gebyrer og omkostninger",
        "What you paid":
            "Hvad du betalte",
        "At a glance":
            "Kort fortalt",
        "Performance vs benchmark":
            "Afkast mod benchmark",
        "Contribution to return":
            "Bidrag til afkast",
        "Return by period":
            "Afkast pr. periode",
        "Return over time":
            "Afkast over tid",
        "Return this period":
            "Afkast denne periode",
        "Ahead of benchmark":
            "Foran benchmark",
        "Risk":
            "Risiko",
        "Top contributors to return":
            "Største bidrag til afkastet",
        "Top detractors from return":
            "Største træk i afkastet",
        "Behind benchmark":
            "Bagud for benchmark",
        "Portfolio Growth":
            "Porteføljeudvikling",
        "Portfolio value and recent performance":
            "Porteføljeværdi og seneste udvikling",
        "Key takeaways":
            "Vigtigste pointer",
        "What these terms mean":
            "Hvad disse begreber betyder",
        "Advisory fee":
            "Rådgivningshonorar",
        "Fund expenses":
            "Fondsomkostninger",
        "Total":
            "I alt",
        "Portfolio value":
            "Porteføljeværdi",
        "Portfolio return":
            "Porteføljeafkast",
        "Portfolio":
            "Portefølje",
        "Benchmark":
            "Benchmark",
        "Return":
            "Afkast",
        "Risk level":
            "Risikoniveau",
        "Target":
            "Mål",
        "Actual":
            "Faktisk",
        "Contribution":
            "Bidrag",
        "Cumulative":
            "Akkumuleret",
        "Period":
            "Periode",
        "Difference":
            "Forskel",
        "Others":
            "Øvrige",
        "Asset class":
            "Aktivklasse",
        "Weight":
            "Vægt",
        "Value":
            "Værdi",
        "Fees":
            "Gebyrer",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "En referencesammensætning, der bruges til at vurdere afkastet. At slå den betyder, at din portefølje klarede sig bedre end markedet på det risikoniveau.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Hvor meget hver del af porteføljen lagde til eller trak fra det samlede afkast. Bidragene summerer til det afkast, du faktisk fik.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Den langsigtede sammensætning, der er aftalt for din risikoprofil. Beholdningerne driver væk fra den, når markederne bevæger sig, og bringes tilbage ved rebalancering.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Alle viste afkast er efter fradrag af gebyrer og afspejler derfor, hvad du faktisk tjente.",
        "Valuations":
            "Værdiansættelser",
        "as at":
            "pr.",
        "Portfolio vs benchmark":
            "Portefølje mod benchmark",
        "last column is drift from target":
            "sidste kolonne viser afvigelsen fra målet",
        "Strategic target":
            "Strategisk mål",
        "Net of fees":
            "Efter gebyrer",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Historiske afkast er ikke en pålidelig indikator for fremtidige resultater. Tallene er efter gebyrer, medmindre andet er angivet.",
        "Give me a quick summary of this report.":
            "Giv mig et hurtigt resumé af denne rapport.",
        "Explain the fees I paid this period.":
            "Forklar de gebyrer, jeg betalte i denne periode.",
        "How did I do against the benchmark?":
            "Hvordan klarede jeg mig mod benchmark?",
        "Allocation donut":
            "Fordelingsdiagram",
        "Actual vs target":
            "Faktisk mod mål",
        "Return drivers":
            "Afkastdrivere",
        "Holdings treemap":
            "Beholdningskort",
        "You vs benchmark":
            "Dig mod benchmark",
        "Fee breakdown":
            "Gebyrfordeling",
        "Money in and out":
            "Ind- og udbetalinger",
        "Show me my asset allocation as a donut chart.":
            "Vis min aktivfordeling som et cirkeldiagram.",
        "Show me my allocation against target as a bar chart.":
            "Vis min fordeling mod målet som et søjlediagram.",
        "Show me what drove my return as a waterfall chart.":
            "Vis hvad der drev mit afkast som et vandfaldsdiagram.",
        "Show me my largest holdings as a treemap.":
            "Vis mine største beholdninger som et træstrukturkort.",
        "Plot my return over time as a line chart.":
            "Tegn mit afkast over tid som et kurvediagram.",
        "Chart my return against the benchmark as a bar chart.":
            "Tegn mit afkast mod benchmark som et søjlediagram.",
        "Show me what I paid as a donut chart.":
            "Vis hvad jeg betalte som et cirkeldiagram.",
        "Show me my cash flow in and out as a donut chart.":
            "Vis mine ind- og udbetalinger som et cirkeldiagram.",
        "How your portfolio is invested":
            "Sådan er din portefølje investeret",
        "Where you sit against your target":
            "Hvor du ligger i forhold til dit mål",
        "What drove your return":
            "Hvad der drev dit afkast",
        "Your largest holdings":
            "Dine største beholdninger",
        "Your return over time":
            "Dit afkast over tid",
        "You against your benchmark":
            "Dig mod dit benchmark",
        "since":
            "siden",
        "vs":
            "mod",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Kvartalsrapport for porteføljen",
        "Conservative":
            "Konservativ",
        "Moderate":
            "Moderat",
        "Growth":
            "Vækst",
        "Aggressive":
            "Offensiv",
    },

    # ── Norwegian (Bokmal) ──────────────────────────────────────
    "nb": {
        "US Equity":
            "Amerikanske aksjer",
        "Intl Equity":
            "Internasjonale aksjer",
        "Fixed Income":
            "Renteplasseringer",
        "Alternatives":
            "Alternative investeringer",
        "Real Assets":
            "Realaktiva",
        "Cash":
            "Kontanter",
        "Asset allocation":
            "Aktivafordeling",
        "Allocation detail":
            "Fordeling i detalj",
        "Allocation vs strategic target":
            "Fordeling mot strategisk mål",
        "Fees and costs":
            "Gebyrer og kostnader",
        "What you paid":
            "Hva du betalte",
        "At a glance":
            "Kort oppsummert",
        "Performance vs benchmark":
            "Avkastning mot referanseindeks",
        "Contribution to return":
            "Bidrag til avkastning",
        "Return by period":
            "Avkastning per periode",
        "Return over time":
            "Avkastning over tid",
        "Return this period":
            "Avkastning denne perioden",
        "Ahead of benchmark":
            "Foran referanseindeksen",
        "Risk":
            "Risiko",
        "Top contributors to return":
            "Største bidrag til avkastningen",
        "Top detractors from return":
            "Største fradrag i avkastningen",
        "Behind benchmark":
            "Bak referanseindeksen",
        "Portfolio Growth":
            "Porteføljeutvikling",
        "Portfolio value and recent performance":
            "Porteføljeverdi og siste utvikling",
        "Key takeaways":
            "Viktigste punkter",
        "What these terms mean":
            "Hva disse begrepene betyr",
        "Advisory fee":
            "Rådgivningshonorar",
        "Fund expenses":
            "Fondskostnader",
        "Total":
            "Totalt",
        "Portfolio value":
            "Porteføljeverdi",
        "Portfolio return":
            "Porteføljeavkastning",
        "Portfolio":
            "Portefølje",
        "Benchmark":
            "Referanseindeks",
        "Return":
            "Avkastning",
        "Risk level":
            "Risikonivå",
        "Target":
            "Mål",
        "Actual":
            "Faktisk",
        "Contribution":
            "Bidrag",
        "Cumulative":
            "Akkumulert",
        "Period":
            "Periode",
        "Difference":
            "Differanse",
        "Others":
            "Øvrige",
        "Asset class":
            "Aktivaklasse",
        "Weight":
            "Vekt",
        "Value":
            "Verdi",
        "Fees":
            "Gebyrer",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "En referansesammensetning som brukes til å vurdere avkastningen. Å slå den betyr at porteføljen din gjorde det bedre enn markedet på det risikonivået.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Hvor mye hver del av porteføljen la til eller trakk fra den samlede avkastningen. Bidragene summerer seg til avkastningen du faktisk fikk.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Den langsiktige sammensetningen som er avtalt for risikoprofilen din. Beholdningene driver bort fra den når markedene beveger seg, og hentes tilbake ved rebalansering.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "All avkastning som vises er etter fradrag for gebyrer, og gjenspeiler dermed hva du faktisk tjente.",
        "Valuations":
            "Verdivurderinger",
        "as at":
            "per",
        "Portfolio vs benchmark":
            "Portefølje mot referanseindeks",
        "last column is drift from target":
            "siste kolonne viser avviket fra målet",
        "Strategic target":
            "Strategisk mål",
        "Net of fees":
            "Etter gebyrer",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Historisk avkastning er ingen garanti for fremtidig avkastning. Tallene er etter gebyrer med mindre annet er oppgitt.",
        "Give me a quick summary of this report.":
            "Gi meg et kort sammendrag av denne rapporten.",
        "Explain the fees I paid this period.":
            "Forklar gebyrene jeg betalte denne perioden.",
        "How did I do against the benchmark?":
            "Hvordan gjorde jeg det mot referanseindeksen?",
        "Allocation donut":
            "Fordelingsdiagram",
        "Actual vs target":
            "Faktisk mot mål",
        "Return drivers":
            "Avkastningsdrivere",
        "Holdings treemap":
            "Beholdningskart",
        "You vs benchmark":
            "Du mot referanseindeksen",
        "Fee breakdown":
            "Gebyrfordeling",
        "Money in and out":
            "Inn- og utbetalinger",
        "Show me my asset allocation as a donut chart.":
            "Vis aktivafordelingen min som et sektordiagram.",
        "Show me my allocation against target as a bar chart.":
            "Vis fordelingen min mot målet som et stolpediagram.",
        "Show me what drove my return as a waterfall chart.":
            "Vis hva som drev avkastningen min som et fossefallsdiagram.",
        "Show me my largest holdings as a treemap.":
            "Vis de største beholdningene mine som et trekart.",
        "Plot my return over time as a line chart.":
            "Tegn avkastningen min over tid som et linjediagram.",
        "Chart my return against the benchmark as a bar chart.":
            "Tegn avkastningen min mot referanseindeksen som et stolpediagram.",
        "Show me what I paid as a donut chart.":
            "Vis hva jeg betalte som et sektordiagram.",
        "Show me my cash flow in and out as a donut chart.":
            "Vis inn- og utbetalingene mine som et sektordiagram.",
        "How your portfolio is invested":
            "Slik er porteføljen din investert",
        "Where you sit against your target":
            "Hvor du ligger mot målet ditt",
        "What drove your return":
            "Hva som drev avkastningen din",
        "Your largest holdings":
            "Dine største beholdninger",
        "Your return over time":
            "Avkastningen din over tid",
        "You against your benchmark":
            "Du mot referanseindeksen din",
        "since":
            "siden",
        "vs":
            "mot",
        "benchmark":
            "referanseindeks",
        "Quarterly Portfolio Review":
            "Kvartalsrapport for porteføljen",
        "Conservative":
            "Konservativ",
        "Moderate":
            "Moderat",
        "Growth":
            "Vekst",
        "Aggressive":
            "Offensiv",
    },

    # ── Finnish ─────────────────────────────────────────────────
    "fi": {
        "US Equity":
            "Yhdysvaltain osakkeet",
        "Intl Equity":
            "Kansainväliset osakkeet",
        "Fixed Income":
            "Korkosijoitukset",
        "Alternatives":
            "Vaihtoehtoiset sijoitukset",
        "Real Assets":
            "Reaaliomaisuus",
        "Cash":
            "Käteisvarat",
        "Asset allocation":
            "Varojen allokaatio",
        "Allocation detail":
            "Allokaation erittely",
        "Allocation vs strategic target":
            "Allokaatio suhteessa strategiseen tavoitteeseen",
        "Fees and costs":
            "Palkkiot ja kulut",
        "What you paid":
            "Mitä maksoit",
        "At a glance":
            "Yhteenveto",
        "Performance vs benchmark":
            "Tuotto suhteessa vertailuindeksiin",
        "Contribution to return":
            "Vaikutus tuottoon",
        "Return by period":
            "Tuotto jaksoittain",
        "Return over time":
            "Tuotto ajan myötä",
        "Return this period":
            "Tämän jakson tuotto",
        "Ahead of benchmark":
            "Vertailuindeksiä edellä",
        "Risk":
            "Riski",
        "Top contributors to return":
            "Suurimmat tuoton kasvattajat",
        "Top detractors from return":
            "Suurimmat tuoton heikentäjät",
        "Behind benchmark":
            "Vertailuindeksiä jäljessä",
        "Portfolio Growth":
            "Salkun kehitys",
        "Portfolio value and recent performance":
            "Salkun arvo ja viimeaikainen kehitys",
        "Key takeaways":
            "Keskeiset havainnot",
        "What these terms mean":
            "Mitä nämä termit tarkoittavat",
        "Advisory fee":
            "Neuvontapalkkio",
        "Fund expenses":
            "Rahastokulut",
        "Total":
            "Yhteensä",
        "Portfolio value":
            "Salkun arvo",
        "Portfolio return":
            "Salkun tuotto",
        "Portfolio":
            "Salkku",
        "Benchmark":
            "Vertailuindeksi",
        "Return":
            "Tuotto",
        "Risk level":
            "Riskitaso",
        "Target":
            "Tavoite",
        "Actual":
            "Toteutunut",
        "Contribution":
            "Vaikutus",
        "Cumulative":
            "Kumulatiivinen",
        "Period":
            "Jakso",
        "Difference":
            "Erotus",
        "Others":
            "Muut",
        "Asset class":
            "Omaisuusluokka",
        "Weight":
            "Paino",
        "Value":
            "Arvo",
        "Fees":
            "Palkkiot",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Vertailukohtana käytettävä sijoitusjakauma, jonka avulla tuottoa arvioidaan. Sen voittaminen tarkoittaa, että salkkusi tuotti paremmin kuin markkina samalla riskitasolla.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kuinka paljon kukin salkun osa lisäsi kokonaistuottoa tai vähensi sitä. Vaikutukset summautuvat siihen tuottoon, jonka todella sait.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Riskiprofiilillesi sovittu pitkän aikavälin jakauma. Sijoitukset ajautuvat siitä markkinoiden liikkuessa ja palautetaan tasapainotuksen yhteydessä.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Kaikki esitetyt tuotot ovat palkkioiden vähentämisen jälkeen, joten ne kuvaavat todellista ansiotasi.",
        "Valuations":
            "Arvostukset",
        "as at":
            "päivänä",
        "Portfolio vs benchmark":
            "Salkku vs. vertailuindeksi",
        "last column is drift from target":
            "viimeinen sarake näyttää poikkeaman tavoitteesta",
        "Strategic target":
            "Strateginen tavoite",
        "Net of fees":
            "Palkkioiden jälkeen",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Historiallinen tuotto ei ole tae tulevasta kehityksestä. Luvut ovat palkkioiden jälkeen, ellei toisin mainita.",
        "Give me a quick summary of this report.":
            "Anna minulle lyhyt yhteenveto tästä raportista.",
        "Explain the fees I paid this period.":
            "Selitä tällä jaksolla maksamani palkkiot.",
        "How did I do against the benchmark?":
            "Miten pärjäsin vertailuindeksiin nähden?",
        "Allocation donut":
            "Allokaatiokaavio",
        "Actual vs target":
            "Toteutunut vs. tavoite",
        "Return drivers":
            "Tuoton ajurit",
        "Holdings treemap":
            "Sijoitusten puukartta",
        "You vs benchmark":
            "Sinä vs. vertailuindeksi",
        "Fee breakdown":
            "Palkkioiden erittely",
        "Money in and out":
            "Rahavirrat sisään ja ulos",
        "Show me my asset allocation as a donut chart.":
            "Näytä varojen allokaationi rengaskaaviona.",
        "Show me my allocation against target as a bar chart.":
            "Näytä allokaationi suhteessa tavoitteeseen pylväskaaviona.",
        "Show me what drove my return as a waterfall chart.":
            "Näytä tuottoni ajurit vesiputouskaaviona.",
        "Show me my largest holdings as a treemap.":
            "Näytä suurimmat sijoitukseni puukarttana.",
        "Plot my return over time as a line chart.":
            "Piirrä tuottoni ajan myötä viivakaaviona.",
        "Chart my return against the benchmark as a bar chart.":
            "Piirrä tuottoni vertailuindeksiin nähden pylväskaaviona.",
        "Show me what I paid as a donut chart.":
            "Näytä maksamani palkkiot rengaskaaviona.",
        "Show me my cash flow in and out as a donut chart.":
            "Näytä rahavirtani sisään ja ulos rengaskaaviona.",
        "How your portfolio is invested":
            "Näin salkkusi on sijoitettu",
        "Where you sit against your target":
            "Missä olet suhteessa tavoitteeseesi",
        "What drove your return":
            "Mikä ohjasi tuottoasi",
        "Your largest holdings":
            "Suurimmat sijoituksesi",
        "Your return over time":
            "Tuottosi ajan myötä",
        "You against your benchmark":
            "Sinä vertailuindeksiäsi vastaan",
        "since":
            "alkaen",
        "vs":
            "vs.",
        "benchmark":
            "vertailuindeksi",
        "Quarterly Portfolio Review":
            "Salkun neljännesvuosikatsaus",
        "Conservative":
            "Varovainen",
        "Moderate":
            "Maltillinen",
        "Growth":
            "Kasvu",
        "Aggressive":
            "Tuottohakuinen",
    },

    # ── Polish ──────────────────────────────────────────────────
    "pl": {
        "US Equity":
            "Akcje amerykańskie",
        "Intl Equity":
            "Akcje międzynarodowe",
        "Fixed Income":
            "Instrumenty dłużne",
        "Alternatives":
            "Inwestycje alternatywne",
        "Real Assets":
            "Aktywa realne",
        "Cash":
            "Środki pieniężne",
        "Asset allocation":
            "Alokacja aktywów",
        "Allocation detail":
            "Szczegóły alokacji",
        "Allocation vs strategic target":
            "Alokacja wobec celu strategicznego",
        "Fees and costs":
            "Opłaty i koszty",
        "What you paid":
            "Ile zapłaciłeś",
        "At a glance":
            "W skrócie",
        "Performance vs benchmark":
            "Wyniki wobec benchmarku",
        "Contribution to return":
            "Wkład w stopę zwrotu",
        "Return by period":
            "Stopa zwrotu w okresach",
        "Return over time":
            "Stopa zwrotu w czasie",
        "Return this period":
            "Stopa zwrotu w tym okresie",
        "Ahead of benchmark":
            "Powyżej benchmarku",
        "Risk":
            "Ryzyko",
        "Top contributors to return":
            "Największy wkład w stopę zwrotu",
        "Top detractors from return":
            "Największe obciążenia stopy zwrotu",
        "Behind benchmark":
            "Poniżej benchmarku",
        "Portfolio Growth":
            "Rozwój portfela",
        "Portfolio value and recent performance":
            "Wartość portfela i ostatnie wyniki",
        "Key takeaways":
            "Najważniejsze wnioski",
        "What these terms mean":
            "Co oznaczają te pojęcia",
        "Advisory fee":
            "Opłata za doradztwo",
        "Fund expenses":
            "Koszty funduszy",
        "Total":
            "Razem",
        "Portfolio value":
            "Wartość portfela",
        "Portfolio return":
            "Stopa zwrotu portfela",
        "Portfolio":
            "Portfel",
        "Benchmark":
            "Benchmark",
        "Return":
            "Stopa zwrotu",
        "Risk level":
            "Poziom ryzyka",
        "Target":
            "Cel",
        "Actual":
            "Rzeczywiste",
        "Contribution":
            "Wkład",
        "Cumulative":
            "Skumulowana",
        "Period":
            "Okres",
        "Difference":
            "Różnica",
        "Others":
            "Pozostałe",
        "Asset class":
            "Klasa aktywów",
        "Weight":
            "Waga",
        "Value":
            "Wartość",
        "Fees":
            "Opłaty",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referencyjny skład portfela służący do oceny wyników. Pobicie go oznacza, że Twój portfel wypadł lepiej niż rynek przy tym poziomie ryzyka.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Ile każda część portfela dodała do całkowitej stopy zwrotu lub od niej odjęła. Wkłady sumują się do stopy zwrotu, którą faktycznie uzyskałeś.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Długoterminowy skład uzgodniony dla Twojego profilu ryzyka. Pozycje oddalają się od niego wraz z ruchami rynku i są przywracane przy rebalansowaniu.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Wszystkie prezentowane stopy zwrotu są po odliczeniu opłat, więc odzwierciedlają to, co faktycznie zarobiłeś.",
        "Valuations":
            "Wyceny",
        "as at":
            "na dzień",
        "Portfolio vs benchmark":
            "Portfel wobec benchmarku",
        "last column is drift from target":
            "ostatnia kolumna pokazuje odchylenie od celu",
        "Strategic target":
            "Cel strategiczny",
        "Net of fees":
            "Po opłatach",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Wyniki historyczne nie stanowią gwarancji przyszłych rezultatów. Dane są po opłatach, o ile nie wskazano inaczej.",
        "Give me a quick summary of this report.":
            "Podaj mi krótkie podsumowanie tego raportu.",
        "Explain the fees I paid this period.":
            "Wyjaśnij opłaty, które zapłaciłem w tym okresie.",
        "How did I do against the benchmark?":
            "Jak wypadłem na tle benchmarku?",
        "Allocation donut":
            "Wykres kołowy alokacji",
        "Actual vs target":
            "Rzeczywiste wobec celu",
        "Return drivers":
            "Czynniki stopy zwrotu",
        "Holdings treemap":
            "Mapa drzewa pozycji",
        "You vs benchmark":
            "Ty wobec benchmarku",
        "Fee breakdown":
            "Struktura opłat",
        "Money in and out":
            "Wpłaty i wypłaty",
        "Show me my asset allocation as a donut chart.":
            "Pokaż moją alokację aktywów jako wykres pierścieniowy.",
        "Show me my allocation against target as a bar chart.":
            "Pokaż moją alokację wobec celu jako wykres słupkowy.",
        "Show me what drove my return as a waterfall chart.":
            "Pokaż, co napędzało moją stopę zwrotu, jako wykres kaskadowy.",
        "Show me my largest holdings as a treemap.":
            "Pokaż moje największe pozycje jako mapę drzewa.",
        "Plot my return over time as a line chart.":
            "Przedstaw moją stopę zwrotu w czasie jako wykres liniowy.",
        "Chart my return against the benchmark as a bar chart.":
            "Przedstaw moją stopę zwrotu wobec benchmarku jako wykres słupkowy.",
        "Show me what I paid as a donut chart.":
            "Pokaż, ile zapłaciłem, jako wykres pierścieniowy.",
        "Show me my cash flow in and out as a donut chart.":
            "Pokaż moje wpłaty i wypłaty jako wykres pierścieniowy.",
        "How your portfolio is invested":
            "Jak zainwestowany jest Twój portfel",
        "Where you sit against your target":
            "Gdzie jesteś wobec swojego celu",
        "What drove your return":
            "Co napędzało Twoją stopę zwrotu",
        "Your largest holdings":
            "Twoje największe pozycje",
        "Your return over time":
            "Twoja stopa zwrotu w czasie",
        "You against your benchmark":
            "Ty wobec swojego benchmarku",
        "since":
            "od",
        "vs":
            "wobec",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Kwartalny przegląd portfela",
        "Conservative":
            "Konserwatywny",
        "Moderate":
            "Umiarkowany",
        "Growth":
            "Wzrostowy",
        "Aggressive":
            "Agresywny",
    },

    # ── Czech ───────────────────────────────────────────────────
    "cs": {
        "US Equity":
            "Americké akcie",
        "Intl Equity":
            "Mezinárodní akcie",
        "Fixed Income":
            "Dluhopisy",
        "Alternatives":
            "Alternativní investice",
        "Real Assets":
            "Reálná aktiva",
        "Cash":
            "Hotovost",
        "Asset allocation":
            "Alokace aktiv",
        "Allocation detail":
            "Detail alokace",
        "Allocation vs strategic target":
            "Alokace vůči strategickému cíli",
        "Fees and costs":
            "Poplatky a náklady",
        "What you paid":
            "Co jste zaplatili",
        "At a glance":
            "Ve zkratce",
        "Performance vs benchmark":
            "Výkonnost vůči benchmarku",
        "Contribution to return":
            "Příspěvek k výnosu",
        "Return by period":
            "Výnos podle období",
        "Return over time":
            "Výnos v čase",
        "Return this period":
            "Výnos za toto období",
        "Ahead of benchmark":
            "Nad benchmarkem",
        "Risk":
            "Riziko",
        "Top contributors to return":
            "Největší přispěvatelé k výnosu",
        "Top detractors from return":
            "Největší brzdy výnosu",
        "Behind benchmark":
            "Pod benchmarkem",
        "Portfolio Growth":
            "Vývoj portfolia",
        "Portfolio value and recent performance":
            "Hodnota portfolia a nedávná výkonnost",
        "Key takeaways":
            "Klíčové poznatky",
        "What these terms mean":
            "Co tyto pojmy znamenají",
        "Advisory fee":
            "Poplatek za poradenství",
        "Fund expenses":
            "Náklady fondů",
        "Total":
            "Celkem",
        "Portfolio value":
            "Hodnota portfolia",
        "Portfolio return":
            "Výnos portfolia",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Benchmark",
        "Return":
            "Výnos",
        "Risk level":
            "Úroveň rizika",
        "Target":
            "Cíl",
        "Actual":
            "Skutečnost",
        "Contribution":
            "Příspěvek",
        "Cumulative":
            "Kumulativní",
        "Period":
            "Období",
        "Difference":
            "Rozdíl",
        "Others":
            "Ostatní",
        "Asset class":
            "Třída aktiv",
        "Weight":
            "Váha",
        "Value":
            "Hodnota",
        "Fees":
            "Poplatky",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referenční složení používané k hodnocení výkonnosti. Překonat je znamená, že vaše portfolio dosáhlo lepšího výsledku než trh při dané úrovni rizika.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kolik každá část portfolia přidala k celkovému výnosu nebo z něj ubrala. Příspěvky se sčítají do výnosu, který jste skutečně obdrželi.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dlouhodobé složení dohodnuté pro váš rizikový profil. Pozice se od něj s pohybem trhů odchylují a při rebalancování se vracejí zpět.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Všechny uvedené výnosy jsou po odečtení poplatků, a odrážejí tedy to, co jste skutečně vydělali.",
        "Valuations":
            "Ocenění",
        "as at":
            "k",
        "Portfolio vs benchmark":
            "Portfolio vůči benchmarku",
        "last column is drift from target":
            "poslední sloupec ukazuje odchylku od cíle",
        "Strategic target":
            "Strategický cíl",
        "Net of fees":
            "Po poplatcích",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Minulá výkonnost není zárukou budoucích výsledků. Údaje jsou po poplatcích, pokud není uvedeno jinak.",
        "Give me a quick summary of this report.":
            "Dej mi stručné shrnutí této zprávy.",
        "Explain the fees I paid this period.":
            "Vysvětli poplatky, které jsem v tomto období zaplatil.",
        "How did I do against the benchmark?":
            "Jak jsem si vedl vůči benchmarku?",
        "Allocation donut":
            "Koláčový graf alokace",
        "Actual vs target":
            "Skutečnost vůči cíli",
        "Return drivers":
            "Faktory výnosu",
        "Holdings treemap":
            "Stromová mapa pozic",
        "You vs benchmark":
            "Vy vůči benchmarku",
        "Fee breakdown":
            "Struktura poplatků",
        "Money in and out":
            "Vklady a výběry",
        "Show me my asset allocation as a donut chart.":
            "Ukaž mi mou alokaci aktiv jako prstencový graf.",
        "Show me my allocation against target as a bar chart.":
            "Ukaž mi mou alokaci vůči cíli jako sloupcový graf.",
        "Show me what drove my return as a waterfall chart.":
            "Ukaž mi, co pohánělo můj výnos, jako vodopádový graf.",
        "Show me my largest holdings as a treemap.":
            "Ukaž mi mé největší pozice jako stromovou mapu.",
        "Plot my return over time as a line chart.":
            "Vykresli můj výnos v čase jako spojnicový graf.",
        "Chart my return against the benchmark as a bar chart.":
            "Vykresli můj výnos vůči benchmarku jako sloupcový graf.",
        "Show me what I paid as a donut chart.":
            "Ukaž mi, co jsem zaplatil, jako prstencový graf.",
        "Show me my cash flow in and out as a donut chart.":
            "Ukaž mi mé vklady a výběry jako prstencový graf.",
        "How your portfolio is invested":
            "Jak je vaše portfolio investováno",
        "Where you sit against your target":
            "Kde stojíte vůči svému cíli",
        "What drove your return":
            "Co pohánělo váš výnos",
        "Your largest holdings":
            "Vaše největší pozice",
        "Your return over time":
            "Váš výnos v čase",
        "You against your benchmark":
            "Vy vůči svému benchmarku",
        "since":
            "od",
        "vs":
            "vs.",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Čtvrtletní přehled portfolia",
        "Conservative":
            "Konzervativní",
        "Moderate":
            "Vyvážený",
        "Growth":
            "Růstový",
        "Aggressive":
            "Dynamický",
    },

    # ── Greek ───────────────────────────────────────────────────
    "el": {
        "US Equity":
            "Αμερικανικές μετοχές",
        "Intl Equity":
            "Διεθνείς μετοχές",
        "Fixed Income":
            "Ομόλογα",
        "Alternatives":
            "Εναλλακτικές επενδύσεις",
        "Real Assets":
            "Πραγματικά περιουσιακά στοιχεία",
        "Cash":
            "Ρευστά διαθέσιμα",
        "Asset allocation":
            "Κατανομή επενδύσεων",
        "Allocation detail":
            "Ανάλυση κατανομής",
        "Allocation vs strategic target":
            "Κατανομή έναντι στρατηγικού στόχου",
        "Fees and costs":
            "Προμήθειες και έξοδα",
        "What you paid":
            "Τι πληρώσατε",
        "At a glance":
            "Με μια ματιά",
        "Performance vs benchmark":
            "Απόδοση έναντι δείκτη αναφοράς",
        "Contribution to return":
            "Συνεισφορά στην απόδοση",
        "Return by period":
            "Απόδοση ανά περίοδο",
        "Return over time":
            "Απόδοση διαχρονικά",
        "Return this period":
            "Απόδοση αυτής της περιόδου",
        "Ahead of benchmark":
            "Πάνω από τον δείκτη αναφοράς",
        "Risk":
            "Κίνδυνος",
        "Top contributors to return":
            "Κύριοι συντελεστές της απόδοσης",
        "Top detractors from return":
            "Κύριοι επιβαρυντικοί παράγοντες",
        "Behind benchmark":
            "Κάτω από τον δείκτη αναφοράς",
        "Portfolio Growth":
            "Εξέλιξη χαρτοφυλακίου",
        "Portfolio value and recent performance":
            "Αξία χαρτοφυλακίου και πρόσφατη απόδοση",
        "Key takeaways":
            "Βασικά συμπεράσματα",
        "What these terms mean":
            "Τι σημαίνουν αυτοί οι όροι",
        "Advisory fee":
            "Αμοιβή συμβουλευτικής",
        "Fund expenses":
            "Έξοδα αμοιβαίων κεφαλαίων",
        "Total":
            "Σύνολο",
        "Portfolio value":
            "Αξία χαρτοφυλακίου",
        "Portfolio return":
            "Απόδοση χαρτοφυλακίου",
        "Portfolio":
            "Χαρτοφυλάκιο",
        "Benchmark":
            "Δείκτης αναφοράς",
        "Return":
            "Απόδοση",
        "Risk level":
            "Επίπεδο κινδύνου",
        "Target":
            "Στόχος",
        "Actual":
            "Πραγματικό",
        "Contribution":
            "Συνεισφορά",
        "Cumulative":
            "Σωρευτικό",
        "Period":
            "Περίοδος",
        "Difference":
            "Διαφορά",
        "Others":
            "Λοιπά",
        "Asset class":
            "Κατηγορία επένδυσης",
        "Weight":
            "Βαρύτητα",
        "Value":
            "Αξία",
        "Fees":
            "Προμήθειες",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Ένα μείγμα αναφοράς που χρησιμοποιείται για την αξιολόγηση της απόδοσης. Η υπέρβασή του σημαίνει ότι το χαρτοφυλάκιό σας απέδωσε καλύτερα από την αγορά σε αυτό το επίπεδο κινδύνου.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Πόσο πρόσθεσε ή αφαίρεσε κάθε τμήμα του χαρτοφυλακίου από τη συνολική απόδοση. Οι συνεισφορές αθροίζονται στην απόδοση που πραγματικά λάβατε.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Το μακροπρόθεσμο μείγμα που συμφωνήθηκε για το προφίλ κινδύνου σας. Οι θέσεις απομακρύνονται από αυτό καθώς κινούνται οι αγορές και επαναφέρονται κατά την εξισορρόπηση.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Όλες οι αποδόσεις που εμφανίζονται είναι μετά την αφαίρεση των προμηθειών και αντικατοπτρίζουν όσα πραγματικά κερδίσατε.",
        "Valuations":
            "Αποτιμήσεις",
        "as at":
            "στις",
        "Portfolio vs benchmark":
            "Χαρτοφυλάκιο έναντι δείκτη αναφοράς",
        "last column is drift from target":
            "η τελευταία στήλη δείχνει την απόκλιση από τον στόχο",
        "Strategic target":
            "Στρατηγικός στόχος",
        "Net of fees":
            "Μετά από προμήθειες",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Οι προηγούμενες αποδόσεις δεν αποτελούν ένδειξη μελλοντικών αποτελεσμάτων. Τα στοιχεία είναι μετά από προμήθειες, εκτός εάν αναφέρεται διαφορετικά.",
        "Give me a quick summary of this report.":
            "Δώσε μου μια σύντομη περίληψη αυτής της αναφοράς.",
        "Explain the fees I paid this period.":
            "Εξήγησε τις προμήθειες που πλήρωσα αυτή την περίοδο.",
        "How did I do against the benchmark?":
            "Πώς τα πήγα σε σχέση με τον δείκτη αναφοράς;",
        "Allocation donut":
            "Διάγραμμα κατανομής",
        "Actual vs target":
            "Πραγματικό έναντι στόχου",
        "Return drivers":
            "Παράγοντες απόδοσης",
        "Holdings treemap":
            "Χάρτης θέσεων",
        "You vs benchmark":
            "Εσείς έναντι δείκτη αναφοράς",
        "Fee breakdown":
            "Ανάλυση προμηθειών",
        "Money in and out":
            "Εισροές και εκροές",
        "Show me my asset allocation as a donut chart.":
            "Δείξε μου την κατανομή των επενδύσεών μου ως δακτυλιοειδές διάγραμμα.",
        "Show me my allocation against target as a bar chart.":
            "Δείξε μου την κατανομή μου έναντι του στόχου ως ραβδόγραμμα.",
        "Show me what drove my return as a waterfall chart.":
            "Δείξε μου τι οδήγησε την απόδοσή μου ως διάγραμμα καταρράκτη.",
        "Show me my largest holdings as a treemap.":
            "Δείξε μου τις μεγαλύτερες θέσεις μου ως χάρτη δέντρου.",
        "Plot my return over time as a line chart.":
            "Σχεδίασε την απόδοσή μου διαχρονικά ως γραμμικό διάγραμμα.",
        "Chart my return against the benchmark as a bar chart.":
            "Σχεδίασε την απόδοσή μου έναντι του δείκτη αναφοράς ως ραβδόγραμμα.",
        "Show me what I paid as a donut chart.":
            "Δείξε μου τι πλήρωσα ως δακτυλιοειδές διάγραμμα.",
        "Show me my cash flow in and out as a donut chart.":
            "Δείξε μου τις εισροές και εκροές μου ως δακτυλιοειδές διάγραμμα.",
        "How your portfolio is invested":
            "Πώς είναι επενδυμένο το χαρτοφυλάκιό σας",
        "Where you sit against your target":
            "Πού βρίσκεστε σε σχέση με τον στόχο σας",
        "What drove your return":
            "Τι οδήγησε την απόδοσή σας",
        "Your largest holdings":
            "Οι μεγαλύτερες θέσεις σας",
        "Your return over time":
            "Η απόδοσή σας διαχρονικά",
        "You against your benchmark":
            "Εσείς έναντι του δείκτη αναφοράς σας",
        "since":
            "από",
        "vs":
            "έναντι",
        "benchmark":
            "δείκτης αναφοράς",
        "Quarterly Portfolio Review":
            "Τριμηνιαία επισκόπηση χαρτοφυλακίου",
        "Conservative":
            "Συντηρητικό",
        "Moderate":
            "Μέτριο",
        "Growth":
            "Ανάπτυξη",
        "Aggressive":
            "Επιθετικό",
    },

    # ── Turkish ─────────────────────────────────────────────────
    "tr": {
        "US Equity":
            "ABD hisse senetleri",
        "Intl Equity":
            "Uluslararası hisse senetleri",
        "Fixed Income":
            "Sabit getirili menkul kıymetler",
        "Alternatives":
            "Alternatif yatırımlar",
        "Real Assets":
            "Reel varlıklar",
        "Cash":
            "Nakit",
        "Asset allocation":
            "Varlık dağılımı",
        "Allocation detail":
            "Dağılım detayı",
        "Allocation vs strategic target":
            "Stratejik hedefe göre dağılım",
        "Fees and costs":
            "Ücretler ve maliyetler",
        "What you paid":
            "Ödediğiniz tutar",
        "At a glance":
            "Özet bakış",
        "Performance vs benchmark":
            "Kıyas ölçütüne göre performans",
        "Contribution to return":
            "Getiriye katkı",
        "Return by period":
            "Döneme göre getiri",
        "Return over time":
            "Zaman içinde getiri",
        "Return this period":
            "Bu dönemin getirisi",
        "Ahead of benchmark":
            "Kıyas ölçütünün üzerinde",
        "Risk":
            "Risk",
        "Top contributors to return":
            "Getiriye en çok katkı sağlayanlar",
        "Top detractors from return":
            "Getiriyi en çok azaltanlar",
        "Behind benchmark":
            "Kıyas ölçütünün altında",
        "Portfolio Growth":
            "Portföy gelişimi",
        "Portfolio value and recent performance":
            "Portföy değeri ve son dönem performansı",
        "Key takeaways":
            "Öne çıkan bulgular",
        "What these terms mean":
            "Bu terimlerin anlamı",
        "Advisory fee":
            "Danışmanlık ücreti",
        "Fund expenses":
            "Fon giderleri",
        "Total":
            "Toplam",
        "Portfolio value":
            "Portföy değeri",
        "Portfolio return":
            "Portföy getirisi",
        "Portfolio":
            "Portföy",
        "Benchmark":
            "Kıyas ölçütü",
        "Return":
            "Getiri",
        "Risk level":
            "Risk düzeyi",
        "Target":
            "Hedef",
        "Actual":
            "Gerçekleşen",
        "Contribution":
            "Katkı",
        "Cumulative":
            "Kümülatif",
        "Period":
            "Dönem",
        "Difference":
            "Fark",
        "Others":
            "Diğer",
        "Asset class":
            "Varlık sınıfı",
        "Weight":
            "Ağırlık",
        "Value":
            "Değer",
        "Fees":
            "Ücretler",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Performansı değerlendirmek için kullanılan referans bir dağılım. Bunu aşmak, portföyünüzün o risk düzeyinde piyasadan daha iyi bir sonuç verdiği anlamına gelir.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Portföyün her bir bölümünün toplam getiriye ne kadar eklediği veya ondan ne kadar eksilttiği. Katkılar, fiilen elde ettiğiniz getiriyi oluşturur.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Risk profiliniz için üzerinde anlaşılan uzun vadeli dağılım. Piyasalar hareket ettikçe pozisyonlar bundan uzaklaşır ve yeniden dengeleme sırasında geri getirilir.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Gösterilen tüm getiriler ücretler düşüldükten sonraki tutarlardır ve fiilen kazandığınızı yansıtır.",
        "Valuations":
            "Değerlemeler",
        "as at":
            "tarihi itibarıyla",
        "Portfolio vs benchmark":
            "Portföy ve kıyas ölçütü",
        "last column is drift from target":
            "son sütun hedeften sapmayı gösterir",
        "Strategic target":
            "Stratejik hedef",
        "Net of fees":
            "Ücretler düşülmüş",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Geçmiş performans gelecekteki sonuçların göstergesi değildir. Aksi belirtilmedikçe rakamlar ücretler düşüldükten sonraki tutarlardır.",
        "Give me a quick summary of this report.":
            "Bu raporun kısa bir özetini ver.",
        "Explain the fees I paid this period.":
            "Bu dönemde ödediğim ücretleri açıkla.",
        "How did I do against the benchmark?":
            "Kıyas ölçütüne göre nasıl bir performans gösterdim?",
        "Allocation donut":
            "Dağılım halka grafiği",
        "Actual vs target":
            "Gerçekleşen ve hedef",
        "Return drivers":
            "Getiri etkenleri",
        "Holdings treemap":
            "Pozisyon ağaç haritası",
        "You vs benchmark":
            "Siz ve kıyas ölçütü",
        "Fee breakdown":
            "Ücret dağılımı",
        "Money in and out":
            "Giren ve çıkan para",
        "Show me my asset allocation as a donut chart.":
            "Varlık dağılımımı halka grafiği olarak göster.",
        "Show me my allocation against target as a bar chart.":
            "Hedefe göre dağılımımı sütun grafiği olarak göster.",
        "Show me what drove my return as a waterfall chart.":
            "Getirimi neyin sağladığını şelale grafiği olarak göster.",
        "Show me my largest holdings as a treemap.":
            "En büyük pozisyonlarımı ağaç haritası olarak göster.",
        "Plot my return over time as a line chart.":
            "Zaman içindeki getirimi çizgi grafiği olarak çiz.",
        "Chart my return against the benchmark as a bar chart.":
            "Getirimi kıyas ölçütüne göre sütun grafiği olarak çiz.",
        "Show me what I paid as a donut chart.":
            "Ne ödediğimi halka grafiği olarak göster.",
        "Show me my cash flow in and out as a donut chart.":
            "Giren ve çıkan paramı halka grafiği olarak göster.",
        "How your portfolio is invested":
            "Portföyünüzün nasıl yatırıldığı",
        "Where you sit against your target":
            "Hedefinize göre durumunuz",
        "What drove your return":
            "Getirinizi ne sağladı",
        "Your largest holdings":
            "En büyük pozisyonlarınız",
        "Your return over time":
            "Zaman içindeki getiriniz",
        "You against your benchmark":
            "Siz ve kıyas ölçütünüz",
        "since":
            "şu tarihten beri",
        "vs":
            "karşı",
        "benchmark":
            "kıyas ölçütü",
        "Quarterly Portfolio Review":
            "Üç Aylık Portföy Değerlendirmesi",
        "Conservative":
            "Muhafazakâr",
        "Moderate":
            "Dengeli",
        "Growth":
            "Büyüme",
        "Aggressive":
            "Agresif",
    },

    # ── Japanese ────────────────────────────────────────────────
    "ja": {
        "US Equity":
            "米国株式",
        "Intl Equity":
            "海外株式",
        "Fixed Income":
            "債券",
        "Alternatives":
            "オルタナティブ投資",
        "Real Assets":
            "実物資産",
        "Cash":
            "現金",
        "Asset allocation":
            "資産配分",
        "Allocation detail":
            "資産配分の内訳",
        "Allocation vs strategic target":
            "戦略目標との比較",
        "Fees and costs":
            "手数料とコスト",
        "What you paid":
            "お支払い額",
        "At a glance":
            "概要",
        "Performance vs benchmark":
            "ベンチマーク対比の運用成績",
        "Contribution to return":
            "リターンへの寄与",
        "Return by period":
            "期間別リターン",
        "Return over time":
            "リターンの推移",
        "Return this period":
            "当期リターン",
        "Ahead of benchmark":
            "ベンチマークを上回る",
        "Risk":
            "リスク",
        "Top contributors to return":
            "リターンへの主な寄与要因",
        "Top detractors from return":
            "リターンの主な押し下げ要因",
        "Behind benchmark":
            "ベンチマークを下回る",
        "Portfolio Growth":
            "ポートフォリオの推移",
        "Portfolio value and recent performance":
            "ポートフォリオ評価額と直近の運用成績",
        "Key takeaways":
            "主なポイント",
        "What these terms mean":
            "用語の説明",
        "Advisory fee":
            "投資顧問料",
        "Fund expenses":
            "ファンド費用",
        "Total":
            "合計",
        "Portfolio value":
            "ポートフォリオ評価額",
        "Portfolio return":
            "ポートフォリオのリターン",
        "Portfolio":
            "ポートフォリオ",
        "Benchmark":
            "ベンチマーク",
        "Return":
            "リターン",
        "Risk level":
            "リスク水準",
        "Target":
            "目標",
        "Actual":
            "実績",
        "Contribution":
            "寄与度",
        "Cumulative":
            "累積",
        "Period":
            "期間",
        "Difference":
            "差",
        "Others":
            "その他",
        "Asset class":
            "資産クラス",
        "Weight":
            "構成比",
        "Value":
            "評価額",
        "Fees":
            "手数料",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "運用成績を評価するための基準となる資産構成です。これを上回ることは、同じリスク水準の市場よりもお客様のポートフォリオが良好な成績を収めたことを意味します。",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "ポートフォリオの各部分が全体のリターンにどれだけ寄与したか、または押し下げたかを示します。寄与度の合計が実際に得られたリターンとなります。",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "お客様のリスクプロファイルに基づき合意された長期的な資産構成です。市場の変動により保有比率は目標から乖離し、リバランス時に元に戻されます。",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "表示されているリターンはすべて手数料控除後であり、実際にお客様が得た成果を反映しています。",
        "Valuations":
            "評価",
        "as at":
            "基準日",
        "Portfolio vs benchmark":
            "ポートフォリオとベンチマーク",
        "last column is drift from target":
            "最終列は目標からの乖離を示します",
        "Strategic target":
            "戦略目標",
        "Net of fees":
            "手数料控除後",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "過去の運用成績は将来の成果を示すものではありません。特に記載のない限り、数値は手数料控除後です。",
        "Give me a quick summary of this report.":
            "このレポートの概要を簡潔に教えてください。",
        "Explain the fees I paid this period.":
            "今期に支払った手数料について説明してください。",
        "How did I do against the benchmark?":
            "ベンチマークと比べてどうでしたか。",
        "Allocation donut":
            "資産配分のドーナツチャート",
        "Actual vs target":
            "実績と目標",
        "Return drivers":
            "リターンの要因",
        "Holdings treemap":
            "保有銘柄のツリーマップ",
        "You vs benchmark":
            "お客様とベンチマーク",
        "Fee breakdown":
            "手数料の内訳",
        "Money in and out":
            "資金の流出入",
        "Show me my asset allocation as a donut chart.":
            "資産配分をドーナツチャートで見せてください。",
        "Show me my allocation against target as a bar chart.":
            "目標に対する資産配分を棒グラフで見せてください。",
        "Show me what drove my return as a waterfall chart.":
            "リターンの要因をウォーターフォールチャートで見せてください。",
        "Show me my largest holdings as a treemap.":
            "保有額の大きい銘柄をツリーマップで見せてください。",
        "Plot my return over time as a line chart.":
            "リターンの推移を折れ線グラフで示してください。",
        "Chart my return against the benchmark as a bar chart.":
            "ベンチマークとのリターン比較を棒グラフで示してください。",
        "Show me what I paid as a donut chart.":
            "支払った手数料をドーナツチャートで見せてください。",
        "Show me my cash flow in and out as a donut chart.":
            "資金の流出入をドーナツチャートで見せてください。",
        "How your portfolio is invested":
            "ポートフォリオの投資内容",
        "Where you sit against your target":
            "目標に対する現在の位置",
        "What drove your return":
            "リターンの要因",
        "Your largest holdings":
            "保有額の大きい銘柄",
        "Your return over time":
            "リターンの推移",
        "You against your benchmark":
            "ベンチマークとの比較",
        "since":
            "以降",
        "vs":
            "対",
        "benchmark":
            "ベンチマーク",
        "Quarterly Portfolio Review":
            "四半期ポートフォリオレポート",
        "Conservative":
            "保守的",
        "Moderate":
            "中庸",
        "Growth":
            "成長",
        "Aggressive":
            "積極的",
    },

    # ── Chinese (Simplified) ────────────────────────────────────
    "zh": {
        "US Equity":
            "美国股票",
        "Intl Equity":
            "国际股票",
        "Fixed Income":
            "固定收益",
        "Alternatives":
            "另类投资",
        "Real Assets":
            "实物资产",
        "Cash":
            "现金",
        "Asset allocation":
            "资产配置",
        "Allocation detail":
            "配置明细",
        "Allocation vs strategic target":
            "配置与战略目标对比",
        "Fees and costs":
            "费用与成本",
        "What you paid":
            "您支付的费用",
        "At a glance":
            "概览",
        "Performance vs benchmark":
            "相对基准的表现",
        "Contribution to return":
            "对回报的贡献",
        "Return by period":
            "各期回报",
        "Return over time":
            "回报走势",
        "Return this period":
            "本期回报",
        "Ahead of benchmark":
            "领先基准",
        "Risk":
            "风险",
        "Top contributors to return":
            "回报的主要贡献来源",
        "Top detractors from return":
            "回报的主要拖累因素",
        "Behind benchmark":
            "落后基准",
        "Portfolio Growth":
            "组合增长",
        "Portfolio value and recent performance":
            "组合价值与近期表现",
        "Key takeaways":
            "要点摘要",
        "What these terms mean":
            "术语说明",
        "Advisory fee":
            "顾问费",
        "Fund expenses":
            "基金费用",
        "Total":
            "合计",
        "Portfolio value":
            "组合价值",
        "Portfolio return":
            "组合回报",
        "Portfolio":
            "投资组合",
        "Benchmark":
            "基准",
        "Return":
            "回报",
        "Risk level":
            "风险等级",
        "Target":
            "目标",
        "Actual":
            "实际",
        "Contribution":
            "贡献",
        "Cumulative":
            "累计",
        "Period":
            "期间",
        "Difference":
            "差额",
        "Others":
            "其他",
        "Asset class":
            "资产类别",
        "Weight":
            "权重",
        "Value":
            "价值",
        "Fees":
            "费用",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "用于评估表现的参考组合。跑赢它意味着在相同风险水平下，您的投资组合表现优于市场。",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "投资组合的各个部分对总回报的增加或减少幅度。各项贡献相加即为您实际获得的回报。",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "根据您的风险状况商定的长期配置。随着市场波动，持仓会偏离该配置，并在再平衡时调整回来。",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "所示所有回报均已扣除费用，反映您实际获得的收益。",
        "Valuations":
            "估值",
        "as at":
            "截至",
        "Portfolio vs benchmark":
            "组合与基准对比",
        "last column is drift from target":
            "最后一列为相对目标的偏离",
        "Strategic target":
            "战略目标",
        "Net of fees":
            "扣费后",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "过往业绩并不代表未来表现。除另有说明外，数据均为扣费后数字。",
        "Give me a quick summary of this report.":
            "请给我这份报告的简要总结。",
        "Explain the fees I paid this period.":
            "请说明我本期支付的费用。",
        "How did I do against the benchmark?":
            "我相对基准的表现如何？",
        "Allocation donut":
            "配置环形图",
        "Actual vs target":
            "实际与目标",
        "Return drivers":
            "回报驱动因素",
        "Holdings treemap":
            "持仓树状图",
        "You vs benchmark":
            "您与基准",
        "Fee breakdown":
            "费用明细",
        "Money in and out":
            "资金流入与流出",
        "Show me my asset allocation as a donut chart.":
            "请用环形图展示我的资产配置。",
        "Show me my allocation against target as a bar chart.":
            "请用柱状图展示我的配置与目标的对比。",
        "Show me what drove my return as a waterfall chart.":
            "请用瀑布图展示我的回报驱动因素。",
        "Show me my largest holdings as a treemap.":
            "请用树状图展示我的最大持仓。",
        "Plot my return over time as a line chart.":
            "请用折线图绘制我的回报走势。",
        "Chart my return against the benchmark as a bar chart.":
            "请用柱状图绘制我与基准的回报对比。",
        "Show me what I paid as a donut chart.":
            "请用环形图展示我支付的费用。",
        "Show me my cash flow in and out as a donut chart.":
            "请用环形图展示我的资金流入与流出。",
        "How your portfolio is invested":
            "您的投资组合如何配置",
        "Where you sit against your target":
            "您相对目标的位置",
        "What drove your return":
            "是什么驱动了您的回报",
        "Your largest holdings":
            "您的最大持仓",
        "Your return over time":
            "您的回报走势",
        "You against your benchmark":
            "您与基准的对比",
        "since":
            "自",
        "vs":
            "对比",
        "benchmark":
            "基准",
        "Quarterly Portfolio Review":
            "季度投资组合报告",
        "Conservative":
            "保守型",
        "Moderate":
            "稳健型",
        "Growth":
            "成长型",
        "Aggressive":
            "进取型",
    },

    # ── Chinese (Traditional) ───────────────────────────────────
    "zh-hant": {
        "US Equity":
            "美國股票",
        "Intl Equity":
            "國際股票",
        "Fixed Income":
            "固定收益",
        "Alternatives":
            "另類投資",
        "Real Assets":
            "實物資產",
        "Cash":
            "現金",
        "Asset allocation":
            "資產配置",
        "Allocation detail":
            "配置明細",
        "Allocation vs strategic target":
            "配置與策略目標比較",
        "Fees and costs":
            "費用與成本",
        "What you paid":
            "您支付的費用",
        "At a glance":
            "概覽",
        "Performance vs benchmark":
            "相對基準的表現",
        "Contribution to return":
            "對報酬的貢獻",
        "Return by period":
            "各期報酬",
        "Return over time":
            "報酬走勢",
        "Return this period":
            "本期報酬",
        "Ahead of benchmark":
            "領先基準",
        "Risk":
            "風險",
        "Top contributors to return":
            "報酬的主要貢獻來源",
        "Top detractors from return":
            "報酬的主要拖累因素",
        "Behind benchmark":
            "落後基準",
        "Portfolio Growth":
            "投資組合成長",
        "Portfolio value and recent performance":
            "投資組合價值與近期表現",
        "Key takeaways":
            "重點摘要",
        "What these terms mean":
            "名詞解釋",
        "Advisory fee":
            "顧問費",
        "Fund expenses":
            "基金費用",
        "Total":
            "合計",
        "Portfolio value":
            "投資組合價值",
        "Portfolio return":
            "投資組合報酬",
        "Portfolio":
            "投資組合",
        "Benchmark":
            "基準",
        "Return":
            "報酬",
        "Risk level":
            "風險等級",
        "Target":
            "目標",
        "Actual":
            "實際",
        "Contribution":
            "貢獻",
        "Cumulative":
            "累計",
        "Period":
            "期間",
        "Difference":
            "差額",
        "Others":
            "其他",
        "Asset class":
            "資產類別",
        "Weight":
            "權重",
        "Value":
            "價值",
        "Fees":
            "費用",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "用於評估表現的參考組合。超越它代表在相同風險水準下，您的投資組合表現優於市場。",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "投資組合各部分對總報酬的增加或減少幅度。各項貢獻加總即為您實際獲得的報酬。",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "依據您的風險屬性所議定的長期配置。隨著市場波動，持倉會偏離該配置，並於再平衡時調整回來。",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "所列報酬皆已扣除費用，反映您實際獲得的收益。",
        "Valuations":
            "評價",
        "as at":
            "截至",
        "Portfolio vs benchmark":
            "投資組合與基準比較",
        "last column is drift from target":
            "最後一欄為相對目標的偏離",
        "Strategic target":
            "策略目標",
        "Net of fees":
            "扣費後",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "過往績效不代表未來表現。除另有說明外，數據皆為扣費後數字。",
        "Give me a quick summary of this report.":
            "請給我這份報告的簡要摘要。",
        "Explain the fees I paid this period.":
            "請說明我本期支付的費用。",
        "How did I do against the benchmark?":
            "我相對基準的表現如何？",
        "Allocation donut":
            "配置環圈圖",
        "Actual vs target":
            "實際與目標",
        "Return drivers":
            "報酬驅動因素",
        "Holdings treemap":
            "持倉樹狀圖",
        "You vs benchmark":
            "您與基準",
        "Fee breakdown":
            "費用明細",
        "Money in and out":
            "資金流入與流出",
        "Show me my asset allocation as a donut chart.":
            "請用環圈圖顯示我的資產配置。",
        "Show me my allocation against target as a bar chart.":
            "請用長條圖顯示我的配置與目標比較。",
        "Show me what drove my return as a waterfall chart.":
            "請用瀑布圖顯示我的報酬驅動因素。",
        "Show me my largest holdings as a treemap.":
            "請用樹狀圖顯示我最大的持倉。",
        "Plot my return over time as a line chart.":
            "請用折線圖繪製我的報酬走勢。",
        "Chart my return against the benchmark as a bar chart.":
            "請用長條圖繪製我與基準的報酬比較。",
        "Show me what I paid as a donut chart.":
            "請用環圈圖顯示我支付的費用。",
        "Show me my cash flow in and out as a donut chart.":
            "請用環圈圖顯示我的資金流入與流出。",
        "How your portfolio is invested":
            "您的投資組合如何配置",
        "Where you sit against your target":
            "您相對目標的位置",
        "What drove your return":
            "是什麼驅動了您的報酬",
        "Your largest holdings":
            "您最大的持倉",
        "Your return over time":
            "您的報酬走勢",
        "You against your benchmark":
            "您與基準的比較",
        "since":
            "自",
        "vs":
            "對比",
        "benchmark":
            "基準",
        "Quarterly Portfolio Review":
            "季度投資組合報告",
        "Conservative":
            "保守型",
        "Moderate":
            "穩健型",
        "Growth":
            "成長型",
        "Aggressive":
            "積極型",
    },

    # ── Korean ──────────────────────────────────────────────────
    "ko": {
        "US Equity":
            "미국 주식",
        "Intl Equity":
            "해외 주식",
        "Fixed Income":
            "채권",
        "Alternatives":
            "대체투자",
        "Real Assets":
            "실물자산",
        "Cash":
            "현금",
        "Asset allocation":
            "자산배분",
        "Allocation detail":
            "자산배분 상세",
        "Allocation vs strategic target":
            "전략적 목표 대비 배분",
        "Fees and costs":
            "수수료 및 비용",
        "What you paid":
            "지급하신 금액",
        "At a glance":
            "한눈에 보기",
        "Performance vs benchmark":
            "벤치마크 대비 성과",
        "Contribution to return":
            "수익률 기여도",
        "Return by period":
            "기간별 수익률",
        "Return over time":
            "기간에 따른 수익률",
        "Return this period":
            "당기 수익률",
        "Ahead of benchmark":
            "벤치마크 상회",
        "Risk":
            "위험",
        "Top contributors to return":
            "수익률 주요 기여 요인",
        "Top detractors from return":
            "수익률 주요 하락 요인",
        "Behind benchmark":
            "벤치마크 하회",
        "Portfolio Growth":
            "포트폴리오 추이",
        "Portfolio value and recent performance":
            "포트폴리오 평가액 및 최근 성과",
        "Key takeaways":
            "주요 내용",
        "What these terms mean":
            "용어 설명",
        "Advisory fee":
            "자문 수수료",
        "Fund expenses":
            "펀드 비용",
        "Total":
            "합계",
        "Portfolio value":
            "포트폴리오 평가액",
        "Portfolio return":
            "포트폴리오 수익률",
        "Portfolio":
            "포트폴리오",
        "Benchmark":
            "벤치마크",
        "Return":
            "수익률",
        "Risk level":
            "위험 수준",
        "Target":
            "목표",
        "Actual":
            "실제",
        "Contribution":
            "기여도",
        "Cumulative":
            "누적",
        "Period":
            "기간",
        "Difference":
            "차이",
        "Others":
            "기타",
        "Asset class":
            "자산군",
        "Weight":
            "비중",
        "Value":
            "평가액",
        "Fees":
            "수수료",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "성과를 평가하기 위한 기준 자산구성입니다. 이를 상회한다는 것은 동일한 위험 수준에서 고객님의 포트폴리오가 시장보다 나은 성과를 냈다는 의미입니다.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "포트폴리오의 각 부분이 전체 수익률에 얼마나 더하거나 뺐는지를 나타냅니다. 기여도의 합계가 실제로 얻으신 수익률입니다.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "고객님의 위험성향에 맞추어 합의된 장기 자산구성입니다. 시장이 움직이면서 보유 비중은 이 구성에서 벗어나며, 리밸런싱 시 다시 조정됩니다.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "표시된 모든 수익률은 수수료 차감 후 기준으로, 실제로 얻으신 성과를 반영합니다.",
        "Valuations":
            "평가",
        "as at":
            "기준일",
        "Portfolio vs benchmark":
            "포트폴리오 대 벤치마크",
        "last column is drift from target":
            "마지막 열은 목표 대비 괴리를 나타냅니다",
        "Strategic target":
            "전략적 목표",
        "Net of fees":
            "수수료 차감 후",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "과거의 성과가 미래의 결과를 보장하지 않습니다. 별도의 언급이 없는 한 수치는 수수료 차감 후 기준입니다.",
        "Give me a quick summary of this report.":
            "이 리포트를 간단히 요약해 주세요.",
        "Explain the fees I paid this period.":
            "이번 기간에 지급한 수수료를 설명해 주세요.",
        "How did I do against the benchmark?":
            "벤치마크와 비교해 어떤 성과를 냈나요?",
        "Allocation donut":
            "자산배분 도넛 차트",
        "Actual vs target":
            "실제 대 목표",
        "Return drivers":
            "수익률 요인",
        "Holdings treemap":
            "보유종목 트리맵",
        "You vs benchmark":
            "고객님 대 벤치마크",
        "Fee breakdown":
            "수수료 내역",
        "Money in and out":
            "자금 유입 및 유출",
        "Show me my asset allocation as a donut chart.":
            "제 자산배분을 도넛 차트로 보여 주세요.",
        "Show me my allocation against target as a bar chart.":
            "목표 대비 자산배분을 막대 차트로 보여 주세요.",
        "Show me what drove my return as a waterfall chart.":
            "수익률을 이끈 요인을 워터폴 차트로 보여 주세요.",
        "Show me my largest holdings as a treemap.":
            "가장 큰 보유종목을 트리맵으로 보여 주세요.",
        "Plot my return over time as a line chart.":
            "기간에 따른 제 수익률을 선 차트로 그려 주세요.",
        "Chart my return against the benchmark as a bar chart.":
            "벤치마크 대비 제 수익률을 막대 차트로 그려 주세요.",
        "Show me what I paid as a donut chart.":
            "제가 지급한 금액을 도넛 차트로 보여 주세요.",
        "Show me my cash flow in and out as a donut chart.":
            "제 자금 유입과 유출을 도넛 차트로 보여 주세요.",
        "How your portfolio is invested":
            "고객님의 포트폴리오 투자 현황",
        "Where you sit against your target":
            "목표 대비 현재 위치",
        "What drove your return":
            "수익률을 이끈 요인",
        "Your largest holdings":
            "고객님의 주요 보유종목",
        "Your return over time":
            "기간에 따른 고객님의 수익률",
        "You against your benchmark":
            "고객님과 벤치마크 비교",
        "since":
            "이후",
        "vs":
            "대비",
        "benchmark":
            "벤치마크",
        "Quarterly Portfolio Review":
            "분기 포트폴리오 리포트",
        "Conservative":
            "안정형",
        "Moderate":
            "중립형",
        "Growth":
            "성장형",
        "Aggressive":
            "공격형",
    },

    # ── Arabic ──────────────────────────────────────────────────
    "ar": {
        "US Equity":
            "أسهم أمريكية",
        "Intl Equity":
            "أسهم دولية",
        "Fixed Income":
            "الدخل الثابت",
        "Alternatives":
            "استثمارات بديلة",
        "Real Assets":
            "أصول عينية",
        "Cash":
            "النقد",
        "Asset allocation":
            "توزيع الأصول",
        "Allocation detail":
            "تفاصيل التوزيع",
        "Allocation vs strategic target":
            "التوزيع مقابل الهدف الاستراتيجي",
        "Fees and costs":
            "الرسوم والتكاليف",
        "What you paid":
            "ما دفعته",
        "At a glance":
            "نظرة عامة",
        "Performance vs benchmark":
            "الأداء مقابل المؤشر الاسترشادي",
        "Contribution to return":
            "المساهمة في العائد",
        "Return by period":
            "العائد حسب الفترة",
        "Return over time":
            "العائد عبر الزمن",
        "Return this period":
            "عائد هذه الفترة",
        "Ahead of benchmark":
            "متقدم على المؤشر",
        "Risk":
            "المخاطر",
        "Top contributors to return":
            "أكبر المساهمين في العائد",
        "Top detractors from return":
            "أكبر المؤثرين سلباً في العائد",
        "Behind benchmark":
            "متأخر عن المؤشر",
        "Portfolio Growth":
            "نمو المحفظة",
        "Portfolio value and recent performance":
            "قيمة المحفظة والأداء الأخير",
        "Key takeaways":
            "أبرز النقاط",
        "What these terms mean":
            "معاني هذه المصطلحات",
        "Advisory fee":
            "رسوم الاستشارة",
        "Fund expenses":
            "مصاريف الصناديق",
        "Total":
            "الإجمالي",
        "Portfolio value":
            "قيمة المحفظة",
        "Portfolio return":
            "عائد المحفظة",
        "Portfolio":
            "المحفظة",
        "Benchmark":
            "المؤشر الاسترشادي",
        "Return":
            "العائد",
        "Risk level":
            "مستوى المخاطر",
        "Target":
            "الهدف",
        "Actual":
            "الفعلي",
        "Contribution":
            "المساهمة",
        "Cumulative":
            "التراكمي",
        "Period":
            "الفترة",
        "Difference":
            "الفرق",
        "Others":
            "أخرى",
        "Asset class":
            "فئة الأصول",
        "Weight":
            "الوزن",
        "Value":
            "القيمة",
        "Fees":
            "الرسوم",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "مزيج مرجعي يُستخدم لتقييم الأداء. تجاوزه يعني أن محفظتك حققت أداءً أفضل من السوق عند مستوى المخاطر نفسه.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "مقدار ما أضافه كل جزء من المحفظة إلى إجمالي العائد أو اقتطعه منه. مجموع المساهمات يساوي العائد الذي حصلت عليه فعلياً.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "المزيج طويل الأجل المتفق عليه لملف المخاطر الخاص بك. تبتعد المراكز عنه مع تحركات الأسواق، ويُعاد ضبطها عند إعادة التوازن.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "جميع العوائد المعروضة بعد خصم الرسوم، وبالتالي تعكس ما كسبته فعلياً.",
        "Valuations":
            "التقييمات",
        "as at":
            "كما في",
        "Portfolio vs benchmark":
            "المحفظة مقابل المؤشر",
        "last column is drift from target":
            "العمود الأخير يوضح الانحراف عن الهدف",
        "Strategic target":
            "الهدف الاستراتيجي",
        "Net of fees":
            "بعد خصم الرسوم",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "الأداء السابق ليس مؤشراً على النتائج المستقبلية. الأرقام بعد خصم الرسوم ما لم يُذكر خلاف ذلك.",
        "Give me a quick summary of this report.":
            "أعطني ملخصاً سريعاً لهذا التقرير.",
        "Explain the fees I paid this period.":
            "اشرح الرسوم التي دفعتها في هذه الفترة.",
        "How did I do against the benchmark?":
            "كيف كان أدائي مقابل المؤشر الاسترشادي؟",
        "Allocation donut":
            "مخطط توزيع الأصول",
        "Actual vs target":
            "الفعلي مقابل الهدف",
        "Return drivers":
            "محركات العائد",
        "Holdings treemap":
            "خريطة الحيازات",
        "You vs benchmark":
            "أنت مقابل المؤشر",
        "Fee breakdown":
            "تفصيل الرسوم",
        "Money in and out":
            "التدفقات الداخلة والخارجة",
        "Show me my asset allocation as a donut chart.":
            "اعرض توزيع أصولي في مخطط دائري.",
        "Show me my allocation against target as a bar chart.":
            "اعرض توزيعي مقابل الهدف في مخطط أعمدة.",
        "Show me what drove my return as a waterfall chart.":
            "اعرض محركات عائدي في مخطط شلالي.",
        "Show me my largest holdings as a treemap.":
            "اعرض أكبر حيازاتي في خريطة شجرية.",
        "Plot my return over time as a line chart.":
            "ارسم عائدي عبر الزمن في مخطط خطي.",
        "Chart my return against the benchmark as a bar chart.":
            "ارسم عائدي مقابل المؤشر في مخطط أعمدة.",
        "Show me what I paid as a donut chart.":
            "اعرض ما دفعته في مخطط دائري.",
        "Show me my cash flow in and out as a donut chart.":
            "اعرض تدفقاتي الداخلة والخارجة في مخطط دائري.",
        "How your portfolio is invested":
            "كيف استُثمرت محفظتك",
        "Where you sit against your target":
            "موقعك مقابل هدفك",
        "What drove your return":
            "ما الذي حرّك عائدك",
        "Your largest holdings":
            "أكبر حيازاتك",
        "Your return over time":
            "عائدك عبر الزمن",
        "You against your benchmark":
            "أنت مقابل مؤشرك الاسترشادي",
        "since":
            "منذ",
        "vs":
            "مقابل",
        "benchmark":
            "المؤشر الاسترشادي",
        "Quarterly Portfolio Review":
            "المراجعة الربع سنوية للمحفظة",
        "Conservative":
            "متحفظ",
        "Moderate":
            "متوازن",
        "Growth":
            "نمو",
        "Aggressive":
            "جريء",
    },

    # ── Hebrew ──────────────────────────────────────────────────
    "he": {
        "US Equity":
            "מניות ארה\"ב",
        "Intl Equity":
            "מניות בינלאומיות",
        "Fixed Income":
            "אג\"ח",
        "Alternatives":
            "השקעות אלטרנטיביות",
        "Real Assets":
            "נכסים ריאליים",
        "Cash":
            "מזומן",
        "Asset allocation":
            "הקצאת נכסים",
        "Allocation detail":
            "פירוט ההקצאה",
        "Allocation vs strategic target":
            "הקצאה מול יעד אסטרטגי",
        "Fees and costs":
            "עמלות ועלויות",
        "What you paid":
            "מה שילמת",
        "At a glance":
            "במבט מהיר",
        "Performance vs benchmark":
            "ביצועים מול מדד הייחוס",
        "Contribution to return":
            "תרומה לתשואה",
        "Return by period":
            "תשואה לפי תקופה",
        "Return over time":
            "תשואה לאורך זמן",
        "Return this period":
            "תשואת התקופה",
        "Ahead of benchmark":
            "מעל מדד הייחוס",
        "Risk":
            "סיכון",
        "Top contributors to return":
            "התורמים המובילים לתשואה",
        "Top detractors from return":
            "הגורמים המכבידים על התשואה",
        "Behind benchmark":
            "מתחת למדד הייחוס",
        "Portfolio Growth":
            "התפתחות התיק",
        "Portfolio value and recent performance":
            "שווי התיק וביצועים אחרונים",
        "Key takeaways":
            "עיקרי הדברים",
        "What these terms mean":
            "משמעות המונחים",
        "Advisory fee":
            "דמי ייעוץ",
        "Fund expenses":
            "הוצאות הקרנות",
        "Total":
            "סה\"כ",
        "Portfolio value":
            "שווי התיק",
        "Portfolio return":
            "תשואת התיק",
        "Portfolio":
            "תיק",
        "Benchmark":
            "מדד ייחוס",
        "Return":
            "תשואה",
        "Risk level":
            "רמת סיכון",
        "Target":
            "יעד",
        "Actual":
            "בפועל",
        "Contribution":
            "תרומה",
        "Cumulative":
            "מצטבר",
        "Period":
            "תקופה",
        "Difference":
            "הפרש",
        "Others":
            "אחרים",
        "Asset class":
            "סוג נכס",
        "Weight":
            "משקל",
        "Value":
            "שווי",
        "Fees":
            "עמלות",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "תמהיל ייחוס המשמש להערכת ביצועים. הכאה שלו משמעותה שהתיק שלך השיג תוצאה טובה יותר מהשוק באותה רמת סיכון.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "כמה כל חלק בתיק הוסיף לתשואה הכוללת או גרע ממנה. סכום התרומות שווה לתשואה שקיבלת בפועל.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "התמהיל ארוך הטווח שסוכם עבור פרופיל הסיכון שלך. האחזקות מתרחקות ממנו עם תנודות השוק ומוחזרות אליו באיזון מחדש.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "כל התשואות המוצגות הן לאחר ניכוי עמלות, ולכן משקפות את מה שהרווחת בפועל.",
        "Valuations":
            "הערכות שווי",
        "as at":
            "נכון ליום",
        "Portfolio vs benchmark":
            "תיק מול מדד ייחוס",
        "last column is drift from target":
            "העמודה האחרונה מציגה את הסטייה מהיעד",
        "Strategic target":
            "יעד אסטרטגי",
        "Net of fees":
            "בניכוי עמלות",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "ביצועי העבר אינם מעידים על תוצאות עתידיות. הנתונים הם בניכוי עמלות אלא אם צוין אחרת.",
        "Give me a quick summary of this report.":
            "תן לי סיכום קצר של הדוח הזה.",
        "Explain the fees I paid this period.":
            "הסבר את העמלות ששילמתי בתקופה זו.",
        "How did I do against the benchmark?":
            "איך הצלחתי מול מדד הייחוס?",
        "Allocation donut":
            "תרשים הקצאה",
        "Actual vs target":
            "בפועל מול יעד",
        "Return drivers":
            "מניעי התשואה",
        "Holdings treemap":
            "מפת אחזקות",
        "You vs benchmark":
            "אתה מול מדד הייחוס",
        "Fee breakdown":
            "פירוט עמלות",
        "Money in and out":
            "כספים נכנסים ויוצאים",
        "Show me my asset allocation as a donut chart.":
            "הצג את הקצאת הנכסים שלי בתרשים טבעת.",
        "Show me my allocation against target as a bar chart.":
            "הצג את ההקצאה שלי מול היעד בתרשים עמודות.",
        "Show me what drove my return as a waterfall chart.":
            "הצג מה הניע את התשואה שלי בתרשים מפל.",
        "Show me my largest holdings as a treemap.":
            "הצג את האחזקות הגדולות שלי במפת עץ.",
        "Plot my return over time as a line chart.":
            "שרטט את התשואה שלי לאורך זמן בתרשים קו.",
        "Chart my return against the benchmark as a bar chart.":
            "שרטט את התשואה שלי מול מדד הייחוס בתרשים עמודות.",
        "Show me what I paid as a donut chart.":
            "הצג מה שילמתי בתרשים טבעת.",
        "Show me my cash flow in and out as a donut chart.":
            "הצג את הכספים הנכנסים והיוצאים שלי בתרשים טבעת.",
        "How your portfolio is invested":
            "כיצד מושקע התיק שלך",
        "Where you sit against your target":
            "היכן אתה עומד מול היעד שלך",
        "What drove your return":
            "מה הניע את התשואה שלך",
        "Your largest holdings":
            "האחזקות הגדולות שלך",
        "Your return over time":
            "התשואה שלך לאורך זמן",
        "You against your benchmark":
            "אתה מול מדד הייחוס שלך",
        "since":
            "מאז",
        "vs":
            "מול",
        "benchmark":
            "מדד ייחוס",
        "Quarterly Portfolio Review":
            "סקירת תיק רבעונית",
        "Conservative":
            "שמרני",
        "Moderate":
            "מאוזן",
        "Growth":
            "צמיחה",
        "Aggressive":
            "אגרסיבי",
    },

    # ── Russian ─────────────────────────────────────────────────
    "ru": {
        "US Equity":
            "Американские акции",
        "Intl Equity":
            "Международные акции",
        "Fixed Income":
            "Облигации",
        "Alternatives":
            "Альтернативные инвестиции",
        "Real Assets":
            "Реальные активы",
        "Cash":
            "Денежные средства",
        "Asset allocation":
            "Распределение активов",
        "Allocation detail":
            "Детализация распределения",
        "Allocation vs strategic target":
            "Распределение относительно стратегической цели",
        "Fees and costs":
            "Комиссии и расходы",
        "What you paid":
            "Что вы заплатили",
        "At a glance":
            "Кратко",
        "Performance vs benchmark":
            "Результаты относительно бенчмарка",
        "Contribution to return":
            "Вклад в доходность",
        "Return by period":
            "Доходность по периодам",
        "Return over time":
            "Доходность во времени",
        "Return this period":
            "Доходность за период",
        "Ahead of benchmark":
            "Выше бенчмарка",
        "Risk":
            "Риск",
        "Top contributors to return":
            "Основные источники доходности",
        "Top detractors from return":
            "Основные факторы снижения доходности",
        "Behind benchmark":
            "Ниже бенчмарка",
        "Portfolio Growth":
            "Динамика портфеля",
        "Portfolio value and recent performance":
            "Стоимость портфеля и последние результаты",
        "Key takeaways":
            "Ключевые выводы",
        "What these terms mean":
            "Значение этих терминов",
        "Advisory fee":
            "Комиссия за консультирование",
        "Fund expenses":
            "Расходы фондов",
        "Total":
            "Итого",
        "Portfolio value":
            "Стоимость портфеля",
        "Portfolio return":
            "Доходность портфеля",
        "Portfolio":
            "Портфель",
        "Benchmark":
            "Бенчмарк",
        "Return":
            "Доходность",
        "Risk level":
            "Уровень риска",
        "Target":
            "Цель",
        "Actual":
            "Фактически",
        "Contribution":
            "Вклад",
        "Cumulative":
            "Накопленная",
        "Period":
            "Период",
        "Difference":
            "Разница",
        "Others":
            "Прочее",
        "Asset class":
            "Класс активов",
        "Weight":
            "Вес",
        "Value":
            "Стоимость",
        "Fees":
            "Комиссии",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Эталонный набор активов, используемый для оценки результатов. Превышение означает, что ваш портфель показал лучший результат, чем рынок при том же уровне риска.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Насколько каждая часть портфеля увеличила или уменьшила общую доходность. Сумма вкладов равна доходности, которую вы фактически получили.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Долгосрочная структура, согласованная для вашего риск-профиля. Позиции отклоняются от неё при движении рынков и возвращаются при ребалансировке.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Вся показанная доходность указана после вычета комиссий и отражает то, что вы фактически заработали.",
        "Valuations":
            "Оценка",
        "as at":
            "по состоянию на",
        "Portfolio vs benchmark":
            "Портфель и бенчмарк",
        "last column is drift from target":
            "последний столбец показывает отклонение от цели",
        "Strategic target":
            "Стратегическая цель",
        "Net of fees":
            "После вычета комиссий",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Прошлые результаты не являются показателем будущих. Данные приведены после вычета комиссий, если не указано иное.",
        "Give me a quick summary of this report.":
            "Дайте краткое резюме этого отчёта.",
        "Explain the fees I paid this period.":
            "Объясните комиссии, которые я заплатил за этот период.",
        "How did I do against the benchmark?":
            "Каковы мои результаты относительно бенчмарка?",
        "Allocation donut":
            "Кольцевая диаграмма распределения",
        "Actual vs target":
            "Фактически и цель",
        "Return drivers":
            "Факторы доходности",
        "Holdings treemap":
            "Карта позиций",
        "You vs benchmark":
            "Вы и бенчмарк",
        "Fee breakdown":
            "Структура комиссий",
        "Money in and out":
            "Поступления и списания",
        "Show me my asset allocation as a donut chart.":
            "Покажите распределение моих активов в виде кольцевой диаграммы.",
        "Show me my allocation against target as a bar chart.":
            "Покажите моё распределение относительно цели в виде столбчатой диаграммы.",
        "Show me what drove my return as a waterfall chart.":
            "Покажите факторы моей доходности в виде каскадной диаграммы.",
        "Show me my largest holdings as a treemap.":
            "Покажите мои крупнейшие позиции в виде древовидной карты.",
        "Plot my return over time as a line chart.":
            "Постройте мою доходность во времени в виде линейного графика.",
        "Chart my return against the benchmark as a bar chart.":
            "Постройте мою доходность относительно бенчмарка в виде столбчатой диаграммы.",
        "Show me what I paid as a donut chart.":
            "Покажите, что я заплатил, в виде кольцевой диаграммы.",
        "Show me my cash flow in and out as a donut chart.":
            "Покажите мои поступления и списания в виде кольцевой диаграммы.",
        "How your portfolio is invested":
            "Как инвестирован ваш портфель",
        "Where you sit against your target":
            "Ваше положение относительно цели",
        "What drove your return":
            "Что определило вашу доходность",
        "Your largest holdings":
            "Ваши крупнейшие позиции",
        "Your return over time":
            "Ваша доходность во времени",
        "You against your benchmark":
            "Вы и ваш бенчмарк",
        "since":
            "с",
        "vs":
            "против",
        "benchmark":
            "бенчмарк",
        "Quarterly Portfolio Review":
            "Квартальный обзор портфеля",
        "Conservative":
            "Консервативный",
        "Moderate":
            "Умеренный",
        "Growth":
            "Ростовой",
        "Aggressive":
            "Агрессивный",
    },

    # ── Ukrainian ───────────────────────────────────────────────
    "uk": {
        "US Equity":
            "Американські акції",
        "Intl Equity":
            "Міжнародні акції",
        "Fixed Income":
            "Облігації",
        "Alternatives":
            "Альтернативні інвестиції",
        "Real Assets":
            "Реальні активи",
        "Cash":
            "Грошові кошти",
        "Asset allocation":
            "Розподіл активів",
        "Allocation detail":
            "Деталізація розподілу",
        "Allocation vs strategic target":
            "Розподіл відносно стратегічної цілі",
        "Fees and costs":
            "Комісії та витрати",
        "What you paid":
            "Що ви сплатили",
        "At a glance":
            "Стисло",
        "Performance vs benchmark":
            "Результати відносно бенчмарку",
        "Contribution to return":
            "Внесок у дохідність",
        "Return by period":
            "Дохідність за періодами",
        "Return over time":
            "Дохідність у часі",
        "Return this period":
            "Дохідність за період",
        "Ahead of benchmark":
            "Вище бенчмарку",
        "Risk":
            "Ризик",
        "Top contributors to return":
            "Основні джерела дохідності",
        "Top detractors from return":
            "Основні чинники зниження дохідності",
        "Behind benchmark":
            "Нижче бенчмарку",
        "Portfolio Growth":
            "Динаміка портфеля",
        "Portfolio value and recent performance":
            "Вартість портфеля та останні результати",
        "Key takeaways":
            "Ключові висновки",
        "What these terms mean":
            "Значення цих термінів",
        "Advisory fee":
            "Комісія за консультування",
        "Fund expenses":
            "Витрати фондів",
        "Total":
            "Разом",
        "Portfolio value":
            "Вартість портфеля",
        "Portfolio return":
            "Дохідність портфеля",
        "Portfolio":
            "Портфель",
        "Benchmark":
            "Бенчмарк",
        "Return":
            "Дохідність",
        "Risk level":
            "Рівень ризику",
        "Target":
            "Ціль",
        "Actual":
            "Фактично",
        "Contribution":
            "Внесок",
        "Cumulative":
            "Накопичена",
        "Period":
            "Період",
        "Difference":
            "Різниця",
        "Others":
            "Інше",
        "Asset class":
            "Клас активів",
        "Weight":
            "Вага",
        "Value":
            "Вартість",
        "Fees":
            "Комісії",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Еталонний набір активів, що використовується для оцінки результатів. Перевищення означає, що ваш портфель показав кращий результат, ніж ринок за того самого рівня ризику.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Наскільки кожна частина портфеля збільшила або зменшила загальну дохідність. Сума внесків дорівнює дохідності, яку ви фактично отримали.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Довгострокова структура, погоджена для вашого ризик-профілю. Позиції відхиляються від неї з рухом ринків і повертаються під час ребалансування.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Уся показана дохідність наведена після вирахування комісій і відображає те, що ви фактично заробили.",
        "Valuations":
            "Оцінка",
        "as at":
            "станом на",
        "Portfolio vs benchmark":
            "Портфель і бенчмарк",
        "last column is drift from target":
            "останній стовпець показує відхилення від цілі",
        "Strategic target":
            "Стратегічна ціль",
        "Net of fees":
            "Після вирахування комісій",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Минулі результати не є показником майбутніх. Дані наведено після вирахування комісій, якщо не зазначено інше.",
        "Give me a quick summary of this report.":
            "Дайте стислий підсумок цього звіту.",
        "Explain the fees I paid this period.":
            "Поясніть комісії, які я сплатив за цей період.",
        "How did I do against the benchmark?":
            "Які мої результати відносно бенчмарку?",
        "Allocation donut":
            "Кільцева діаграма розподілу",
        "Actual vs target":
            "Фактично та ціль",
        "Return drivers":
            "Чинники дохідності",
        "Holdings treemap":
            "Карта позицій",
        "You vs benchmark":
            "Ви і бенчмарк",
        "Fee breakdown":
            "Структура комісій",
        "Money in and out":
            "Надходження та списання",
        "Show me my asset allocation as a donut chart.":
            "Покажіть розподіл моїх активів у вигляді кільцевої діаграми.",
        "Show me my allocation against target as a bar chart.":
            "Покажіть мій розподіл відносно цілі у вигляді стовпчикової діаграми.",
        "Show me what drove my return as a waterfall chart.":
            "Покажіть чинники моєї дохідності у вигляді каскадної діаграми.",
        "Show me my largest holdings as a treemap.":
            "Покажіть мої найбільші позиції у вигляді деревовидної карти.",
        "Plot my return over time as a line chart.":
            "Побудуйте мою дохідність у часі у вигляді лінійного графіка.",
        "Chart my return against the benchmark as a bar chart.":
            "Побудуйте мою дохідність відносно бенчмарку у вигляді стовпчикової діаграми.",
        "Show me what I paid as a donut chart.":
            "Покажіть, що я сплатив, у вигляді кільцевої діаграми.",
        "Show me my cash flow in and out as a donut chart.":
            "Покажіть мої надходження та списання у вигляді кільцевої діаграми.",
        "How your portfolio is invested":
            "Як інвестовано ваш портфель",
        "Where you sit against your target":
            "Ваше становище відносно цілі",
        "What drove your return":
            "Що визначило вашу дохідність",
        "Your largest holdings":
            "Ваші найбільші позиції",
        "Your return over time":
            "Ваша дохідність у часі",
        "You against your benchmark":
            "Ви і ваш бенчмарк",
        "since":
            "з",
        "vs":
            "проти",
        "benchmark":
            "бенчмарк",
        "Quarterly Portfolio Review":
            "Квартальний огляд портфеля",
        "Conservative":
            "Консервативний",
        "Moderate":
            "Помірний",
        "Growth":
            "Зростання",
        "Aggressive":
            "Агресивний",
    },

    # ── Bulgarian ───────────────────────────────────────────────
    "bg": {
        "US Equity":
            "Американски акции",
        "Intl Equity":
            "Международни акции",
        "Fixed Income":
            "Облигации",
        "Alternatives":
            "Алтернативни инвестиции",
        "Real Assets":
            "Реални активи",
        "Cash":
            "Парични средства",
        "Asset allocation":
            "Разпределение на активите",
        "Allocation detail":
            "Детайли на разпределението",
        "Allocation vs strategic target":
            "Разпределение спрямо стратегическата цел",
        "Fees and costs":
            "Такси и разходи",
        "What you paid":
            "Какво платихте",
        "At a glance":
            "Накратко",
        "Performance vs benchmark":
            "Резултати спрямо бенчмарка",
        "Contribution to return":
            "Принос към доходността",
        "Return by period":
            "Доходност по периоди",
        "Return over time":
            "Доходност във времето",
        "Return this period":
            "Доходност за периода",
        "Ahead of benchmark":
            "Над бенчмарка",
        "Risk":
            "Риск",
        "Top contributors to return":
            "Основни източници на доходност",
        "Top detractors from return":
            "Основни фактори, намаляващи доходността",
        "Behind benchmark":
            "Под бенчмарка",
        "Portfolio Growth":
            "Развитие на портфейла",
        "Portfolio value and recent performance":
            "Стойност на портфейла и последни резултати",
        "Key takeaways":
            "Основни изводи",
        "What these terms mean":
            "Значение на тези понятия",
        "Advisory fee":
            "Такса за консултиране",
        "Fund expenses":
            "Разходи на фондовете",
        "Total":
            "Общо",
        "Portfolio value":
            "Стойност на портфейла",
        "Portfolio return":
            "Доходност на портфейла",
        "Portfolio":
            "Портфейл",
        "Benchmark":
            "Бенчмарк",
        "Return":
            "Доходност",
        "Risk level":
            "Ниво на риск",
        "Target":
            "Цел",
        "Actual":
            "Действително",
        "Contribution":
            "Принос",
        "Cumulative":
            "Натрупана",
        "Period":
            "Период",
        "Difference":
            "Разлика",
        "Others":
            "Други",
        "Asset class":
            "Клас активи",
        "Weight":
            "Тегло",
        "Value":
            "Стойност",
        "Fees":
            "Такси",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Еталонен набор от активи, използван за оценка на резултатите. Надминаването му означава, че вашият портфейл се е представил по-добре от пазара при същото ниво на риск.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Колко всяка част от портфейла е добавила към общата доходност или е отнела от нея. Сумата на приносите е равна на доходността, която действително сте получили.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Дългосрочната структура, договорена за вашия рисков профил. Позициите се отклоняват от нея с движението на пазарите и се връщат при ребалансиране.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Всички показани доходности са след приспадане на такси и отразяват това, което действително сте спечелили.",
        "Valuations":
            "Оценки",
        "as at":
            "към",
        "Portfolio vs benchmark":
            "Портфейл спрямо бенчмарк",
        "last column is drift from target":
            "последната колона показва отклонението от целта",
        "Strategic target":
            "Стратегическа цел",
        "Net of fees":
            "След приспадане на такси",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Миналите резултати не са показателни за бъдещи резултати. Данните са след приспадане на такси, освен ако не е посочено друго.",
        "Give me a quick summary of this report.":
            "Дай ми кратко обобщение на този отчет.",
        "Explain the fees I paid this period.":
            "Обясни таксите, които платих през този период.",
        "How did I do against the benchmark?":
            "Как се представих спрямо бенчмарка?",
        "Allocation donut":
            "Кръгова диаграма на разпределението",
        "Actual vs target":
            "Действително спрямо цел",
        "Return drivers":
            "Фактори на доходността",
        "Holdings treemap":
            "Карта на позициите",
        "You vs benchmark":
            "Вие и бенчмаркът",
        "Fee breakdown":
            "Структура на таксите",
        "Money in and out":
            "Входящи и изходящи средства",
        "Show me my asset allocation as a donut chart.":
            "Покажи разпределението на активите ми като пръстеновидна диаграма.",
        "Show me my allocation against target as a bar chart.":
            "Покажи разпределението ми спрямо целта като стълбовидна диаграма.",
        "Show me what drove my return as a waterfall chart.":
            "Покажи какво определи доходността ми като каскадна диаграма.",
        "Show me my largest holdings as a treemap.":
            "Покажи най-големите ми позиции като дървовидна карта.",
        "Plot my return over time as a line chart.":
            "Начертай доходността ми във времето като линейна диаграма.",
        "Chart my return against the benchmark as a bar chart.":
            "Начертай доходността ми спрямо бенчмарка като стълбовидна диаграма.",
        "Show me what I paid as a donut chart.":
            "Покажи какво платих като пръстеновидна диаграма.",
        "Show me my cash flow in and out as a donut chart.":
            "Покажи входящите и изходящите ми средства като пръстеновидна диаграма.",
        "How your portfolio is invested":
            "Как е инвестиран вашият портфейл",
        "Where you sit against your target":
            "Къде се намирате спрямо целта си",
        "What drove your return":
            "Какво определи вашата доходност",
        "Your largest holdings":
            "Вашите най-големи позиции",
        "Your return over time":
            "Вашата доходност във времето",
        "You against your benchmark":
            "Вие спрямо вашия бенчмарк",
        "since":
            "от",
        "vs":
            "спрямо",
        "benchmark":
            "бенчмарк",
        "Quarterly Portfolio Review":
            "Тримесечен преглед на портфейла",
        "Conservative":
            "Консервативен",
        "Moderate":
            "Умерен",
        "Growth":
            "Растеж",
        "Aggressive":
            "Агресивен",
    },

    # ── Macedonian ──────────────────────────────────────────────
    "mk": {
        "US Equity":
            "Американски акции",
        "Intl Equity":
            "Меѓународни акции",
        "Fixed Income":
            "Обврзници",
        "Alternatives":
            "Алтернативни инвестиции",
        "Real Assets":
            "Реални средства",
        "Cash":
            "Готовина",
        "Asset allocation":
            "Распределба на средствата",
        "Allocation detail":
            "Детали за распределбата",
        "Allocation vs strategic target":
            "Распределба во однос на стратешката цел",
        "Fees and costs":
            "Провизии и трошоци",
        "What you paid":
            "Што плативте",
        "At a glance":
            "Накратко",
        "Performance vs benchmark":
            "Резултати во однос на бенчмаркот",
        "Contribution to return":
            "Придонес кон приносот",
        "Return by period":
            "Принос по периоди",
        "Return over time":
            "Принос низ времето",
        "Return this period":
            "Принос за периодот",
        "Ahead of benchmark":
            "Над бенчмаркот",
        "Risk":
            "Ризик",
        "Top contributors to return":
            "Главни извори на принос",
        "Top detractors from return":
            "Главни фактори што го намалуваат приносот",
        "Behind benchmark":
            "Под бенчмаркот",
        "Portfolio Growth":
            "Развој на портфолиото",
        "Portfolio value and recent performance":
            "Вредност на портфолиото и последни резултати",
        "Key takeaways":
            "Клучни заклучоци",
        "What these terms mean":
            "Значење на овие поими",
        "Advisory fee":
            "Провизија за советување",
        "Fund expenses":
            "Трошоци на фондовите",
        "Total":
            "Вкупно",
        "Portfolio value":
            "Вредност на портфолиото",
        "Portfolio return":
            "Принос на портфолиото",
        "Portfolio":
            "Портфолио",
        "Benchmark":
            "Бенчмарк",
        "Return":
            "Принос",
        "Risk level":
            "Ниво на ризик",
        "Target":
            "Цел",
        "Actual":
            "Реално",
        "Contribution":
            "Придонес",
        "Cumulative":
            "Кумулативно",
        "Period":
            "Период",
        "Difference":
            "Разлика",
        "Others":
            "Друго",
        "Asset class":
            "Класа на средства",
        "Weight":
            "Тежина",
        "Value":
            "Вредност",
        "Fees":
            "Провизии",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Референтна структура што се користи за оценување на резултатите. Надминувањето значи дека вашето портфолио оствари подобар резултат од пазарот при истото ниво на ризик.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Колку секој дел од портфолиото додал на вкупниот принос или одзел од него. Збирот на придонесите е еднаков на приносот што навистина го добивте.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Долгорочната структура договорена за вашиот ризичен профил. Позициите отстапуваат од неа со движењата на пазарите и се враќаат при ребалансирање.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Сите прикажани приноси се по одбивање на провизиите и го одразуваат тоа што навистина го заработивте.",
        "Valuations":
            "Проценки",
        "as at":
            "заклучно со",
        "Portfolio vs benchmark":
            "Портфолио во однос на бенчмаркот",
        "last column is drift from target":
            "последната колона го покажува отстапувањето од целта",
        "Strategic target":
            "Стратешка цел",
        "Net of fees":
            "По одбивање на провизии",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Минатите резултати не се показател за идни резултати. Податоците се по одбивање на провизии, освен ако не е поинаку наведено.",
        "Give me a quick summary of this report.":
            "Дај ми кратко резиме на овој извештај.",
        "Explain the fees I paid this period.":
            "Објасни ми ги провизиите што ги платив во овој период.",
        "How did I do against the benchmark?":
            "Како се претставив во однос на бенчмаркот?",
        "Allocation donut":
            "Прстенест дијаграм на распределбата",
        "Actual vs target":
            "Реално во однос на целта",
        "Return drivers":
            "Фактори на приносот",
        "Holdings treemap":
            "Карта на позициите",
        "You vs benchmark":
            "Вие и бенчмаркот",
        "Fee breakdown":
            "Структура на провизиите",
        "Money in and out":
            "Приливи и одливи",
        "Show me my asset allocation as a donut chart.":
            "Прикажи ја мојата распределба на средства како прстенест дијаграм.",
        "Show me my allocation against target as a bar chart.":
            "Прикажи ја мојата распределба во однос на целта како столбест дијаграм.",
        "Show me what drove my return as a waterfall chart.":
            "Прикажи што го поттикна мојот принос како каскаден дијаграм.",
        "Show me my largest holdings as a treemap.":
            "Прикажи ги моите најголеми позиции како дрвовидна карта.",
        "Plot my return over time as a line chart.":
            "Нацртај го мојот принос низ времето како линиски дијаграм.",
        "Chart my return against the benchmark as a bar chart.":
            "Нацртај го мојот принос во однос на бенчмаркот како столбест дијаграм.",
        "Show me what I paid as a donut chart.":
            "Прикажи што платив како прстенест дијаграм.",
        "Show me my cash flow in and out as a donut chart.":
            "Прикажи ги моите приливи и одливи како прстенест дијаграм.",
        "How your portfolio is invested":
            "Како е инвестирано вашето портфолио",
        "Where you sit against your target":
            "Каде сте во однос на вашата цел",
        "What drove your return":
            "Што го поттикна вашиот принос",
        "Your largest holdings":
            "Вашите најголеми позиции",
        "Your return over time":
            "Вашиот принос низ времето",
        "You against your benchmark":
            "Вие во однос на вашиот бенчмарк",
        "since":
            "од",
        "vs":
            "наспроти",
        "benchmark":
            "бенчмарк",
        "Quarterly Portfolio Review":
            "Квартален преглед на портфолиото",
        "Conservative":
            "Конзервативно",
        "Moderate":
            "Умерено",
        "Growth":
            "Раст",
        "Aggressive":
            "Агресивно",
    },

    # ── Serbian (Latin) ─────────────────────────────────────────
    "sr": {
        "US Equity":
            "Američke akcije",
        "Intl Equity":
            "Međunarodne akcije",
        "Fixed Income":
            "Obveznice",
        "Alternatives":
            "Alternativna ulaganja",
        "Real Assets":
            "Realna imovina",
        "Cash":
            "Gotovina",
        "Asset allocation":
            "Raspodela imovine",
        "Allocation detail":
            "Detalji raspodele",
        "Allocation vs strategic target":
            "Raspodela u odnosu na strateški cilj",
        "Fees and costs":
            "Naknade i troškovi",
        "What you paid":
            "Šta ste platili",
        "At a glance":
            "Ukratko",
        "Performance vs benchmark":
            "Rezultati u odnosu na benchmark",
        "Contribution to return":
            "Doprinos prinosu",
        "Return by period":
            "Prinos po periodima",
        "Return over time":
            "Prinos tokom vremena",
        "Return this period":
            "Prinos za period",
        "Ahead of benchmark":
            "Iznad benchmarka",
        "Risk":
            "Rizik",
        "Top contributors to return":
            "Glavni izvori prinosa",
        "Top detractors from return":
            "Glavni faktori smanjenja prinosa",
        "Behind benchmark":
            "Ispod benchmarka",
        "Portfolio Growth":
            "Kretanje portfolija",
        "Portfolio value and recent performance":
            "Vrednost portfolija i nedavni rezultati",
        "Key takeaways":
            "Ključni zaključci",
        "What these terms mean":
            "Značenje ovih pojmova",
        "Advisory fee":
            "Naknada za savetovanje",
        "Fund expenses":
            "Troškovi fondova",
        "Total":
            "Ukupno",
        "Portfolio value":
            "Vrednost portfolija",
        "Portfolio return":
            "Prinos portfolija",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Benchmark",
        "Return":
            "Prinos",
        "Risk level":
            "Nivo rizika",
        "Target":
            "Cilj",
        "Actual":
            "Stvarno",
        "Contribution":
            "Doprinos",
        "Cumulative":
            "Kumulativno",
        "Period":
            "Period",
        "Difference":
            "Razlika",
        "Others":
            "Ostalo",
        "Asset class":
            "Klasa imovine",
        "Weight":
            "Ponder",
        "Value":
            "Vrednost",
        "Fees":
            "Naknade",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referentna struktura koja se koristi za ocenu rezultata. Nadmašiti je znači da je vaš portfolio ostvario bolji rezultat od tržišta pri istom nivou rizika.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Koliko je svaki deo portfolija dodao ukupnom prinosu ili oduzeo od njega. Zbir doprinosa jednak je prinosu koji ste stvarno ostvarili.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dugoročna struktura dogovorena za vaš profil rizika. Pozicije odstupaju od nje kako se tržišta kreću i vraćaju se prilikom rebalansiranja.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Svi prikazani prinosi su nakon odbitka naknada i odražavaju ono što ste stvarno zaradili.",
        "Valuations":
            "Procene",
        "as at":
            "na dan",
        "Portfolio vs benchmark":
            "Portfolio u odnosu na benchmark",
        "last column is drift from target":
            "poslednja kolona prikazuje odstupanje od cilja",
        "Strategic target":
            "Strateški cilj",
        "Net of fees":
            "Nakon naknada",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Prošli rezultati nisu pokazatelj budućih rezultata. Podaci su nakon odbitka naknada, osim ako nije drugačije navedeno.",
        "Give me a quick summary of this report.":
            "Daj mi kratak rezime ovog izveštaja.",
        "Explain the fees I paid this period.":
            "Objasni naknade koje sam platio u ovom periodu.",
        "How did I do against the benchmark?":
            "Kakvi su moji rezultati u odnosu na benchmark?",
        "Allocation donut":
            "Prstenasti grafikon raspodele",
        "Actual vs target":
            "Stvarno u odnosu na cilj",
        "Return drivers":
            "Faktori prinosa",
        "Holdings treemap":
            "Mapa pozicija",
        "You vs benchmark":
            "Vi i benchmark",
        "Fee breakdown":
            "Struktura naknada",
        "Money in and out":
            "Uplate i isplate",
        "Show me my asset allocation as a donut chart.":
            "Prikaži moju raspodelu imovine kao prstenasti grafikon.",
        "Show me my allocation against target as a bar chart.":
            "Prikaži moju raspodelu u odnosu na cilj kao stubičasti grafikon.",
        "Show me what drove my return as a waterfall chart.":
            "Prikaži šta je pokrenulo moj prinos kao vodopadni grafikon.",
        "Show me my largest holdings as a treemap.":
            "Prikaži moje najveće pozicije kao mapu stabla.",
        "Plot my return over time as a line chart.":
            "Nacrtaj moj prinos tokom vremena kao linijski grafikon.",
        "Chart my return against the benchmark as a bar chart.":
            "Nacrtaj moj prinos u odnosu na benchmark kao stubičasti grafikon.",
        "Show me what I paid as a donut chart.":
            "Prikaži šta sam platio kao prstenasti grafikon.",
        "Show me my cash flow in and out as a donut chart.":
            "Prikaži moje uplate i isplate kao prstenasti grafikon.",
        "How your portfolio is invested":
            "Kako je uložen vaš portfolio",
        "Where you sit against your target":
            "Gde se nalazite u odnosu na svoj cilj",
        "What drove your return":
            "Šta je pokrenulo vaš prinos",
        "Your largest holdings":
            "Vaše najveće pozicije",
        "Your return over time":
            "Vaš prinos tokom vremena",
        "You against your benchmark":
            "Vi u odnosu na vaš benchmark",
        "since":
            "od",
        "vs":
            "naspram",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Kvartalni pregled portfolija",
        "Conservative":
            "Konzervativan",
        "Moderate":
            "Umeren",
        "Growth":
            "Rast",
        "Aggressive":
            "Agresivan",
    },

    # ── Croatian ────────────────────────────────────────────────
    "hr": {
        "US Equity":
            "Američke dionice",
        "Intl Equity":
            "Međunarodne dionice",
        "Fixed Income":
            "Obveznice",
        "Alternatives":
            "Alternativna ulaganja",
        "Real Assets":
            "Realna imovina",
        "Cash":
            "Novac",
        "Asset allocation":
            "Raspodjela imovine",
        "Allocation detail":
            "Detalji raspodjele",
        "Allocation vs strategic target":
            "Raspodjela u odnosu na strateški cilj",
        "Fees and costs":
            "Naknade i troškovi",
        "What you paid":
            "Što ste platili",
        "At a glance":
            "Ukratko",
        "Performance vs benchmark":
            "Rezultati u odnosu na benchmark",
        "Contribution to return":
            "Doprinos prinosu",
        "Return by period":
            "Prinos po razdobljima",
        "Return over time":
            "Prinos tijekom vremena",
        "Return this period":
            "Prinos za razdoblje",
        "Ahead of benchmark":
            "Iznad benchmarka",
        "Risk":
            "Rizik",
        "Top contributors to return":
            "Glavni izvori prinosa",
        "Top detractors from return":
            "Glavni čimbenici smanjenja prinosa",
        "Behind benchmark":
            "Ispod benchmarka",
        "Portfolio Growth":
            "Kretanje portfelja",
        "Portfolio value and recent performance":
            "Vrijednost portfelja i nedavni rezultati",
        "Key takeaways":
            "Ključni zaključci",
        "What these terms mean":
            "Značenje ovih pojmova",
        "Advisory fee":
            "Naknada za savjetovanje",
        "Fund expenses":
            "Troškovi fondova",
        "Total":
            "Ukupno",
        "Portfolio value":
            "Vrijednost portfelja",
        "Portfolio return":
            "Prinos portfelja",
        "Portfolio":
            "Portfelj",
        "Benchmark":
            "Benchmark",
        "Return":
            "Prinos",
        "Risk level":
            "Razina rizika",
        "Target":
            "Cilj",
        "Actual":
            "Stvarno",
        "Contribution":
            "Doprinos",
        "Cumulative":
            "Kumulativno",
        "Period":
            "Razdoblje",
        "Difference":
            "Razlika",
        "Others":
            "Ostalo",
        "Asset class":
            "Razred imovine",
        "Weight":
            "Ponder",
        "Value":
            "Vrijednost",
        "Fees":
            "Naknade",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referentna struktura koja se koristi za ocjenu rezultata. Nadmašiti je znači da je vaš portfelj ostvario bolji rezultat od tržišta uz istu razinu rizika.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Koliko je svaki dio portfelja pridonio ukupnom prinosu ili ga umanjio. Zbroj doprinosa jednak je prinosu koji ste stvarno ostvarili.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dugoročna struktura dogovorena za vaš profil rizika. Pozicije odstupaju od nje kako se tržišta kreću i vraćaju se pri rebalansiranju.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Svi prikazani prinosi su nakon odbitka naknada i odražavaju ono što ste stvarno zaradili.",
        "Valuations":
            "Procjene",
        "as at":
            "na dan",
        "Portfolio vs benchmark":
            "Portfelj u odnosu na benchmark",
        "last column is drift from target":
            "posljednji stupac prikazuje odstupanje od cilja",
        "Strategic target":
            "Strateški cilj",
        "Net of fees":
            "Nakon naknada",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Prošli rezultati nisu pokazatelj budućih rezultata. Podaci su nakon odbitka naknada, osim ako nije drugačije navedeno.",
        "Give me a quick summary of this report.":
            "Daj mi kratak sažetak ovog izvješća.",
        "Explain the fees I paid this period.":
            "Objasni naknade koje sam platio u ovom razdoblju.",
        "How did I do against the benchmark?":
            "Kakvi su moji rezultati u odnosu na benchmark?",
        "Allocation donut":
            "Prstenasti grafikon raspodjele",
        "Actual vs target":
            "Stvarno u odnosu na cilj",
        "Return drivers":
            "Čimbenici prinosa",
        "Holdings treemap":
            "Karta pozicija",
        "You vs benchmark":
            "Vi i benchmark",
        "Fee breakdown":
            "Struktura naknada",
        "Money in and out":
            "Uplate i isplate",
        "Show me my asset allocation as a donut chart.":
            "Prikaži moju raspodjelu imovine kao prstenasti grafikon.",
        "Show me my allocation against target as a bar chart.":
            "Prikaži moju raspodjelu u odnosu na cilj kao stupčasti grafikon.",
        "Show me what drove my return as a waterfall chart.":
            "Prikaži što je pokrenulo moj prinos kao vodopadni grafikon.",
        "Show me my largest holdings as a treemap.":
            "Prikaži moje najveće pozicije kao kartu stabla.",
        "Plot my return over time as a line chart.":
            "Nacrtaj moj prinos tijekom vremena kao linijski grafikon.",
        "Chart my return against the benchmark as a bar chart.":
            "Nacrtaj moj prinos u odnosu na benchmark kao stupčasti grafikon.",
        "Show me what I paid as a donut chart.":
            "Prikaži što sam platio kao prstenasti grafikon.",
        "Show me my cash flow in and out as a donut chart.":
            "Prikaži moje uplate i isplate kao prstenasti grafikon.",
        "How your portfolio is invested":
            "Kako je uložen vaš portfelj",
        "Where you sit against your target":
            "Gdje se nalazite u odnosu na svoj cilj",
        "What drove your return":
            "Što je pokrenulo vaš prinos",
        "Your largest holdings":
            "Vaše najveće pozicije",
        "Your return over time":
            "Vaš prinos tijekom vremena",
        "You against your benchmark":
            "Vi u odnosu na vaš benchmark",
        "since":
            "od",
        "vs":
            "naspram",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Tromjesečni pregled portfelja",
        "Conservative":
            "Konzervativan",
        "Moderate":
            "Umjeren",
        "Growth":
            "Rast",
        "Aggressive":
            "Agresivan",
    },

    # ── Bosnian ─────────────────────────────────────────────────
    "bs": {
        "US Equity":
            "Američke dionice",
        "Intl Equity":
            "Međunarodne dionice",
        "Fixed Income":
            "Obveznice",
        "Alternatives":
            "Alternativna ulaganja",
        "Real Assets":
            "Realna imovina",
        "Cash":
            "Gotovina",
        "Asset allocation":
            "Raspodjela imovine",
        "Allocation detail":
            "Detalji raspodjele",
        "Allocation vs strategic target":
            "Raspodjela u odnosu na strateški cilj",
        "Fees and costs":
            "Naknade i troškovi",
        "What you paid":
            "Šta ste platili",
        "At a glance":
            "Ukratko",
        "Performance vs benchmark":
            "Rezultati u odnosu na benchmark",
        "Contribution to return":
            "Doprinos prinosu",
        "Return by period":
            "Prinos po periodima",
        "Return over time":
            "Prinos tokom vremena",
        "Return this period":
            "Prinos za period",
        "Ahead of benchmark":
            "Iznad benchmarka",
        "Risk":
            "Rizik",
        "Top contributors to return":
            "Glavni izvori prinosa",
        "Top detractors from return":
            "Glavni faktori smanjenja prinosa",
        "Behind benchmark":
            "Ispod benchmarka",
        "Portfolio Growth":
            "Kretanje portfolija",
        "Portfolio value and recent performance":
            "Vrijednost portfolija i nedavni rezultati",
        "Key takeaways":
            "Ključni zaključci",
        "What these terms mean":
            "Značenje ovih pojmova",
        "Advisory fee":
            "Naknada za savjetovanje",
        "Fund expenses":
            "Troškovi fondova",
        "Total":
            "Ukupno",
        "Portfolio value":
            "Vrijednost portfolija",
        "Portfolio return":
            "Prinos portfolija",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Benchmark",
        "Return":
            "Prinos",
        "Risk level":
            "Nivo rizika",
        "Target":
            "Cilj",
        "Actual":
            "Stvarno",
        "Contribution":
            "Doprinos",
        "Cumulative":
            "Kumulativno",
        "Period":
            "Period",
        "Difference":
            "Razlika",
        "Others":
            "Ostalo",
        "Asset class":
            "Klasa imovine",
        "Weight":
            "Ponder",
        "Value":
            "Vrijednost",
        "Fees":
            "Naknade",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referentna struktura koja se koristi za ocjenu rezultata. Nadmašiti je znači da je vaš portfolio ostvario bolji rezultat od tržišta pri istom nivou rizika.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Koliko je svaki dio portfolija dodao ukupnom prinosu ili oduzeo od njega. Zbir doprinosa jednak je prinosu koji ste stvarno ostvarili.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dugoročna struktura dogovorena za vaš profil rizika. Pozicije odstupaju od nje kako se tržišta kreću i vraćaju se prilikom rebalansiranja.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Svi prikazani prinosi su nakon odbitka naknada i odražavaju ono što ste stvarno zaradili.",
        "Valuations":
            "Procjene",
        "as at":
            "na dan",
        "Portfolio vs benchmark":
            "Portfolio u odnosu na benchmark",
        "last column is drift from target":
            "posljednja kolona prikazuje odstupanje od cilja",
        "Strategic target":
            "Strateški cilj",
        "Net of fees":
            "Nakon naknada",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Prošli rezultati nisu pokazatelj budućih rezultata. Podaci su nakon odbitka naknada, osim ako nije drugačije navedeno.",
        "Give me a quick summary of this report.":
            "Daj mi kratak sažetak ovog izvještaja.",
        "Explain the fees I paid this period.":
            "Objasni naknade koje sam platio u ovom periodu.",
        "How did I do against the benchmark?":
            "Kakvi su moji rezultati u odnosu na benchmark?",
        "Allocation donut":
            "Prstenasti grafikon raspodjele",
        "Actual vs target":
            "Stvarno u odnosu na cilj",
        "Return drivers":
            "Faktori prinosa",
        "Holdings treemap":
            "Mapa pozicija",
        "You vs benchmark":
            "Vi i benchmark",
        "Fee breakdown":
            "Struktura naknada",
        "Money in and out":
            "Uplate i isplate",
        "Show me my asset allocation as a donut chart.":
            "Prikaži moju raspodjelu imovine kao prstenasti grafikon.",
        "Show me my allocation against target as a bar chart.":
            "Prikaži moju raspodjelu u odnosu na cilj kao stubičasti grafikon.",
        "Show me what drove my return as a waterfall chart.":
            "Prikaži šta je pokrenulo moj prinos kao vodopadni grafikon.",
        "Show me my largest holdings as a treemap.":
            "Prikaži moje najveće pozicije kao mapu stabla.",
        "Plot my return over time as a line chart.":
            "Nacrtaj moj prinos tokom vremena kao linijski grafikon.",
        "Chart my return against the benchmark as a bar chart.":
            "Nacrtaj moj prinos u odnosu na benchmark kao stubičasti grafikon.",
        "Show me what I paid as a donut chart.":
            "Prikaži šta sam platio kao prstenasti grafikon.",
        "Show me my cash flow in and out as a donut chart.":
            "Prikaži moje uplate i isplate kao prstenasti grafikon.",
        "How your portfolio is invested":
            "Kako je uložen vaš portfolio",
        "Where you sit against your target":
            "Gdje se nalazite u odnosu na svoj cilj",
        "What drove your return":
            "Šta je pokrenulo vaš prinos",
        "Your largest holdings":
            "Vaše najveće pozicije",
        "Your return over time":
            "Vaš prinos tokom vremena",
        "You against your benchmark":
            "Vi u odnosu na vaš benchmark",
        "since":
            "od",
        "vs":
            "naspram",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Kvartalni pregled portfolija",
        "Conservative":
            "Konzervativan",
        "Moderate":
            "Umjeren",
        "Growth":
            "Rast",
        "Aggressive":
            "Agresivan",
    },

    # ── Slovak ──────────────────────────────────────────────────
    "sk": {
        "US Equity":
            "Americké akcie",
        "Intl Equity":
            "Medzinárodné akcie",
        "Fixed Income":
            "Dlhopisy",
        "Alternatives":
            "Alternatívne investície",
        "Real Assets":
            "Reálne aktíva",
        "Cash":
            "Hotovosť",
        "Asset allocation":
            "Alokácia aktív",
        "Allocation detail":
            "Detail alokácie",
        "Allocation vs strategic target":
            "Alokácia voči strategickému cieľu",
        "Fees and costs":
            "Poplatky a náklady",
        "What you paid":
            "Čo ste zaplatili",
        "At a glance":
            "V skratke",
        "Performance vs benchmark":
            "Výkonnosť voči benchmarku",
        "Contribution to return":
            "Príspevok k výnosu",
        "Return by period":
            "Výnos podľa období",
        "Return over time":
            "Výnos v čase",
        "Return this period":
            "Výnos za toto obdobie",
        "Ahead of benchmark":
            "Nad benchmarkom",
        "Risk":
            "Riziko",
        "Top contributors to return":
            "Najväčší prispievatelia k výnosu",
        "Top detractors from return":
            "Najväčšie brzdy výnosu",
        "Behind benchmark":
            "Pod benchmarkom",
        "Portfolio Growth":
            "Vývoj portfólia",
        "Portfolio value and recent performance":
            "Hodnota portfólia a nedávna výkonnosť",
        "Key takeaways":
            "Kľúčové zistenia",
        "What these terms mean":
            "Čo tieto pojmy znamenajú",
        "Advisory fee":
            "Poplatok za poradenstvo",
        "Fund expenses":
            "Náklady fondov",
        "Total":
            "Spolu",
        "Portfolio value":
            "Hodnota portfólia",
        "Portfolio return":
            "Výnos portfólia",
        "Portfolio":
            "Portfólio",
        "Benchmark":
            "Benchmark",
        "Return":
            "Výnos",
        "Risk level":
            "Úroveň rizika",
        "Target":
            "Cieľ",
        "Actual":
            "Skutočnosť",
        "Contribution":
            "Príspevok",
        "Cumulative":
            "Kumulatívny",
        "Period":
            "Obdobie",
        "Difference":
            "Rozdiel",
        "Others":
            "Ostatné",
        "Asset class":
            "Trieda aktív",
        "Weight":
            "Váha",
        "Value":
            "Hodnota",
        "Fees":
            "Poplatky",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referenčné zloženie používané na hodnotenie výkonnosti. Prekonať ho znamená, že vaše portfólio dosiahlo lepší výsledok než trh pri rovnakej úrovni rizika.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Koľko každá časť portfólia pridala k celkovému výnosu alebo z neho ubrala. Príspevky sa sčítajú do výnosu, ktorý ste skutočne dostali.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dlhodobé zloženie dohodnuté pre váš rizikový profil. Pozície sa od neho s pohybom trhov odchyľujú a pri rebalansovaní sa vracajú späť.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Všetky uvedené výnosy sú po odpočítaní poplatkov, a teda odrážajú to, čo ste skutočne zarobili.",
        "Valuations":
            "Ocenenia",
        "as at":
            "k",
        "Portfolio vs benchmark":
            "Portfólio voči benchmarku",
        "last column is drift from target":
            "posledný stĺpec ukazuje odchýlku od cieľa",
        "Strategic target":
            "Strategický cieľ",
        "Net of fees":
            "Po poplatkoch",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Minulá výkonnosť nie je zárukou budúcich výsledkov. Údaje sú po poplatkoch, ak nie je uvedené inak.",
        "Give me a quick summary of this report.":
            "Daj mi stručné zhrnutie tejto správy.",
        "Explain the fees I paid this period.":
            "Vysvetli poplatky, ktoré som v tomto období zaplatil.",
        "How did I do against the benchmark?":
            "Ako som si viedol voči benchmarku?",
        "Allocation donut":
            "Koláčový graf alokácie",
        "Actual vs target":
            "Skutočnosť voči cieľu",
        "Return drivers":
            "Faktory výnosu",
        "Holdings treemap":
            "Stromová mapa pozícií",
        "You vs benchmark":
            "Vy voči benchmarku",
        "Fee breakdown":
            "Štruktúra poplatkov",
        "Money in and out":
            "Vklady a výbery",
        "Show me my asset allocation as a donut chart.":
            "Ukáž mi moju alokáciu aktív ako prstencový graf.",
        "Show me my allocation against target as a bar chart.":
            "Ukáž mi moju alokáciu voči cieľu ako stĺpcový graf.",
        "Show me what drove my return as a waterfall chart.":
            "Ukáž mi, čo poháňalo môj výnos, ako vodopádový graf.",
        "Show me my largest holdings as a treemap.":
            "Ukáž mi moje najväčšie pozície ako stromovú mapu.",
        "Plot my return over time as a line chart.":
            "Vykresli môj výnos v čase ako spojnicový graf.",
        "Chart my return against the benchmark as a bar chart.":
            "Vykresli môj výnos voči benchmarku ako stĺpcový graf.",
        "Show me what I paid as a donut chart.":
            "Ukáž mi, čo som zaplatil, ako prstencový graf.",
        "Show me my cash flow in and out as a donut chart.":
            "Ukáž mi moje vklady a výbery ako prstencový graf.",
        "How your portfolio is invested":
            "Ako je vaše portfólio investované",
        "Where you sit against your target":
            "Kde stojíte voči svojmu cieľu",
        "What drove your return":
            "Čo poháňalo váš výnos",
        "Your largest holdings":
            "Vaše najväčšie pozície",
        "Your return over time":
            "Váš výnos v čase",
        "You against your benchmark":
            "Vy voči svojmu benchmarku",
        "since":
            "od",
        "vs":
            "vs.",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Štvrťročný prehľad portfólia",
        "Conservative":
            "Konzervatívny",
        "Moderate":
            "Vyvážený",
        "Growth":
            "Rastový",
        "Aggressive":
            "Dynamický",
    },

    # ── Slovenian ───────────────────────────────────────────────
    "sl": {
        "US Equity":
            "Ameriške delnice",
        "Intl Equity":
            "Mednarodne delnice",
        "Fixed Income":
            "Obveznice",
        "Alternatives":
            "Alternativne naložbe",
        "Real Assets":
            "Realna sredstva",
        "Cash":
            "Denarna sredstva",
        "Asset allocation":
            "Razporeditev sredstev",
        "Allocation detail":
            "Podrobnosti razporeditve",
        "Allocation vs strategic target":
            "Razporeditev glede na strateški cilj",
        "Fees and costs":
            "Provizije in stroški",
        "What you paid":
            "Kaj ste plačali",
        "At a glance":
            "Na kratko",
        "Performance vs benchmark":
            "Uspešnost glede na benchmark",
        "Contribution to return":
            "Prispevek k donosu",
        "Return by period":
            "Donos po obdobjih",
        "Return over time":
            "Donos skozi čas",
        "Return this period":
            "Donos v tem obdobju",
        "Ahead of benchmark":
            "Nad benchmarkom",
        "Risk":
            "Tveganje",
        "Top contributors to return":
            "Največji prispevki k donosu",
        "Top detractors from return":
            "Največji zaviralci donosa",
        "Behind benchmark":
            "Pod benchmarkom",
        "Portfolio Growth":
            "Gibanje portfelja",
        "Portfolio value and recent performance":
            "Vrednost portfelja in nedavna uspešnost",
        "Key takeaways":
            "Ključne ugotovitve",
        "What these terms mean":
            "Kaj pomenijo ti izrazi",
        "Advisory fee":
            "Provizija za svetovanje",
        "Fund expenses":
            "Stroški skladov",
        "Total":
            "Skupaj",
        "Portfolio value":
            "Vrednost portfelja",
        "Portfolio return":
            "Donos portfelja",
        "Portfolio":
            "Portfelj",
        "Benchmark":
            "Benchmark",
        "Return":
            "Donos",
        "Risk level":
            "Raven tveganja",
        "Target":
            "Cilj",
        "Actual":
            "Dejansko",
        "Contribution":
            "Prispevek",
        "Cumulative":
            "Kumulativno",
        "Period":
            "Obdobje",
        "Difference":
            "Razlika",
        "Others":
            "Drugo",
        "Asset class":
            "Razred sredstev",
        "Weight":
            "Utež",
        "Value":
            "Vrednost",
        "Fees":
            "Provizije",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referenčna sestava, ki se uporablja za oceno uspešnosti. Preseči jo pomeni, da je vaš portfelj dosegel boljši rezultat od trga pri enaki ravni tveganja.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Koliko je vsak del portfelja dodal k skupnemu donosu ali ga zmanjšal. Vsota prispevkov je enaka donosu, ki ste ga dejansko prejeli.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Dolgoročna sestava, dogovorjena za vaš profil tveganja. Pozicije se od nje oddaljujejo z gibanjem trgov in se vrnejo ob ponovnem uravnoteženju.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Vsi prikazani donosi so po odbitku provizij in odražajo to, kar ste dejansko zaslužili.",
        "Valuations":
            "Vrednotenja",
        "as at":
            "na dan",
        "Portfolio vs benchmark":
            "Portfelj glede na benchmark",
        "last column is drift from target":
            "zadnji stolpec prikazuje odstopanje od cilja",
        "Strategic target":
            "Strateški cilj",
        "Net of fees":
            "Po odbitku provizij",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Pretekla uspešnost ni pokazatelj prihodnjih rezultatov. Podatki so po odbitku provizij, razen če ni navedeno drugače.",
        "Give me a quick summary of this report.":
            "Daj mi kratek povzetek tega poročila.",
        "Explain the fees I paid this period.":
            "Pojasni provizije, ki sem jih plačal v tem obdobju.",
        "How did I do against the benchmark?":
            "Kakšni so moji rezultati glede na benchmark?",
        "Allocation donut":
            "Prstanasti grafikon razporeditve",
        "Actual vs target":
            "Dejansko glede na cilj",
        "Return drivers":
            "Dejavniki donosa",
        "Holdings treemap":
            "Zemljevid pozicij",
        "You vs benchmark":
            "Vi in benchmark",
        "Fee breakdown":
            "Struktura provizij",
        "Money in and out":
            "Vplačila in izplačila",
        "Show me my asset allocation as a donut chart.":
            "Prikaži mojo razporeditev sredstev kot prstanasti grafikon.",
        "Show me my allocation against target as a bar chart.":
            "Prikaži mojo razporeditev glede na cilj kot stolpčni grafikon.",
        "Show me what drove my return as a waterfall chart.":
            "Prikaži, kaj je poganjalo moj donos, kot slapovni grafikon.",
        "Show me my largest holdings as a treemap.":
            "Prikaži moje največje pozicije kot drevesni zemljevid.",
        "Plot my return over time as a line chart.":
            "Nariši moj donos skozi čas kot črtni grafikon.",
        "Chart my return against the benchmark as a bar chart.":
            "Nariši moj donos glede na benchmark kot stolpčni grafikon.",
        "Show me what I paid as a donut chart.":
            "Prikaži, kaj sem plačal, kot prstanasti grafikon.",
        "Show me my cash flow in and out as a donut chart.":
            "Prikaži moja vplačila in izplačila kot prstanasti grafikon.",
        "How your portfolio is invested":
            "Kako je naložen vaš portfelj",
        "Where you sit against your target":
            "Kje ste glede na svoj cilj",
        "What drove your return":
            "Kaj je poganjalo vaš donos",
        "Your largest holdings":
            "Vaše največje pozicije",
        "Your return over time":
            "Vaš donos skozi čas",
        "You against your benchmark":
            "Vi glede na vaš benchmark",
        "since":
            "od",
        "vs":
            "proti",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Četrtletni pregled portfelja",
        "Conservative":
            "Konzervativen",
        "Moderate":
            "Zmeren",
        "Growth":
            "Rast",
        "Aggressive":
            "Agresiven",
    },

    # ── Romanian ────────────────────────────────────────────────
    "ro": {
        "US Equity":
            "Acțiuni americane",
        "Intl Equity":
            "Acțiuni internaționale",
        "Fixed Income":
            "Obligațiuni",
        "Alternatives":
            "Investiții alternative",
        "Real Assets":
            "Active reale",
        "Cash":
            "Numerar",
        "Asset allocation":
            "Alocarea activelor",
        "Allocation detail":
            "Detalii privind alocarea",
        "Allocation vs strategic target":
            "Alocare față de ținta strategică",
        "Fees and costs":
            "Comisioane și costuri",
        "What you paid":
            "Ce ați plătit",
        "At a glance":
            "Pe scurt",
        "Performance vs benchmark":
            "Performanța față de indicele de referință",
        "Contribution to return":
            "Contribuția la randament",
        "Return by period":
            "Randament pe perioade",
        "Return over time":
            "Randament în timp",
        "Return this period":
            "Randamentul acestei perioade",
        "Ahead of benchmark":
            "Peste indicele de referință",
        "Risk":
            "Risc",
        "Top contributors to return":
            "Principalele contribuții la randament",
        "Top detractors from return":
            "Principalii factori care au redus randamentul",
        "Behind benchmark":
            "Sub indicele de referință",
        "Portfolio Growth":
            "Evoluția portofoliului",
        "Portfolio value and recent performance":
            "Valoarea portofoliului și performanța recentă",
        "Key takeaways":
            "Concluzii principale",
        "What these terms mean":
            "Ce înseamnă acești termeni",
        "Advisory fee":
            "Comision de consultanță",
        "Fund expenses":
            "Cheltuielile fondurilor",
        "Total":
            "Total",
        "Portfolio value":
            "Valoarea portofoliului",
        "Portfolio return":
            "Randamentul portofoliului",
        "Portfolio":
            "Portofoliu",
        "Benchmark":
            "Indice de referință",
        "Return":
            "Randament",
        "Risk level":
            "Nivel de risc",
        "Target":
            "Țintă",
        "Actual":
            "Efectiv",
        "Contribution":
            "Contribuție",
        "Cumulative":
            "Cumulativ",
        "Period":
            "Perioadă",
        "Difference":
            "Diferență",
        "Others":
            "Altele",
        "Asset class":
            "Clasă de active",
        "Weight":
            "Pondere",
        "Value":
            "Valoare",
        "Fees":
            "Comisioane",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "O structură de referință folosită pentru evaluarea performanței. Depășirea ei înseamnă că portofoliul dumneavoastră a avut un rezultat mai bun decât piața la același nivel de risc.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Cât a adăugat sau a scăzut fiecare parte a portofoliului din randamentul total. Suma contribuțiilor este egală cu randamentul pe care l-ați primit efectiv.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Structura pe termen lung convenită pentru profilul dumneavoastră de risc. Pozițiile se îndepărtează de ea pe măsură ce piețele evoluează și sunt readuse la reechilibrare.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Toate randamentele prezentate sunt după deducerea comisioanelor și reflectă ceea ce ați câștigat efectiv.",
        "Valuations":
            "Evaluări",
        "as at":
            "la data de",
        "Portfolio vs benchmark":
            "Portofoliu față de indicele de referință",
        "last column is drift from target":
            "ultima coloană arată abaterea față de țintă",
        "Strategic target":
            "Țintă strategică",
        "Net of fees":
            "După comisioane",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Performanțele trecute nu constituie o garanție a rezultatelor viitoare. Cifrele sunt după deducerea comisioanelor, cu excepția cazurilor în care se precizează altfel.",
        "Give me a quick summary of this report.":
            "Dă-mi un rezumat scurt al acestui raport.",
        "Explain the fees I paid this period.":
            "Explică-mi comisioanele plătite în această perioadă.",
        "How did I do against the benchmark?":
            "Cum m-am descurcat față de indicele de referință?",
        "Allocation donut":
            "Diagramă inelară a alocării",
        "Actual vs target":
            "Efectiv față de țintă",
        "Return drivers":
            "Factorii randamentului",
        "Holdings treemap":
            "Hartă a pozițiilor",
        "You vs benchmark":
            "Dumneavoastră față de indicele de referință",
        "Fee breakdown":
            "Structura comisioanelor",
        "Money in and out":
            "Intrări și ieșiri",
        "Show me my asset allocation as a donut chart.":
            "Arată-mi alocarea activelor mele ca diagramă inelară.",
        "Show me my allocation against target as a bar chart.":
            "Arată-mi alocarea mea față de țintă ca diagramă cu bare.",
        "Show me what drove my return as a waterfall chart.":
            "Arată-mi ce a determinat randamentul meu ca diagramă cascadă.",
        "Show me my largest holdings as a treemap.":
            "Arată-mi cele mai mari poziții ale mele ca hartă arborescentă.",
        "Plot my return over time as a line chart.":
            "Trasează randamentul meu în timp ca diagramă cu linii.",
        "Chart my return against the benchmark as a bar chart.":
            "Trasează randamentul meu față de indicele de referință ca diagramă cu bare.",
        "Show me what I paid as a donut chart.":
            "Arată-mi ce am plătit ca diagramă inelară.",
        "Show me my cash flow in and out as a donut chart.":
            "Arată-mi intrările și ieșirile mele ca diagramă inelară.",
        "How your portfolio is invested":
            "Cum este investit portofoliul dumneavoastră",
        "Where you sit against your target":
            "Unde vă situați față de ținta dumneavoastră",
        "What drove your return":
            "Ce a determinat randamentul dumneavoastră",
        "Your largest holdings":
            "Cele mai mari poziții ale dumneavoastră",
        "Your return over time":
            "Randamentul dumneavoastră în timp",
        "You against your benchmark":
            "Dumneavoastră față de indicele dumneavoastră de referință",
        "since":
            "din",
        "vs":
            "față de",
        "benchmark":
            "indice de referință",
        "Quarterly Portfolio Review":
            "Analiza trimestrială a portofoliului",
        "Conservative":
            "Conservator",
        "Moderate":
            "Moderat",
        "Growth":
            "Creștere",
        "Aggressive":
            "Agresiv",
    },

    # ── Hungarian ───────────────────────────────────────────────
    "hu": {
        "US Equity":
            "Amerikai részvények",
        "Intl Equity":
            "Nemzetközi részvények",
        "Fixed Income":
            "Kötvények",
        "Alternatives":
            "Alternatív befektetések",
        "Real Assets":
            "Reáleszközök",
        "Cash":
            "Készpénz",
        "Asset allocation":
            "Eszközallokáció",
        "Allocation detail":
            "Az allokáció részletei",
        "Allocation vs strategic target":
            "Allokáció a stratégiai célhoz képest",
        "Fees and costs":
            "Díjak és költségek",
        "What you paid":
            "Amit fizetett",
        "At a glance":
            "Röviden",
        "Performance vs benchmark":
            "Teljesítmény a referenciaindexhez képest",
        "Contribution to return":
            "Hozzájárulás a hozamhoz",
        "Return by period":
            "Hozam időszakonként",
        "Return over time":
            "Hozam az idő során",
        "Return this period":
            "Ezen időszak hozama",
        "Ahead of benchmark":
            "A referenciaindex felett",
        "Risk":
            "Kockázat",
        "Top contributors to return":
            "A hozamhoz leginkább hozzájárulók",
        "Top detractors from return":
            "A hozamot leginkább csökkentők",
        "Behind benchmark":
            "A referenciaindex alatt",
        "Portfolio Growth":
            "A portfólió alakulása",
        "Portfolio value and recent performance":
            "Portfólióérték és a közelmúlt teljesítménye",
        "Key takeaways":
            "Legfontosabb megállapítások",
        "What these terms mean":
            "Mit jelentenek ezek a fogalmak",
        "Advisory fee":
            "Tanácsadási díj",
        "Fund expenses":
            "Alapköltségek",
        "Total":
            "Összesen",
        "Portfolio value":
            "Portfólióérték",
        "Portfolio return":
            "Portfólióhozam",
        "Portfolio":
            "Portfólió",
        "Benchmark":
            "Referenciaindex",
        "Return":
            "Hozam",
        "Risk level":
            "Kockázati szint",
        "Target":
            "Cél",
        "Actual":
            "Tényleges",
        "Contribution":
            "Hozzájárulás",
        "Cumulative":
            "Kumulált",
        "Period":
            "Időszak",
        "Difference":
            "Különbség",
        "Others":
            "Egyéb",
        "Asset class":
            "Eszközosztály",
        "Weight":
            "Súly",
        "Value":
            "Érték",
        "Fees":
            "Díjak",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Referencia-összetétel, amellyel a teljesítményt mérik. Túlszárnyalása azt jelenti, hogy portfóliója jobban teljesített, mint a piac azonos kockázati szinten.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Mennyivel járult hozzá a portfólió egyes része a teljes hozamhoz, vagy mennyivel csökkentette azt. A hozzájárulások összege adja a ténylegesen elért hozamot.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "A kockázati profiljához egyeztetett hosszú távú összetétel. A pozíciók a piacok mozgásával eltávolodnak tőle, és az újrasúlyozáskor térnek vissza.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Minden feltüntetett hozam a díjak levonása utáni, így azt tükrözi, amit ténylegesen keresett.",
        "Valuations":
            "Értékelések",
        "as at":
            "időpontja",
        "Portfolio vs benchmark":
            "Portfólió a referenciaindexhez képest",
        "last column is drift from target":
            "az utolsó oszlop a céltól való eltérést mutatja",
        "Strategic target":
            "Stratégiai cél",
        "Net of fees":
            "Díjak levonása után",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "A múltbeli teljesítmény nem jelzi előre a jövőbeli eredményeket. Az adatok a díjak levonása utániak, hacsak másként nem jelezzük.",
        "Give me a quick summary of this report.":
            "Adj rövid összefoglalót erről a jelentésről.",
        "Explain the fees I paid this period.":
            "Magyarázd el az ebben az időszakban fizetett díjakat.",
        "How did I do against the benchmark?":
            "Hogyan teljesítettem a referenciaindexhez képest?",
        "Allocation donut":
            "Allokációs gyűrűdiagram",
        "Actual vs target":
            "Tényleges a célhoz képest",
        "Return drivers":
            "A hozam mozgatórugói",
        "Holdings treemap":
            "Pozíciók fatérképe",
        "You vs benchmark":
            "Ön és a referenciaindex",
        "Fee breakdown":
            "Díjak megoszlása",
        "Money in and out":
            "Be- és kifizetések",
        "Show me my asset allocation as a donut chart.":
            "Mutasd az eszközallokációmat gyűrűdiagramként.",
        "Show me my allocation against target as a bar chart.":
            "Mutasd az allokációmat a célhoz képest oszlopdiagramként.",
        "Show me what drove my return as a waterfall chart.":
            "Mutasd meg vízesésdiagramként, mi mozgatta a hozamomat.",
        "Show me my largest holdings as a treemap.":
            "Mutasd a legnagyobb pozícióimat fatérképként.",
        "Plot my return over time as a line chart.":
            "Ábrázold a hozamomat az idő során vonaldiagramként.",
        "Chart my return against the benchmark as a bar chart.":
            "Ábrázold a hozamomat a referenciaindexhez képest oszlopdiagramként.",
        "Show me what I paid as a donut chart.":
            "Mutasd meg gyűrűdiagramként, mit fizettem.",
        "Show me my cash flow in and out as a donut chart.":
            "Mutasd a be- és kifizetéseimet gyűrűdiagramként.",
        "How your portfolio is invested":
            "Hogyan van befektetve a portfóliója",
        "Where you sit against your target":
            "Hol áll a céljához képest",
        "What drove your return":
            "Mi mozgatta a hozamát",
        "Your largest holdings":
            "Legnagyobb pozíciói",
        "Your return over time":
            "Hozama az idő során",
        "You against your benchmark":
            "Ön a referenciaindexéhez képest",
        "since":
            "óta",
        "vs":
            "vs.",
        "benchmark":
            "referenciaindex",
        "Quarterly Portfolio Review":
            "Negyedéves portfólió-áttekintés",
        "Conservative":
            "Konzervatív",
        "Moderate":
            "Mérsékelt",
        "Growth":
            "Növekedési",
        "Aggressive":
            "Agresszív",
    },

    # ── Estonian ────────────────────────────────────────────────
    "et": {
        "US Equity":
            "USA aktsiad",
        "Intl Equity":
            "Rahvusvahelised aktsiad",
        "Fixed Income":
            "Võlakirjad",
        "Alternatives":
            "Alternatiivsed investeeringud",
        "Real Assets":
            "Reaalvara",
        "Cash":
            "Raha",
        "Asset allocation":
            "Varade jaotus",
        "Allocation detail":
            "Jaotuse üksikasjad",
        "Allocation vs strategic target":
            "Jaotus võrreldes strateegilise eesmärgiga",
        "Fees and costs":
            "Tasud ja kulud",
        "What you paid":
            "Mida te maksite",
        "At a glance":
            "Lühidalt",
        "Performance vs benchmark":
            "Tootlus võrreldes võrdlusindeksiga",
        "Contribution to return":
            "Panus tootlusse",
        "Return by period":
            "Tootlus perioodide kaupa",
        "Return over time":
            "Tootlus ajas",
        "Return this period":
            "Selle perioodi tootlus",
        "Ahead of benchmark":
            "Üle võrdlusindeksi",
        "Risk":
            "Risk",
        "Top contributors to return":
            "Suurimad panustajad tootlusse",
        "Top detractors from return":
            "Suurimad tootlust vähendanud tegurid",
        "Behind benchmark":
            "Alla võrdlusindeksi",
        "Portfolio Growth":
            "Portfelli areng",
        "Portfolio value and recent performance":
            "Portfelli väärtus ja hiljutine tootlus",
        "Key takeaways":
            "Peamised järeldused",
        "What these terms mean":
            "Mida need mõisted tähendavad",
        "Advisory fee":
            "Nõustamistasu",
        "Fund expenses":
            "Fondide kulud",
        "Total":
            "Kokku",
        "Portfolio value":
            "Portfelli väärtus",
        "Portfolio return":
            "Portfelli tootlus",
        "Portfolio":
            "Portfell",
        "Benchmark":
            "Võrdlusindeks",
        "Return":
            "Tootlus",
        "Risk level":
            "Riskitase",
        "Target":
            "Eesmärk",
        "Actual":
            "Tegelik",
        "Contribution":
            "Panus",
        "Cumulative":
            "Kumulatiivne",
        "Period":
            "Periood",
        "Difference":
            "Vahe",
        "Others":
            "Muud",
        "Asset class":
            "Varaklass",
        "Weight":
            "Osakaal",
        "Value":
            "Väärtus",
        "Fees":
            "Tasud",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Võrdlusalus, mida kasutatakse tootluse hindamiseks. Selle ületamine tähendab, et teie portfell saavutas samal riskitasemel turust parema tulemuse.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kui palju iga portfelli osa lisas kogutootlusele või sellest vähendas. Panuste summa võrdub tootlusega, mille te tegelikult saite.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Teie riskiprofiili jaoks kokku lepitud pikaajaline jaotus. Positsioonid kalduvad sellest turgude liikudes kõrvale ja tuuakse tasakaalustamisel tagasi.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Kõik näidatud tootlused on pärast tasude mahaarvamist ja peegeldavad seega tegelikku teenistust.",
        "Valuations":
            "Hindamised",
        "as at":
            "seisuga",
        "Portfolio vs benchmark":
            "Portfell võrreldes võrdlusindeksiga",
        "last column is drift from target":
            "viimane veerg näitab kõrvalekallet eesmärgist",
        "Strategic target":
            "Strateegiline eesmärk",
        "Net of fees":
            "Pärast tasude mahaarvamist",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Varasem tootlus ei näita tulevasi tulemusi. Arvud on pärast tasude mahaarvamist, kui pole märgitud teisiti.",
        "Give me a quick summary of this report.":
            "Anna mulle sellest aruandest lühike kokkuvõte.",
        "Explain the fees I paid this period.":
            "Selgita tasusid, mida ma sel perioodil maksin.",
        "How did I do against the benchmark?":
            "Kuidas ma võrdlusindeksiga võrreldes hakkama sain?",
        "Allocation donut":
            "Jaotuse rõngasdiagramm",
        "Actual vs target":
            "Tegelik võrreldes eesmärgiga",
        "Return drivers":
            "Tootluse tegurid",
        "Holdings treemap":
            "Positsioonide puukaart",
        "You vs benchmark":
            "Teie ja võrdlusindeks",
        "Fee breakdown":
            "Tasude jaotus",
        "Money in and out":
            "Sisse- ja väljamaksed",
        "Show me my asset allocation as a donut chart.":
            "Näita mu varade jaotust rõngasdiagrammina.",
        "Show me my allocation against target as a bar chart.":
            "Näita mu jaotust võrreldes eesmärgiga tulpdiagrammina.",
        "Show me what drove my return as a waterfall chart.":
            "Näita koskediagrammina, mis mu tootlust mõjutas.",
        "Show me my largest holdings as a treemap.":
            "Näita mu suurimaid positsioone puukaardina.",
        "Plot my return over time as a line chart.":
            "Joonista mu tootlus ajas joondiagrammina.",
        "Chart my return against the benchmark as a bar chart.":
            "Joonista mu tootlus võrreldes võrdlusindeksiga tulpdiagrammina.",
        "Show me what I paid as a donut chart.":
            "Näita rõngasdiagrammina, mida ma maksin.",
        "Show me my cash flow in and out as a donut chart.":
            "Näita mu sisse- ja väljamakseid rõngasdiagrammina.",
        "How your portfolio is invested":
            "Kuidas teie portfell on investeeritud",
        "Where you sit against your target":
            "Kus te oma eesmärgi suhtes olete",
        "What drove your return":
            "Mis mõjutas teie tootlust",
        "Your largest holdings":
            "Teie suurimad positsioonid",
        "Your return over time":
            "Teie tootlus ajas",
        "You against your benchmark":
            "Teie võrreldes oma võrdlusindeksiga",
        "since":
            "alates",
        "vs":
            "vs.",
        "benchmark":
            "võrdlusindeks",
        "Quarterly Portfolio Review":
            "Kvartaalne portfelliülevaade",
        "Conservative":
            "Konservatiivne",
        "Moderate":
            "Mõõdukas",
        "Growth":
            "Kasv",
        "Aggressive":
            "Agressiivne",
    },

    # ── Latvian ─────────────────────────────────────────────────
    "lv": {
        "US Equity":
            "ASV akcijas",
        "Intl Equity":
            "Starptautiskās akcijas",
        "Fixed Income":
            "Obligācijas",
        "Alternatives":
            "Alternatīvie ieguldījumi",
        "Real Assets":
            "Reālie aktīvi",
        "Cash":
            "Nauda",
        "Asset allocation":
            "Aktīvu sadalījums",
        "Allocation detail":
            "Sadalījuma detaļas",
        "Allocation vs strategic target":
            "Sadalījums pret stratēģisko mērķi",
        "Fees and costs":
            "Maksas un izmaksas",
        "What you paid":
            "Ko jūs samaksājāt",
        "At a glance":
            "Īsumā",
        "Performance vs benchmark":
            "Rezultāti pret etalonu",
        "Contribution to return":
            "Ieguldījums ienesīgumā",
        "Return by period":
            "Ienesīgums pa periodiem",
        "Return over time":
            "Ienesīgums laika gaitā",
        "Return this period":
            "Šī perioda ienesīgums",
        "Ahead of benchmark":
            "Virs etalona",
        "Risk":
            "Risks",
        "Top contributors to return":
            "Lielākie ienesīguma veicinātāji",
        "Top detractors from return":
            "Lielākie ienesīgumu mazinošie faktori",
        "Behind benchmark":
            "Zem etalona",
        "Portfolio Growth":
            "Portfeļa attīstība",
        "Portfolio value and recent performance":
            "Portfeļa vērtība un nesenie rezultāti",
        "Key takeaways":
            "Galvenie secinājumi",
        "What these terms mean":
            "Ko nozīmē šie termini",
        "Advisory fee":
            "Konsultāciju maksa",
        "Fund expenses":
            "Fondu izmaksas",
        "Total":
            "Kopā",
        "Portfolio value":
            "Portfeļa vērtība",
        "Portfolio return":
            "Portfeļa ienesīgums",
        "Portfolio":
            "Portfelis",
        "Benchmark":
            "Etalons",
        "Return":
            "Ienesīgums",
        "Risk level":
            "Riska līmenis",
        "Target":
            "Mērķis",
        "Actual":
            "Faktiskais",
        "Contribution":
            "Ieguldījums",
        "Cumulative":
            "Kumulatīvais",
        "Period":
            "Periods",
        "Difference":
            "Starpība",
        "Others":
            "Citi",
        "Asset class":
            "Aktīvu klase",
        "Weight":
            "Svars",
        "Value":
            "Vērtība",
        "Fees":
            "Maksas",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Atsauces sastāvs, ko izmanto rezultātu novērtēšanai. Tā pārsniegšana nozīmē, ka jūsu portfelis sasniedza labāku rezultātu nekā tirgus tādā pašā riska līmenī.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Cik daudz katra portfeļa daļa pievienoja kopējam ienesīgumam vai no tā atņēma. Ieguldījumu summa ir vienāda ar ienesīgumu, ko jūs faktiski saņēmāt.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Ilgtermiņa sastāvs, kas saskaņots jūsu riska profilam. Pozīcijas no tā attālinās līdz ar tirgus kustībām un tiek atgrieztas atpakaļ, veicot līdzsvarošanu.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Visi norādītie ienesīgumi ir pēc maksu atskaitīšanas un tādējādi atspoguļo to, ko jūs faktiski nopelnījāt.",
        "Valuations":
            "Novērtējumi",
        "as at":
            "uz",
        "Portfolio vs benchmark":
            "Portfelis pret etalonu",
        "last column is drift from target":
            "pēdējā kolonna rāda novirzi no mērķa",
        "Strategic target":
            "Stratēģiskais mērķis",
        "Net of fees":
            "Pēc maksu atskaitīšanas",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Iepriekšējie rezultāti negarantē nākotnes rezultātus. Skaitļi ir pēc maksu atskaitīšanas, ja vien nav norādīts citādi.",
        "Give me a quick summary of this report.":
            "Sniedz man īsu šī pārskata kopsavilkumu.",
        "Explain the fees I paid this period.":
            "Paskaidro maksas, ko es samaksāju šajā periodā.",
        "How did I do against the benchmark?":
            "Kā man veicās salīdzinājumā ar etalonu?",
        "Allocation donut":
            "Sadalījuma gredzena diagramma",
        "Actual vs target":
            "Faktiskais pret mērķi",
        "Return drivers":
            "Ienesīguma faktori",
        "Holdings treemap":
            "Pozīciju koka karte",
        "You vs benchmark":
            "Jūs pret etalonu",
        "Fee breakdown":
            "Maksu sadalījums",
        "Money in and out":
            "Ieņēmumi un izmaksas",
        "Show me my asset allocation as a donut chart.":
            "Parādi manu aktīvu sadalījumu kā gredzena diagrammu.",
        "Show me my allocation against target as a bar chart.":
            "Parādi manu sadalījumu pret mērķi kā stabiņu diagrammu.",
        "Show me what drove my return as a waterfall chart.":
            "Parādi, kas veicināja manu ienesīgumu, kā ūdenskrituma diagrammu.",
        "Show me my largest holdings as a treemap.":
            "Parādi manas lielākās pozīcijas kā koka karti.",
        "Plot my return over time as a line chart.":
            "Attēlo manu ienesīgumu laika gaitā kā līniju diagrammu.",
        "Chart my return against the benchmark as a bar chart.":
            "Attēlo manu ienesīgumu pret etalonu kā stabiņu diagrammu.",
        "Show me what I paid as a donut chart.":
            "Parādi, ko es samaksāju, kā gredzena diagrammu.",
        "Show me my cash flow in and out as a donut chart.":
            "Parādi manus ieņēmumus un izmaksas kā gredzena diagrammu.",
        "How your portfolio is invested":
            "Kā ir ieguldīts jūsu portfelis",
        "Where you sit against your target":
            "Kur jūs atrodaties attiecībā pret savu mērķi",
        "What drove your return":
            "Kas veicināja jūsu ienesīgumu",
        "Your largest holdings":
            "Jūsu lielākās pozīcijas",
        "Your return over time":
            "Jūsu ienesīgums laika gaitā",
        "You against your benchmark":
            "Jūs pret savu etalonu",
        "since":
            "kopš",
        "vs":
            "pret",
        "benchmark":
            "etalons",
        "Quarterly Portfolio Review":
            "Ceturkšņa portfeļa pārskats",
        "Conservative":
            "Konservatīvs",
        "Moderate":
            "Mērens",
        "Growth":
            "Izaugsmes",
        "Aggressive":
            "Agresīvs",
    },

    # ── Lithuanian ──────────────────────────────────────────────
    "lt": {
        "US Equity":
            "JAV akcijos",
        "Intl Equity":
            "Tarptautinės akcijos",
        "Fixed Income":
            "Obligacijos",
        "Alternatives":
            "Alternatyvios investicijos",
        "Real Assets":
            "Realusis turtas",
        "Cash":
            "Grynieji pinigai",
        "Asset allocation":
            "Turto paskirstymas",
        "Allocation detail":
            "Paskirstymo detalės",
        "Allocation vs strategic target":
            "Paskirstymas palyginti su strateginiu tikslu",
        "Fees and costs":
            "Mokesčiai ir išlaidos",
        "What you paid":
            "Ką sumokėjote",
        "At a glance":
            "Trumpai",
        "Performance vs benchmark":
            "Rezultatai palyginti su lyginamuoju indeksu",
        "Contribution to return":
            "Indėlis į grąžą",
        "Return by period":
            "Grąža pagal laikotarpius",
        "Return over time":
            "Grąža laikui bėgant",
        "Return this period":
            "Šio laikotarpio grąža",
        "Ahead of benchmark":
            "Virš lyginamojo indekso",
        "Risk":
            "Rizika",
        "Top contributors to return":
            "Didžiausi grąžos veiksniai",
        "Top detractors from return":
            "Didžiausi grąžą mažinę veiksniai",
        "Behind benchmark":
            "Žemiau lyginamojo indekso",
        "Portfolio Growth":
            "Portfelio raida",
        "Portfolio value and recent performance":
            "Portfelio vertė ir naujausi rezultatai",
        "Key takeaways":
            "Pagrindinės išvados",
        "What these terms mean":
            "Ką reiškia šios sąvokos",
        "Advisory fee":
            "Konsultavimo mokestis",
        "Fund expenses":
            "Fondų išlaidos",
        "Total":
            "Iš viso",
        "Portfolio value":
            "Portfelio vertė",
        "Portfolio return":
            "Portfelio grąža",
        "Portfolio":
            "Portfelis",
        "Benchmark":
            "Lyginamasis indeksas",
        "Return":
            "Grąža",
        "Risk level":
            "Rizikos lygis",
        "Target":
            "Tikslas",
        "Actual":
            "Faktinis",
        "Contribution":
            "Indėlis",
        "Cumulative":
            "Kaupiamoji",
        "Period":
            "Laikotarpis",
        "Difference":
            "Skirtumas",
        "Others":
            "Kita",
        "Asset class":
            "Turto klasė",
        "Weight":
            "Svoris",
        "Value":
            "Vertė",
        "Fees":
            "Mokesčiai",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Etaloninė sudėtis, naudojama rezultatams vertinti. Ją viršyti reiškia, kad jūsų portfelis pasiekė geresnį rezultatą nei rinka esant tam pačiam rizikos lygiui.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kiek kiekviena portfelio dalis pridėjo prie bendros grąžos arba iš jos atėmė. Indėlių suma lygi grąžai, kurią iš tikrųjų gavote.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Ilgalaikė sudėtis, sutarta pagal jūsų rizikos profilį. Pozicijos nuo jos nutolsta rinkoms judant ir grąžinamos atliekant subalansavimą.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Visos pateiktos grąžos yra atskaičius mokesčius ir atspindi tai, ką iš tikrųjų uždirbote.",
        "Valuations":
            "Vertinimai",
        "as at":
            "data",
        "Portfolio vs benchmark":
            "Portfelis palyginti su lyginamuoju indeksu",
        "last column is drift from target":
            "paskutinis stulpelis rodo nuokrypį nuo tikslo",
        "Strategic target":
            "Strateginis tikslas",
        "Net of fees":
            "Atskaičius mokesčius",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Praeities rezultatai negarantuoja ateities rezultatų. Skaičiai pateikti atskaičius mokesčius, jei nenurodyta kitaip.",
        "Give me a quick summary of this report.":
            "Pateik man trumpą šios ataskaitos santrauką.",
        "Explain the fees I paid this period.":
            "Paaiškink mokesčius, kuriuos sumokėjau per šį laikotarpį.",
        "How did I do against the benchmark?":
            "Kokie mano rezultatai palyginti su lyginamuoju indeksu?",
        "Allocation donut":
            "Paskirstymo žiedinė diagrama",
        "Actual vs target":
            "Faktinis palyginti su tikslu",
        "Return drivers":
            "Grąžos veiksniai",
        "Holdings treemap":
            "Pozicijų medžio žemėlapis",
        "You vs benchmark":
            "Jūs ir lyginamasis indeksas",
        "Fee breakdown":
            "Mokesčių struktūra",
        "Money in and out":
            "Įplaukos ir išmokos",
        "Show me my asset allocation as a donut chart.":
            "Parodyk mano turto paskirstymą kaip žiedinę diagramą.",
        "Show me my allocation against target as a bar chart.":
            "Parodyk mano paskirstymą palyginti su tikslu kaip stulpelinę diagramą.",
        "Show me what drove my return as a waterfall chart.":
            "Parodyk, kas lėmė mano grąžą, kaip krioklio diagramą.",
        "Show me my largest holdings as a treemap.":
            "Parodyk mano didžiausias pozicijas kaip medžio žemėlapį.",
        "Plot my return over time as a line chart.":
            "Nubraižyk mano grąžą laikui bėgant kaip linijinę diagramą.",
        "Chart my return against the benchmark as a bar chart.":
            "Nubraižyk mano grąžą palyginti su lyginamuoju indeksu kaip stulpelinę diagramą.",
        "Show me what I paid as a donut chart.":
            "Parodyk, ką sumokėjau, kaip žiedinę diagramą.",
        "Show me my cash flow in and out as a donut chart.":
            "Parodyk mano įplaukas ir išmokas kaip žiedinę diagramą.",
        "How your portfolio is invested":
            "Kaip investuotas jūsų portfelis",
        "Where you sit against your target":
            "Kur esate savo tikslo atžvilgiu",
        "What drove your return":
            "Kas lėmė jūsų grąžą",
        "Your largest holdings":
            "Jūsų didžiausios pozicijos",
        "Your return over time":
            "Jūsų grąža laikui bėgant",
        "You against your benchmark":
            "Jūs palyginti su savo lyginamuoju indeksu",
        "since":
            "nuo",
        "vs":
            "palyginti su",
        "benchmark":
            "lyginamasis indeksas",
        "Quarterly Portfolio Review":
            "Ketvirtinė portfelio apžvalga",
        "Conservative":
            "Konservatyvus",
        "Moderate":
            "Vidutinis",
        "Growth":
            "Augimo",
        "Aggressive":
            "Agresyvus",
    },

    # ── Icelandic ───────────────────────────────────────────────
    "is": {
        "US Equity":
            "Bandarísk hlutabréf",
        "Intl Equity":
            "Alþjóðleg hlutabréf",
        "Fixed Income":
            "Skuldabréf",
        "Alternatives":
            "Óhefðbundnar fjárfestingar",
        "Real Assets":
            "Raunverulegar eignir",
        "Cash":
            "Reiðufé",
        "Asset allocation":
            "Eignaskipting",
        "Allocation detail":
            "Sundurliðun eignaskiptingar",
        "Allocation vs strategic target":
            "Eignaskipting miðað við stefnumarkmið",
        "Fees and costs":
            "Þóknanir og kostnaður",
        "What you paid":
            "Það sem þú greiddir",
        "At a glance":
            "Í hnotskurn",
        "Performance vs benchmark":
            "Ávöxtun miðað við viðmið",
        "Contribution to return":
            "Framlag til ávöxtunar",
        "Return by period":
            "Ávöxtun eftir tímabilum",
        "Return over time":
            "Ávöxtun yfir tíma",
        "Return this period":
            "Ávöxtun þessa tímabils",
        "Ahead of benchmark":
            "Yfir viðmiði",
        "Risk":
            "Áhætta",
        "Top contributors to return":
            "Mesta framlag til ávöxtunar",
        "Top detractors from return":
            "Mest dragandi þættir ávöxtunar",
        "Behind benchmark":
            "Undir viðmiði",
        "Portfolio Growth":
            "Þróun safns",
        "Portfolio value and recent performance":
            "Verðmæti safns og nýleg ávöxtun",
        "Key takeaways":
            "Helstu atriði",
        "What these terms mean":
            "Hvað þessi hugtök þýða",
        "Advisory fee":
            "Ráðgjafarþóknun",
        "Fund expenses":
            "Kostnaður sjóða",
        "Total":
            "Samtals",
        "Portfolio value":
            "Verðmæti safns",
        "Portfolio return":
            "Ávöxtun safns",
        "Portfolio":
            "Safn",
        "Benchmark":
            "Viðmið",
        "Return":
            "Ávöxtun",
        "Risk level":
            "Áhættustig",
        "Target":
            "Markmið",
        "Actual":
            "Raunverulegt",
        "Contribution":
            "Framlag",
        "Cumulative":
            "Uppsafnað",
        "Period":
            "Tímabil",
        "Difference":
            "Mismunur",
        "Others":
            "Annað",
        "Asset class":
            "Eignaflokkur",
        "Weight":
            "Vægi",
        "Value":
            "Verðmæti",
        "Fees":
            "Þóknanir",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Viðmiðunarsamsetning sem notuð er til að meta ávöxtun. Að fara fram úr henni þýðir að safnið þitt skilaði betri árangri en markaðurinn á sama áhættustigi.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Hversu miklu hver hluti safnsins bætti við heildarávöxtunina eða dró frá henni. Framlögin leggjast saman í þá ávöxtun sem þú fékkst í raun.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Langtímasamsetningin sem samið var um fyrir áhættusnið þitt. Eignir fjarlægjast hana þegar markaðir hreyfast og eru færðar til baka við endurjafnvægi.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Öll ávöxtun sem sýnd er er eftir að þóknanir hafa verið dregnar frá og endurspeglar því raunverulegan ávinning þinn.",
        "Valuations":
            "Verðmöt",
        "as at":
            "miðað við",
        "Portfolio vs benchmark":
            "Safn miðað við viðmið",
        "last column is drift from target":
            "síðasti dálkur sýnir frávik frá markmiði",
        "Strategic target":
            "Stefnumarkmið",
        "Net of fees":
            "Eftir þóknanir",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Fyrri ávöxtun er ekki vísbending um framtíðarárangur. Tölur eru eftir þóknanir nema annað sé tekið fram.",
        "Give me a quick summary of this report.":
            "Gefðu mér stutta samantekt á þessari skýrslu.",
        "Explain the fees I paid this period.":
            "Útskýrðu þóknanirnar sem ég greiddi á þessu tímabili.",
        "How did I do against the benchmark?":
            "Hvernig gekk mér miðað við viðmiðið?",
        "Allocation donut":
            "Hringrit eignaskiptingar",
        "Actual vs target":
            "Raunverulegt miðað við markmið",
        "Return drivers":
            "Drifkraftar ávöxtunar",
        "Holdings treemap":
            "Trjákort eigna",
        "You vs benchmark":
            "Þú miðað við viðmið",
        "Fee breakdown":
            "Sundurliðun þóknana",
        "Money in and out":
            "Inn- og útgreiðslur",
        "Show me my asset allocation as a donut chart.":
            "Sýndu eignaskiptingu mína sem hringrit.",
        "Show me my allocation against target as a bar chart.":
            "Sýndu eignaskiptingu mína miðað við markmið sem súlurit.",
        "Show me what drove my return as a waterfall chart.":
            "Sýndu hvað dreif ávöxtun mína sem fossarit.",
        "Show me my largest holdings as a treemap.":
            "Sýndu stærstu eignir mínar sem trjákort.",
        "Plot my return over time as a line chart.":
            "Teiknaðu ávöxtun mína yfir tíma sem línurit.",
        "Chart my return against the benchmark as a bar chart.":
            "Teiknaðu ávöxtun mína miðað við viðmiðið sem súlurit.",
        "Show me what I paid as a donut chart.":
            "Sýndu hvað ég greiddi sem hringrit.",
        "Show me my cash flow in and out as a donut chart.":
            "Sýndu inn- og útgreiðslur mínar sem hringrit.",
        "How your portfolio is invested":
            "Hvernig safnið þitt er fjárfest",
        "Where you sit against your target":
            "Hvar þú stendur miðað við markmið þitt",
        "What drove your return":
            "Hvað dreif ávöxtun þína",
        "Your largest holdings":
            "Stærstu eignir þínar",
        "Your return over time":
            "Ávöxtun þín yfir tíma",
        "You against your benchmark":
            "Þú miðað við viðmiðið þitt",
        "since":
            "frá",
        "vs":
            "á móti",
        "benchmark":
            "viðmið",
        "Quarterly Portfolio Review":
            "Ársfjórðungsleg yfirferð safns",
        "Conservative":
            "Varfærið",
        "Moderate":
            "Hóflegt",
        "Growth":
            "Vaxtar",
        "Aggressive":
            "Áhættusækið",
    },

    # ── Indonesian ──────────────────────────────────────────────
    "id": {
        "US Equity":
            "Saham AS",
        "Intl Equity":
            "Saham internasional",
        "Fixed Income":
            "Pendapatan tetap",
        "Alternatives":
            "Investasi alternatif",
        "Real Assets":
            "Aset riil",
        "Cash":
            "Kas",
        "Asset allocation":
            "Alokasi aset",
        "Allocation detail":
            "Rincian alokasi",
        "Allocation vs strategic target":
            "Alokasi terhadap target strategis",
        "Fees and costs":
            "Biaya dan ongkos",
        "What you paid":
            "Yang Anda bayarkan",
        "At a glance":
            "Sekilas",
        "Performance vs benchmark":
            "Kinerja terhadap tolok ukur",
        "Contribution to return":
            "Kontribusi terhadap imbal hasil",
        "Return by period":
            "Imbal hasil per periode",
        "Return over time":
            "Imbal hasil dari waktu ke waktu",
        "Return this period":
            "Imbal hasil periode ini",
        "Ahead of benchmark":
            "Di atas tolok ukur",
        "Risk":
            "Risiko",
        "Top contributors to return":
            "Kontributor utama imbal hasil",
        "Top detractors from return":
            "Penghambat utama imbal hasil",
        "Behind benchmark":
            "Di bawah tolok ukur",
        "Portfolio Growth":
            "Perkembangan portofolio",
        "Portfolio value and recent performance":
            "Nilai portofolio dan kinerja terkini",
        "Key takeaways":
            "Poin-poin utama",
        "What these terms mean":
            "Arti istilah-istilah ini",
        "Advisory fee":
            "Biaya penasihat",
        "Fund expenses":
            "Beban dana",
        "Total":
            "Total",
        "Portfolio value":
            "Nilai portofolio",
        "Portfolio return":
            "Imbal hasil portofolio",
        "Portfolio":
            "Portofolio",
        "Benchmark":
            "Tolok ukur",
        "Return":
            "Imbal hasil",
        "Risk level":
            "Tingkat risiko",
        "Target":
            "Target",
        "Actual":
            "Aktual",
        "Contribution":
            "Kontribusi",
        "Cumulative":
            "Kumulatif",
        "Period":
            "Periode",
        "Difference":
            "Selisih",
        "Others":
            "Lainnya",
        "Asset class":
            "Kelas aset",
        "Weight":
            "Bobot",
        "Value":
            "Nilai",
        "Fees":
            "Biaya",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Komposisi acuan yang digunakan untuk menilai kinerja. Melampauinya berarti portofolio Anda berkinerja lebih baik daripada pasar pada tingkat risiko yang sama.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Seberapa besar setiap bagian portofolio menambah atau mengurangi imbal hasil total. Jumlah kontribusi sama dengan imbal hasil yang benar-benar Anda terima.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Komposisi jangka panjang yang disepakati untuk profil risiko Anda. Posisi menjauh darinya seiring pergerakan pasar dan dikembalikan saat penyeimbangan ulang.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Semua imbal hasil yang ditampilkan sudah dikurangi biaya, sehingga mencerminkan apa yang benar-benar Anda peroleh.",
        "Valuations":
            "Penilaian",
        "as at":
            "per",
        "Portfolio vs benchmark":
            "Portofolio terhadap tolok ukur",
        "last column is drift from target":
            "kolom terakhir menunjukkan penyimpangan dari target",
        "Strategic target":
            "Target strategis",
        "Net of fees":
            "Setelah biaya",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Kinerja masa lalu bukan merupakan indikasi hasil di masa depan. Angka-angka sudah dikurangi biaya kecuali dinyatakan lain.",
        "Give me a quick summary of this report.":
            "Berikan ringkasan singkat laporan ini.",
        "Explain the fees I paid this period.":
            "Jelaskan biaya yang saya bayar pada periode ini.",
        "How did I do against the benchmark?":
            "Bagaimana kinerja saya terhadap tolok ukur?",
        "Allocation donut":
            "Diagram donat alokasi",
        "Actual vs target":
            "Aktual terhadap target",
        "Return drivers":
            "Pendorong imbal hasil",
        "Holdings treemap":
            "Peta kepemilikan",
        "You vs benchmark":
            "Anda terhadap tolok ukur",
        "Fee breakdown":
            "Rincian biaya",
        "Money in and out":
            "Dana masuk dan keluar",
        "Show me my asset allocation as a donut chart.":
            "Tampilkan alokasi aset saya sebagai diagram donat.",
        "Show me my allocation against target as a bar chart.":
            "Tampilkan alokasi saya terhadap target sebagai diagram batang.",
        "Show me what drove my return as a waterfall chart.":
            "Tampilkan apa yang mendorong imbal hasil saya sebagai diagram air terjun.",
        "Show me my largest holdings as a treemap.":
            "Tampilkan kepemilikan terbesar saya sebagai peta pohon.",
        "Plot my return over time as a line chart.":
            "Gambarkan imbal hasil saya dari waktu ke waktu sebagai diagram garis.",
        "Chart my return against the benchmark as a bar chart.":
            "Gambarkan imbal hasil saya terhadap tolok ukur sebagai diagram batang.",
        "Show me what I paid as a donut chart.":
            "Tampilkan apa yang saya bayar sebagai diagram donat.",
        "Show me my cash flow in and out as a donut chart.":
            "Tampilkan dana masuk dan keluar saya sebagai diagram donat.",
        "How your portfolio is invested":
            "Bagaimana portofolio Anda diinvestasikan",
        "Where you sit against your target":
            "Posisi Anda terhadap target Anda",
        "What drove your return":
            "Apa yang mendorong imbal hasil Anda",
        "Your largest holdings":
            "Kepemilikan terbesar Anda",
        "Your return over time":
            "Imbal hasil Anda dari waktu ke waktu",
        "You against your benchmark":
            "Anda terhadap tolok ukur Anda",
        "since":
            "sejak",
        "vs":
            "vs",
        "benchmark":
            "tolok ukur",
        "Quarterly Portfolio Review":
            "Tinjauan Portofolio Triwulanan",
        "Conservative":
            "Konservatif",
        "Moderate":
            "Moderat",
        "Growth":
            "Pertumbuhan",
        "Aggressive":
            "Agresif",
    },

    # ── Malay ───────────────────────────────────────────────────
    "ms": {
        "US Equity":
            "Saham AS",
        "Intl Equity":
            "Saham antarabangsa",
        "Fixed Income":
            "Pendapatan tetap",
        "Alternatives":
            "Pelaburan alternatif",
        "Real Assets":
            "Aset benar",
        "Cash":
            "Tunai",
        "Asset allocation":
            "Peruntukan aset",
        "Allocation detail":
            "Perincian peruntukan",
        "Allocation vs strategic target":
            "Peruntukan berbanding sasaran strategik",
        "Fees and costs":
            "Yuran dan kos",
        "What you paid":
            "Apa yang anda bayar",
        "At a glance":
            "Sepintas lalu",
        "Performance vs benchmark":
            "Prestasi berbanding penanda aras",
        "Contribution to return":
            "Sumbangan kepada pulangan",
        "Return by period":
            "Pulangan mengikut tempoh",
        "Return over time":
            "Pulangan sepanjang masa",
        "Return this period":
            "Pulangan tempoh ini",
        "Ahead of benchmark":
            "Mengatasi penanda aras",
        "Risk":
            "Risiko",
        "Top contributors to return":
            "Penyumbang utama pulangan",
        "Top detractors from return":
            "Penyusut utama pulangan",
        "Behind benchmark":
            "Di bawah penanda aras",
        "Portfolio Growth":
            "Perkembangan portfolio",
        "Portfolio value and recent performance":
            "Nilai portfolio dan prestasi terkini",
        "Key takeaways":
            "Perkara utama",
        "What these terms mean":
            "Maksud istilah-istilah ini",
        "Advisory fee":
            "Yuran nasihat",
        "Fund expenses":
            "Perbelanjaan dana",
        "Total":
            "Jumlah",
        "Portfolio value":
            "Nilai portfolio",
        "Portfolio return":
            "Pulangan portfolio",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Penanda aras",
        "Return":
            "Pulangan",
        "Risk level":
            "Tahap risiko",
        "Target":
            "Sasaran",
        "Actual":
            "Sebenar",
        "Contribution":
            "Sumbangan",
        "Cumulative":
            "Kumulatif",
        "Period":
            "Tempoh",
        "Difference":
            "Perbezaan",
        "Others":
            "Lain-lain",
        "Asset class":
            "Kelas aset",
        "Weight":
            "Wajaran",
        "Value":
            "Nilai",
        "Fees":
            "Yuran",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Komposisi rujukan yang digunakan untuk menilai prestasi. Mengatasinya bermakna portfolio anda berprestasi lebih baik daripada pasaran pada tahap risiko yang sama.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Berapa banyak setiap bahagian portfolio menambah atau mengurangkan jumlah pulangan. Jumlah sumbangan sama dengan pulangan yang benar-benar anda terima.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Komposisi jangka panjang yang dipersetujui untuk profil risiko anda. Kedudukan menjauh daripadanya apabila pasaran bergerak dan dikembalikan semasa pengimbangan semula.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Semua pulangan yang ditunjukkan adalah selepas ditolak yuran, jadi mencerminkan apa yang benar-benar anda perolehi.",
        "Valuations":
            "Penilaian",
        "as at":
            "pada",
        "Portfolio vs benchmark":
            "Portfolio berbanding penanda aras",
        "last column is drift from target":
            "lajur terakhir menunjukkan sisihan daripada sasaran",
        "Strategic target":
            "Sasaran strategik",
        "Net of fees":
            "Selepas yuran",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Prestasi lalu bukan petunjuk kepada keputusan masa hadapan. Angka adalah selepas ditolak yuran melainkan dinyatakan sebaliknya.",
        "Give me a quick summary of this report.":
            "Beri saya ringkasan pendek laporan ini.",
        "Explain the fees I paid this period.":
            "Terangkan yuran yang saya bayar pada tempoh ini.",
        "How did I do against the benchmark?":
            "Bagaimana prestasi saya berbanding penanda aras?",
        "Allocation donut":
            "Carta donat peruntukan",
        "Actual vs target":
            "Sebenar berbanding sasaran",
        "Return drivers":
            "Pemacu pulangan",
        "Holdings treemap":
            "Peta pegangan",
        "You vs benchmark":
            "Anda berbanding penanda aras",
        "Fee breakdown":
            "Perincian yuran",
        "Money in and out":
            "Wang masuk dan keluar",
        "Show me my asset allocation as a donut chart.":
            "Tunjukkan peruntukan aset saya sebagai carta donat.",
        "Show me my allocation against target as a bar chart.":
            "Tunjukkan peruntukan saya berbanding sasaran sebagai carta bar.",
        "Show me what drove my return as a waterfall chart.":
            "Tunjukkan apa yang memacu pulangan saya sebagai carta air terjun.",
        "Show me my largest holdings as a treemap.":
            "Tunjukkan pegangan terbesar saya sebagai peta pokok.",
        "Plot my return over time as a line chart.":
            "Lukiskan pulangan saya sepanjang masa sebagai carta garis.",
        "Chart my return against the benchmark as a bar chart.":
            "Lukiskan pulangan saya berbanding penanda aras sebagai carta bar.",
        "Show me what I paid as a donut chart.":
            "Tunjukkan apa yang saya bayar sebagai carta donat.",
        "Show me my cash flow in and out as a donut chart.":
            "Tunjukkan wang masuk dan keluar saya sebagai carta donat.",
        "How your portfolio is invested":
            "Bagaimana portfolio anda dilaburkan",
        "Where you sit against your target":
            "Kedudukan anda berbanding sasaran anda",
        "What drove your return":
            "Apa yang memacu pulangan anda",
        "Your largest holdings":
            "Pegangan terbesar anda",
        "Your return over time":
            "Pulangan anda sepanjang masa",
        "You against your benchmark":
            "Anda berbanding penanda aras anda",
        "since":
            "sejak",
        "vs":
            "lwn",
        "benchmark":
            "penanda aras",
        "Quarterly Portfolio Review":
            "Ulasan Portfolio Suku Tahunan",
        "Conservative":
            "Konservatif",
        "Moderate":
            "Sederhana",
        "Growth":
            "Pertumbuhan",
        "Aggressive":
            "Agresif",
    },

    # ── Vietnamese ──────────────────────────────────────────────
    "vi": {
        "US Equity":
            "Cổ phiếu Mỹ",
        "Intl Equity":
            "Cổ phiếu quốc tế",
        "Fixed Income":
            "Trái phiếu",
        "Alternatives":
            "Đầu tư thay thế",
        "Real Assets":
            "Tài sản thực",
        "Cash":
            "Tiền mặt",
        "Asset allocation":
            "Phân bổ tài sản",
        "Allocation detail":
            "Chi tiết phân bổ",
        "Allocation vs strategic target":
            "Phân bổ so với mục tiêu chiến lược",
        "Fees and costs":
            "Phí và chi phí",
        "What you paid":
            "Số tiền quý vị đã trả",
        "At a glance":
            "Tổng quan",
        "Performance vs benchmark":
            "Hiệu quả so với chỉ số tham chiếu",
        "Contribution to return":
            "Đóng góp vào lợi nhuận",
        "Return by period":
            "Lợi nhuận theo kỳ",
        "Return over time":
            "Lợi nhuận theo thời gian",
        "Return this period":
            "Lợi nhuận kỳ này",
        "Ahead of benchmark":
            "Vượt chỉ số tham chiếu",
        "Risk":
            "Rủi ro",
        "Top contributors to return":
            "Các yếu tố đóng góp chính vào lợi nhuận",
        "Top detractors from return":
            "Các yếu tố làm giảm lợi nhuận",
        "Behind benchmark":
            "Thấp hơn chỉ số tham chiếu",
        "Portfolio Growth":
            "Diễn biến danh mục",
        "Portfolio value and recent performance":
            "Giá trị danh mục và hiệu quả gần đây",
        "Key takeaways":
            "Những điểm chính",
        "What these terms mean":
            "Ý nghĩa của các thuật ngữ này",
        "Advisory fee":
            "Phí tư vấn",
        "Fund expenses":
            "Chi phí quỹ",
        "Total":
            "Tổng cộng",
        "Portfolio value":
            "Giá trị danh mục",
        "Portfolio return":
            "Lợi nhuận danh mục",
        "Portfolio":
            "Danh mục",
        "Benchmark":
            "Chỉ số tham chiếu",
        "Return":
            "Lợi nhuận",
        "Risk level":
            "Mức rủi ro",
        "Target":
            "Mục tiêu",
        "Actual":
            "Thực tế",
        "Contribution":
            "Đóng góp",
        "Cumulative":
            "Lũy kế",
        "Period":
            "Kỳ",
        "Difference":
            "Chênh lệch",
        "Others":
            "Khác",
        "Asset class":
            "Loại tài sản",
        "Weight":
            "Tỷ trọng",
        "Value":
            "Giá trị",
        "Fees":
            "Phí",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Một danh mục tham chiếu dùng để đánh giá hiệu quả. Vượt qua nó nghĩa là danh mục của quý vị đạt kết quả tốt hơn thị trường ở cùng mức rủi ro.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Mức độ mà mỗi phần của danh mục làm tăng hoặc giảm tổng lợi nhuận. Tổng các đóng góp bằng đúng lợi nhuận quý vị thực nhận.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Cơ cấu dài hạn đã thống nhất cho hồ sơ rủi ro của quý vị. Các vị thế lệch khỏi cơ cấu này khi thị trường biến động và được đưa về khi tái cân bằng.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Mọi lợi nhuận hiển thị đều đã trừ phí, do đó phản ánh đúng số tiền quý vị thực sự thu được.",
        "Valuations":
            "Định giá",
        "as at":
            "tại ngày",
        "Portfolio vs benchmark":
            "Danh mục so với chỉ số tham chiếu",
        "last column is drift from target":
            "cột cuối cùng cho biết mức lệch so với mục tiêu",
        "Strategic target":
            "Mục tiêu chiến lược",
        "Net of fees":
            "Sau khi trừ phí",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Hiệu quả trong quá khứ không phải là chỉ báo cho kết quả trong tương lai. Các số liệu đã trừ phí trừ khi có ghi chú khác.",
        "Give me a quick summary of this report.":
            "Cho tôi bản tóm tắt ngắn gọn báo cáo này.",
        "Explain the fees I paid this period.":
            "Giải thích các khoản phí tôi đã trả trong kỳ này.",
        "How did I do against the benchmark?":
            "Tôi đã đạt kết quả thế nào so với chỉ số tham chiếu?",
        "Allocation donut":
            "Biểu đồ vành khuyên phân bổ",
        "Actual vs target":
            "Thực tế so với mục tiêu",
        "Return drivers":
            "Các yếu tố tác động đến lợi nhuận",
        "Holdings treemap":
            "Bản đồ danh mục nắm giữ",
        "You vs benchmark":
            "Quý vị so với chỉ số tham chiếu",
        "Fee breakdown":
            "Chi tiết phí",
        "Money in and out":
            "Tiền vào và tiền ra",
        "Show me my asset allocation as a donut chart.":
            "Hiển thị phân bổ tài sản của tôi dưới dạng biểu đồ vành khuyên.",
        "Show me my allocation against target as a bar chart.":
            "Hiển thị phân bổ của tôi so với mục tiêu dưới dạng biểu đồ cột.",
        "Show me what drove my return as a waterfall chart.":
            "Hiển thị điều gì đã tác động đến lợi nhuận của tôi dưới dạng biểu đồ thác nước.",
        "Show me my largest holdings as a treemap.":
            "Hiển thị các khoản nắm giữ lớn nhất của tôi dưới dạng bản đồ cây.",
        "Plot my return over time as a line chart.":
            "Vẽ lợi nhuận của tôi theo thời gian dưới dạng biểu đồ đường.",
        "Chart my return against the benchmark as a bar chart.":
            "Vẽ lợi nhuận của tôi so với chỉ số tham chiếu dưới dạng biểu đồ cột.",
        "Show me what I paid as a donut chart.":
            "Hiển thị số tiền tôi đã trả dưới dạng biểu đồ vành khuyên.",
        "Show me my cash flow in and out as a donut chart.":
            "Hiển thị tiền vào và tiền ra của tôi dưới dạng biểu đồ vành khuyên.",
        "How your portfolio is invested":
            "Danh mục của quý vị được đầu tư như thế nào",
        "Where you sit against your target":
            "Vị trí của quý vị so với mục tiêu",
        "What drove your return":
            "Điều gì đã tác động đến lợi nhuận của quý vị",
        "Your largest holdings":
            "Các khoản nắm giữ lớn nhất của quý vị",
        "Your return over time":
            "Lợi nhuận của quý vị theo thời gian",
        "You against your benchmark":
            "Quý vị so với chỉ số tham chiếu của mình",
        "since":
            "từ",
        "vs":
            "so với",
        "benchmark":
            "chỉ số tham chiếu",
        "Quarterly Portfolio Review":
            "Báo cáo Danh mục Hàng quý",
        "Conservative":
            "Thận trọng",
        "Moderate":
            "Cân bằng",
        "Growth":
            "Tăng trưởng",
        "Aggressive":
            "Mạo hiểm",
    },

    # ── Filipino ────────────────────────────────────────────────
    "tl": {
        "US Equity":
            "Mga sapi sa US",
        "Intl Equity":
            "Mga sapi sa ibang bansa",
        "Fixed Income":
            "Mga bono",
        "Alternatives":
            "Mga alternatibong puhunan",
        "Real Assets":
            "Mga tunay na ari-arian",
        "Cash":
            "Salapi",
        "Asset allocation":
            "Alokasyon ng ari-arian",
        "Allocation detail":
            "Detalye ng alokasyon",
        "Allocation vs strategic target":
            "Alokasyon kumpara sa estratehikong tunguhin",
        "Fees and costs":
            "Mga bayarin at gastos",
        "What you paid":
            "Ang binayaran ninyo",
        "At a glance":
            "Sa isang sulyap",
        "Performance vs benchmark":
            "Pagganap kumpara sa benchmark",
        "Contribution to return":
            "Ambag sa kita",
        "Return by period":
            "Kita bawat panahon",
        "Return over time":
            "Kita sa paglipas ng panahon",
        "Return this period":
            "Kita sa panahong ito",
        "Ahead of benchmark":
            "Nangunguna sa benchmark",
        "Risk":
            "Panganib",
        "Top contributors to return":
            "Pangunahing nag-ambag sa kita",
        "Top detractors from return":
            "Pangunahing nagpababa ng kita",
        "Behind benchmark":
            "Nahuhuli sa benchmark",
        "Portfolio Growth":
            "Paglago ng portfolio",
        "Portfolio value and recent performance":
            "Halaga ng portfolio at kamakailang pagganap",
        "Key takeaways":
            "Mga pangunahing punto",
        "What these terms mean":
            "Ang ibig sabihin ng mga terminong ito",
        "Advisory fee":
            "Bayad sa pagpapayo",
        "Fund expenses":
            "Gastos ng pondo",
        "Total":
            "Kabuuan",
        "Portfolio value":
            "Halaga ng portfolio",
        "Portfolio return":
            "Kita ng portfolio",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Benchmark",
        "Return":
            "Kita",
        "Risk level":
            "Antas ng panganib",
        "Target":
            "Tunguhin",
        "Actual":
            "Aktwal",
        "Contribution":
            "Ambag",
        "Cumulative":
            "Kabuuang naipon",
        "Period":
            "Panahon",
        "Difference":
            "Pagkakaiba",
        "Others":
            "Iba pa",
        "Asset class":
            "Uri ng ari-arian",
        "Weight":
            "Timbang",
        "Value":
            "Halaga",
        "Fees":
            "Mga bayarin",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Isang sanggunian na kombinasyon na ginagamit upang sukatin ang pagganap. Ang paglampas dito ay nangangahulugang mas mahusay ang naging resulta ng inyong portfolio kaysa sa merkado sa parehong antas ng panganib.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kung magkano ang idinagdag o ibinawas ng bawat bahagi ng portfolio sa kabuuang kita. Ang kabuuan ng mga ambag ay katumbas ng kitang aktwal ninyong natanggap.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Ang pangmatagalang kombinasyon na napagkasunduan para sa inyong profile ng panganib. Lumalayo rito ang mga hawak habang gumagalaw ang merkado, at ibinabalik tuwing may rebalancing.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Lahat ng kitang ipinapakita ay matapos ibawas ang mga bayarin, kaya ipinapakita nito ang tunay ninyong kinita.",
        "Valuations":
            "Mga pagpapahalaga",
        "as at":
            "sa petsang",
        "Portfolio vs benchmark":
            "Portfolio kumpara sa benchmark",
        "last column is drift from target":
            "ang huling hanay ay ang lihis mula sa tunguhin",
        "Strategic target":
            "Estratehikong tunguhin",
        "Net of fees":
            "Matapos ang mga bayarin",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Ang nakaraang pagganap ay hindi katiyakan ng resulta sa hinaharap. Ang mga datos ay matapos ibawas ang mga bayarin maliban kung nakasaad ang iba.",
        "Give me a quick summary of this report.":
            "Bigyan mo ako ng maikling buod ng ulat na ito.",
        "Explain the fees I paid this period.":
            "Ipaliwanag ang mga bayaring binayaran ko sa panahong ito.",
        "How did I do against the benchmark?":
            "Kumusta ang naging resulta ko kumpara sa benchmark?",
        "Allocation donut":
            "Donut chart ng alokasyon",
        "Actual vs target":
            "Aktwal kumpara sa tunguhin",
        "Return drivers":
            "Mga nagtulak sa kita",
        "Holdings treemap":
            "Treemap ng mga hawak",
        "You vs benchmark":
            "Kayo kumpara sa benchmark",
        "Fee breakdown":
            "Detalye ng mga bayarin",
        "Money in and out":
            "Papasok at palabas na pera",
        "Show me my asset allocation as a donut chart.":
            "Ipakita ang alokasyon ng ari-arian ko bilang donut chart.",
        "Show me my allocation against target as a bar chart.":
            "Ipakita ang alokasyon ko kumpara sa tunguhin bilang bar chart.",
        "Show me what drove my return as a waterfall chart.":
            "Ipakita kung ano ang nagtulak sa kita ko bilang waterfall chart.",
        "Show me my largest holdings as a treemap.":
            "Ipakita ang pinakamalalaking hawak ko bilang treemap.",
        "Plot my return over time as a line chart.":
            "Iguhit ang kita ko sa paglipas ng panahon bilang line chart.",
        "Chart my return against the benchmark as a bar chart.":
            "Iguhit ang kita ko kumpara sa benchmark bilang bar chart.",
        "Show me what I paid as a donut chart.":
            "Ipakita kung magkano ang binayaran ko bilang donut chart.",
        "Show me my cash flow in and out as a donut chart.":
            "Ipakita ang papasok at palabas na pera ko bilang donut chart.",
        "How your portfolio is invested":
            "Kung paano nakapuhunan ang inyong portfolio",
        "Where you sit against your target":
            "Nasaan kayo kumpara sa inyong tunguhin",
        "What drove your return":
            "Ano ang nagtulak sa inyong kita",
        "Your largest holdings":
            "Ang inyong pinakamalalaking hawak",
        "Your return over time":
            "Ang inyong kita sa paglipas ng panahon",
        "You against your benchmark":
            "Kayo kumpara sa inyong benchmark",
        "since":
            "mula",
        "vs":
            "laban sa",
        "benchmark":
            "benchmark",
        "Quarterly Portfolio Review":
            "Quarterly na Pagsusuri ng Portfolio",
        "Conservative":
            "Maingat",
        "Moderate":
            "Katamtaman",
        "Growth":
            "Paglago",
        "Aggressive":
            "Agresibo",
    },

    # ── Thai ────────────────────────────────────────────────────
    "th": {
        "US Equity":
            "หุ้นสหรัฐฯ",
        "Intl Equity":
            "หุ้นต่างประเทศ",
        "Fixed Income":
            "ตราสารหนี้",
        "Alternatives":
            "การลงทุนทางเลือก",
        "Real Assets":
            "สินทรัพย์ที่มีตัวตน",
        "Cash":
            "เงินสด",
        "Asset allocation":
            "การจัดสรรสินทรัพย์",
        "Allocation detail":
            "รายละเอียดการจัดสรร",
        "Allocation vs strategic target":
            "การจัดสรรเทียบกับเป้าหมายเชิงกลยุทธ์",
        "Fees and costs":
            "ค่าธรรมเนียมและค่าใช้จ่าย",
        "What you paid":
            "สิ่งที่คุณจ่าย",
        "At a glance":
            "ภาพรวม",
        "Performance vs benchmark":
            "ผลตอบแทนเทียบกับดัชนีอ้างอิง",
        "Contribution to return":
            "การมีส่วนร่วมต่อผลตอบแทน",
        "Return by period":
            "ผลตอบแทนตามช่วงเวลา",
        "Return over time":
            "ผลตอบแทนตามกาลเวลา",
        "Return this period":
            "ผลตอบแทนงวดนี้",
        "Ahead of benchmark":
            "สูงกว่าดัชนีอ้างอิง",
        "Risk":
            "ความเสี่ยง",
        "Top contributors to return":
            "ปัจจัยหลักที่เพิ่มผลตอบแทน",
        "Top detractors from return":
            "ปัจจัยหลักที่ลดผลตอบแทน",
        "Behind benchmark":
            "ต่ำกว่าดัชนีอ้างอิง",
        "Portfolio Growth":
            "การเติบโตของพอร์ต",
        "Portfolio value and recent performance":
            "มูลค่าพอร์ตและผลตอบแทนล่าสุด",
        "Key takeaways":
            "ประเด็นสำคัญ",
        "What these terms mean":
            "ความหมายของคำเหล่านี้",
        "Advisory fee":
            "ค่าธรรมเนียมที่ปรึกษา",
        "Fund expenses":
            "ค่าใช้จ่ายกองทุน",
        "Total":
            "รวม",
        "Portfolio value":
            "มูลค่าพอร์ต",
        "Portfolio return":
            "ผลตอบแทนพอร์ต",
        "Portfolio":
            "พอร์ตการลงทุน",
        "Benchmark":
            "ดัชนีอ้างอิง",
        "Return":
            "ผลตอบแทน",
        "Risk level":
            "ระดับความเสี่ยง",
        "Target":
            "เป้าหมาย",
        "Actual":
            "ตามจริง",
        "Contribution":
            "การมีส่วนร่วม",
        "Cumulative":
            "สะสม",
        "Period":
            "งวด",
        "Difference":
            "ผลต่าง",
        "Others":
            "อื่น ๆ",
        "Asset class":
            "ประเภทสินทรัพย์",
        "Weight":
            "น้ำหนัก",
        "Value":
            "มูลค่า",
        "Fees":
            "ค่าธรรมเนียม",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "สัดส่วนอ้างอิงที่ใช้ประเมินผลตอบแทน การทำได้สูงกว่าหมายความว่าพอร์ตของคุณให้ผลดีกว่าตลาดที่ระดับความเสี่ยงเดียวกัน",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "แต่ละส่วนของพอร์ตเพิ่มหรือลดผลตอบแทนรวมมากเพียงใด ผลรวมของการมีส่วนร่วมเท่ากับผลตอบแทนที่คุณได้รับจริง",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "สัดส่วนระยะยาวที่ตกลงไว้ตามระดับความเสี่ยงของคุณ สัดส่วนการถือครองจะเบี่ยงเบนไปเมื่อตลาดเคลื่อนไหว และจะถูกปรับกลับเมื่อมีการปรับสมดุล",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "ผลตอบแทนทั้งหมดที่แสดงเป็นตัวเลขหลังหักค่าธรรมเนียมแล้ว จึงสะท้อนสิ่งที่คุณได้รับจริง",
        "Valuations":
            "การประเมินมูลค่า",
        "as at":
            "ณ วันที่",
        "Portfolio vs benchmark":
            "พอร์ตเทียบกับดัชนีอ้างอิง",
        "last column is drift from target":
            "คอลัมน์สุดท้ายแสดงส่วนต่างจากเป้าหมาย",
        "Strategic target":
            "เป้าหมายเชิงกลยุทธ์",
        "Net of fees":
            "หลังหักค่าธรรมเนียม",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "ผลการดำเนินงานในอดีตไม่ได้เป็นเครื่องบ่งชี้ผลในอนาคต ตัวเลขเป็นยอดหลังหักค่าธรรมเนียม เว้นแต่ระบุไว้เป็นอย่างอื่น",
        "Give me a quick summary of this report.":
            "ขอสรุปรายงานฉบับนี้แบบสั้น ๆ",
        "Explain the fees I paid this period.":
            "อธิบายค่าธรรมเนียมที่ฉันจ่ายในงวดนี้",
        "How did I do against the benchmark?":
            "ผลตอบแทนของฉันเทียบกับดัชนีอ้างอิงเป็นอย่างไร",
        "Allocation donut":
            "แผนภูมิโดนัทการจัดสรร",
        "Actual vs target":
            "ตามจริงเทียบกับเป้าหมาย",
        "Return drivers":
            "ปัจจัยขับเคลื่อนผลตอบแทน",
        "Holdings treemap":
            "แผนภูมิต้นไม้การถือครอง",
        "You vs benchmark":
            "คุณเทียบกับดัชนีอ้างอิง",
        "Fee breakdown":
            "รายละเอียดค่าธรรมเนียม",
        "Money in and out":
            "เงินเข้าและเงินออก",
        "Show me my asset allocation as a donut chart.":
            "แสดงการจัดสรรสินทรัพย์ของฉันเป็นแผนภูมิโดนัท",
        "Show me my allocation against target as a bar chart.":
            "แสดงการจัดสรรของฉันเทียบกับเป้าหมายเป็นแผนภูมิแท่ง",
        "Show me what drove my return as a waterfall chart.":
            "แสดงปัจจัยที่ขับเคลื่อนผลตอบแทนของฉันเป็นแผนภูมิน้ำตก",
        "Show me my largest holdings as a treemap.":
            "แสดงการถือครองที่ใหญ่ที่สุดของฉันเป็นแผนภูมิต้นไม้",
        "Plot my return over time as a line chart.":
            "วาดผลตอบแทนของฉันตามกาลเวลาเป็นแผนภูมิเส้น",
        "Chart my return against the benchmark as a bar chart.":
            "วาดผลตอบแทนของฉันเทียบกับดัชนีอ้างอิงเป็นแผนภูมิแท่ง",
        "Show me what I paid as a donut chart.":
            "แสดงสิ่งที่ฉันจ่ายเป็นแผนภูมิโดนัท",
        "Show me my cash flow in and out as a donut chart.":
            "แสดงเงินเข้าและเงินออกของฉันเป็นแผนภูมิโดนัท",
        "How your portfolio is invested":
            "พอร์ตของคุณลงทุนอย่างไร",
        "Where you sit against your target":
            "คุณอยู่ตรงไหนเทียบกับเป้าหมาย",
        "What drove your return":
            "อะไรขับเคลื่อนผลตอบแทนของคุณ",
        "Your largest holdings":
            "การถือครองที่ใหญ่ที่สุดของคุณ",
        "Your return over time":
            "ผลตอบแทนของคุณตามกาลเวลา",
        "You against your benchmark":
            "คุณเทียบกับดัชนีอ้างอิงของคุณ",
        "since":
            "ตั้งแต่",
        "vs":
            "เทียบกับ",
        "benchmark":
            "ดัชนีอ้างอิง",
        "Quarterly Portfolio Review":
            "รายงานพอร์ตรายไตรมาส",
        "Conservative":
            "ระมัดระวัง",
        "Moderate":
            "ปานกลาง",
        "Growth":
            "เติบโต",
        "Aggressive":
            "เชิงรุก",
    },

    # ── Persian ─────────────────────────────────────────────────
    "fa": {
        "US Equity":
            "سهام آمریکا",
        "Intl Equity":
            "سهام بین‌المللی",
        "Fixed Income":
            "اوراق با درآمد ثابت",
        "Alternatives":
            "سرمایه‌گذاری‌های جایگزین",
        "Real Assets":
            "دارایی‌های واقعی",
        "Cash":
            "وجه نقد",
        "Asset allocation":
            "تخصیص دارایی",
        "Allocation detail":
            "جزئیات تخصیص",
        "Allocation vs strategic target":
            "تخصیص در برابر هدف راهبردی",
        "Fees and costs":
            "کارمزدها و هزینه‌ها",
        "What you paid":
            "آنچه پرداخت کردید",
        "At a glance":
            "در یک نگاه",
        "Performance vs benchmark":
            "عملکرد در برابر شاخص مرجع",
        "Contribution to return":
            "سهم در بازده",
        "Return by period":
            "بازده بر حسب دوره",
        "Return over time":
            "بازده در طول زمان",
        "Return this period":
            "بازده این دوره",
        "Ahead of benchmark":
            "بالاتر از شاخص مرجع",
        "Risk":
            "ریسک",
        "Top contributors to return":
            "بیشترین سهم در بازده",
        "Top detractors from return":
            "بیشترین کاهش‌دهنده بازده",
        "Behind benchmark":
            "پایین‌تر از شاخص مرجع",
        "Portfolio Growth":
            "رشد سبد",
        "Portfolio value and recent performance":
            "ارزش سبد و عملکرد اخیر",
        "Key takeaways":
            "نکات کلیدی",
        "What these terms mean":
            "معنای این اصطلاحات",
        "Advisory fee":
            "کارمزد مشاوره",
        "Fund expenses":
            "هزینه‌های صندوق",
        "Total":
            "مجموع",
        "Portfolio value":
            "ارزش سبد",
        "Portfolio return":
            "بازده سبد",
        "Portfolio":
            "سبد",
        "Benchmark":
            "شاخص مرجع",
        "Return":
            "بازده",
        "Risk level":
            "سطح ریسک",
        "Target":
            "هدف",
        "Actual":
            "واقعی",
        "Contribution":
            "سهم",
        "Cumulative":
            "تجمعی",
        "Period":
            "دوره",
        "Difference":
            "تفاوت",
        "Others":
            "سایر",
        "Asset class":
            "طبقه دارایی",
        "Weight":
            "وزن",
        "Value":
            "ارزش",
        "Fees":
            "کارمزدها",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "ترکیبی مرجع که برای سنجش عملکرد به کار می‌رود. پیشی گرفتن از آن یعنی سبد شما در همان سطح ریسک عملکرد بهتری از بازار داشته است.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "اینکه هر بخش از سبد چقدر به بازده کل افزوده یا از آن کاسته است. مجموع سهم‌ها برابر با بازدهی است که واقعاً دریافت کرده‌اید.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "ترکیب بلندمدتی که برای پروفایل ریسک شما توافق شده است. با حرکت بازارها موقعیت‌ها از آن فاصله می‌گیرند و در زمان متعادل‌سازی بازگردانده می‌شوند.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "همه بازده‌های نشان‌داده‌شده پس از کسر کارمزدها هستند و بنابراین آنچه را واقعاً به دست آورده‌اید نشان می‌دهند.",
        "Valuations":
            "ارزش‌گذاری‌ها",
        "as at":
            "در تاریخ",
        "Portfolio vs benchmark":
            "سبد در برابر شاخص مرجع",
        "last column is drift from target":
            "ستون آخر انحراف از هدف را نشان می‌دهد",
        "Strategic target":
            "هدف راهبردی",
        "Net of fees":
            "پس از کسر کارمزد",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "عملکرد گذشته نشان‌دهنده نتایج آینده نیست. ارقام پس از کسر کارمزدها هستند مگر آنکه خلاف آن ذکر شود.",
        "Give me a quick summary of this report.":
            "یک خلاصه کوتاه از این گزارش به من بده.",
        "Explain the fees I paid this period.":
            "کارمزدهایی را که در این دوره پرداختم توضیح بده.",
        "How did I do against the benchmark?":
            "عملکرد من در برابر شاخص مرجع چگونه بود؟",
        "Allocation donut":
            "نمودار دایره‌ای تخصیص",
        "Actual vs target":
            "واقعی در برابر هدف",
        "Return drivers":
            "محرک‌های بازده",
        "Holdings treemap":
            "نقشه دارایی‌ها",
        "You vs benchmark":
            "شما در برابر شاخص مرجع",
        "Fee breakdown":
            "تفکیک کارمزدها",
        "Money in and out":
            "ورود و خروج وجه",
        "Show me my asset allocation as a donut chart.":
            "تخصیص دارایی من را به صورت نمودار دایره‌ای نشان بده.",
        "Show me my allocation against target as a bar chart.":
            "تخصیص من در برابر هدف را به صورت نمودار میله‌ای نشان بده.",
        "Show me what drove my return as a waterfall chart.":
            "آنچه بازده من را رقم زد به صورت نمودار آبشاری نشان بده.",
        "Show me my largest holdings as a treemap.":
            "بزرگ‌ترین دارایی‌های من را به صورت نقشه درختی نشان بده.",
        "Plot my return over time as a line chart.":
            "بازده من در طول زمان را به صورت نمودار خطی رسم کن.",
        "Chart my return against the benchmark as a bar chart.":
            "بازده من در برابر شاخص مرجع را به صورت نمودار میله‌ای رسم کن.",
        "Show me what I paid as a donut chart.":
            "آنچه پرداخت کرده‌ام را به صورت نمودار دایره‌ای نشان بده.",
        "Show me my cash flow in and out as a donut chart.":
            "ورود و خروج وجه من را به صورت نمودار دایره‌ای نشان بده.",
        "How your portfolio is invested":
            "سبد شما چگونه سرمایه‌گذاری شده است",
        "Where you sit against your target":
            "جایگاه شما در برابر هدفتان",
        "What drove your return":
            "چه چیزی بازده شما را رقم زد",
        "Your largest holdings":
            "بزرگ‌ترین دارایی‌های شما",
        "Your return over time":
            "بازده شما در طول زمان",
        "You against your benchmark":
            "شما در برابر شاخص مرجع خود",
        "since":
            "از",
        "vs":
            "در برابر",
        "benchmark":
            "شاخص مرجع",
        "Quarterly Portfolio Review":
            "بررسی فصلی سبد",
        "Conservative":
            "محافظه‌کارانه",
        "Moderate":
            "متعادل",
        "Growth":
            "رشدی",
        "Aggressive":
            "تهاجمی",
    },

    # ── Urdu ────────────────────────────────────────────────────
    "ur": {
        "US Equity":
            "امریکی حصص",
        "Intl Equity":
            "بین الاقوامی حصص",
        "Fixed Income":
            "مقررہ آمدنی",
        "Alternatives":
            "متبادل سرمایہ کاری",
        "Real Assets":
            "حقیقی اثاثے",
        "Cash":
            "نقد",
        "Asset allocation":
            "اثاثوں کی تقسیم",
        "Allocation detail":
            "تقسیم کی تفصیل",
        "Allocation vs strategic target":
            "حکمت عملی کے ہدف کے مقابلے میں تقسیم",
        "Fees and costs":
            "فیسیں اور اخراجات",
        "What you paid":
            "آپ نے کیا ادا کیا",
        "At a glance":
            "ایک نظر میں",
        "Performance vs benchmark":
            "بینچ مارک کے مقابلے میں کارکردگی",
        "Contribution to return":
            "منافع میں حصہ",
        "Return by period":
            "مدت کے لحاظ سے منافع",
        "Return over time":
            "وقت کے ساتھ منافع",
        "Return this period":
            "اس مدت کا منافع",
        "Ahead of benchmark":
            "بینچ مارک سے آگے",
        "Risk":
            "خطرہ",
        "Top contributors to return":
            "منافع میں سب سے زیادہ حصہ ڈالنے والے",
        "Top detractors from return":
            "منافع کو سب سے زیادہ کم کرنے والے",
        "Behind benchmark":
            "بینچ مارک سے پیچھے",
        "Portfolio Growth":
            "پورٹ فولیو کی نمو",
        "Portfolio value and recent performance":
            "پورٹ فولیو کی مالیت اور حالیہ کارکردگی",
        "Key takeaways":
            "اہم نکات",
        "What these terms mean":
            "ان اصطلاحات کا مطلب",
        "Advisory fee":
            "مشاورتی فیس",
        "Fund expenses":
            "فنڈ کے اخراجات",
        "Total":
            "کل",
        "Portfolio value":
            "پورٹ فولیو کی مالیت",
        "Portfolio return":
            "پورٹ فولیو کا منافع",
        "Portfolio":
            "پورٹ فولیو",
        "Benchmark":
            "بینچ مارک",
        "Return":
            "منافع",
        "Risk level":
            "خطرے کی سطح",
        "Target":
            "ہدف",
        "Actual":
            "حقیقی",
        "Contribution":
            "حصہ",
        "Cumulative":
            "مجموعی",
        "Period":
            "مدت",
        "Difference":
            "فرق",
        "Others":
            "دیگر",
        "Asset class":
            "اثاثہ جماعت",
        "Weight":
            "وزن",
        "Value":
            "مالیت",
        "Fees":
            "فیسیں",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "کارکردگی جانچنے کے لیے استعمال ہونے والا ایک حوالہ مرکب۔ اس سے آگے نکلنے کا مطلب ہے کہ اسی سطح کے خطرے پر آپ کے پورٹ فولیو نے مارکیٹ سے بہتر کارکردگی دکھائی۔",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "پورٹ فولیو کے ہر حصے نے کل منافع میں کتنا اضافہ کیا یا اس میں کتنی کمی کی۔ تمام حصوں کا مجموعہ وہی منافع بنتا ہے جو آپ کو حقیقتاً ملا۔",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "آپ کے خطرے کے پروفائل کے لیے طے شدہ طویل مدتی مرکب۔ مارکیٹ کی حرکت کے ساتھ پوزیشنیں اس سے ہٹ جاتی ہیں اور توازن بحال کرتے وقت واپس لائی جاتی ہیں۔",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "دکھایا گیا تمام منافع فیسوں کی کٹوتی کے بعد کا ہے، اس لیے یہ آپ کی حقیقی کمائی کو ظاہر کرتا ہے۔",
        "Valuations":
            "تشخیص",
        "as at":
            "بتاریخ",
        "Portfolio vs benchmark":
            "پورٹ فولیو بمقابلہ بینچ مارک",
        "last column is drift from target":
            "آخری کالم ہدف سے انحراف ظاہر کرتا ہے",
        "Strategic target":
            "حکمت عملی کا ہدف",
        "Net of fees":
            "فیسوں کی کٹوتی کے بعد",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "ماضی کی کارکردگی مستقبل کے نتائج کی ضمانت نہیں۔ اعداد و شمار فیسوں کی کٹوتی کے بعد کے ہیں جب تک کہ دوسری صورت نہ بتائی جائے۔",
        "Give me a quick summary of this report.":
            "مجھے اس رپورٹ کا مختصر خلاصہ دیں۔",
        "Explain the fees I paid this period.":
            "اس مدت میں ادا کی گئی فیسوں کی وضاحت کریں۔",
        "How did I do against the benchmark?":
            "بینچ مارک کے مقابلے میں میری کارکردگی کیسی رہی؟",
        "Allocation donut":
            "تقسیم کا ڈونٹ چارٹ",
        "Actual vs target":
            "حقیقی بمقابلہ ہدف",
        "Return drivers":
            "منافع کے محرکات",
        "Holdings treemap":
            "ملکیت کا ٹری میپ",
        "You vs benchmark":
            "آپ بمقابلہ بینچ مارک",
        "Fee breakdown":
            "فیسوں کی تفصیل",
        "Money in and out":
            "آنے اور جانے والی رقم",
        "Show me my asset allocation as a donut chart.":
            "میرے اثاثوں کی تقسیم ڈونٹ چارٹ کے طور پر دکھائیں۔",
        "Show me my allocation against target as a bar chart.":
            "ہدف کے مقابلے میں میری تقسیم بار چارٹ کے طور پر دکھائیں۔",
        "Show me what drove my return as a waterfall chart.":
            "میرے منافع کے محرکات واٹر فال چارٹ کے طور پر دکھائیں۔",
        "Show me my largest holdings as a treemap.":
            "میری سب سے بڑی ملکیتیں ٹری میپ کے طور پر دکھائیں۔",
        "Plot my return over time as a line chart.":
            "وقت کے ساتھ میرا منافع لائن چارٹ کے طور پر بنائیں۔",
        "Chart my return against the benchmark as a bar chart.":
            "بینچ مارک کے مقابلے میں میرا منافع بار چارٹ کے طور پر بنائیں۔",
        "Show me what I paid as a donut chart.":
            "میں نے جو ادا کیا وہ ڈونٹ چارٹ کے طور پر دکھائیں۔",
        "Show me my cash flow in and out as a donut chart.":
            "میری آنے اور جانے والی رقم ڈونٹ چارٹ کے طور پر دکھائیں۔",
        "How your portfolio is invested":
            "آپ کا پورٹ فولیو کس طرح سرمایہ کاری شدہ ہے",
        "Where you sit against your target":
            "آپ اپنے ہدف کے مقابلے میں کہاں ہیں",
        "What drove your return":
            "آپ کے منافع کا سبب کیا بنا",
        "Your largest holdings":
            "آپ کی سب سے بڑی ملکیتیں",
        "Your return over time":
            "وقت کے ساتھ آپ کا منافع",
        "You against your benchmark":
            "آپ اپنے بینچ مارک کے مقابلے میں",
        "since":
            "سے",
        "vs":
            "بمقابلہ",
        "benchmark":
            "بینچ مارک",
        "Quarterly Portfolio Review":
            "سہ ماہی پورٹ فولیو جائزہ",
        "Conservative":
            "محتاط",
        "Moderate":
            "متوازن",
        "Growth":
            "نمو",
        "Aggressive":
            "جارحانہ",
    },

    # ── Bengali ─────────────────────────────────────────────────
    "bn": {
        "US Equity":
            "মার্কিন শেয়ার",
        "Intl Equity":
            "আন্তর্জাতিক শেয়ার",
        "Fixed Income":
            "স্থির আয়",
        "Alternatives":
            "বিকল্প বিনিয়োগ",
        "Real Assets":
            "প্রকৃত সম্পদ",
        "Cash":
            "নগদ",
        "Asset allocation":
            "সম্পদ বণ্টন",
        "Allocation detail":
            "বণ্টনের বিবরণ",
        "Allocation vs strategic target":
            "কৌশলগত লক্ষ্যের সাপেক্ষে বণ্টন",
        "Fees and costs":
            "ফি ও খরচ",
        "What you paid":
            "আপনি যা পরিশোধ করেছেন",
        "At a glance":
            "এক নজরে",
        "Performance vs benchmark":
            "বেঞ্চমার্কের তুলনায় কার্যকারিতা",
        "Contribution to return":
            "রিটার্নে অবদান",
        "Return by period":
            "সময়কাল অনুযায়ী রিটার্ন",
        "Return over time":
            "সময়ের সাথে রিটার্ন",
        "Return this period":
            "এই সময়কালের রিটার্ন",
        "Ahead of benchmark":
            "বেঞ্চমার্কের চেয়ে এগিয়ে",
        "Risk":
            "ঝুঁকি",
        "Top contributors to return":
            "রিটার্নে প্রধান অবদানকারী",
        "Top detractors from return":
            "রিটার্ন হ্রাসকারী প্রধান কারণ",
        "Behind benchmark":
            "বেঞ্চমার্কের চেয়ে পিছিয়ে",
        "Portfolio Growth":
            "পোর্টফোলিওর বৃদ্ধি",
        "Portfolio value and recent performance":
            "পোর্টফোলিওর মূল্য ও সাম্প্রতিক কার্যকারিতা",
        "Key takeaways":
            "মূল বিষয়সমূহ",
        "What these terms mean":
            "এই পরিভাষাগুলির অর্থ",
        "Advisory fee":
            "পরামর্শ ফি",
        "Fund expenses":
            "ফান্ডের খরচ",
        "Total":
            "মোট",
        "Portfolio value":
            "পোর্টফোলিওর মূল্য",
        "Portfolio return":
            "পোর্টফোলিওর রিটার্ন",
        "Portfolio":
            "পোর্টফোলিও",
        "Benchmark":
            "বেঞ্চমার্ক",
        "Return":
            "রিটার্ন",
        "Risk level":
            "ঝুঁকির স্তর",
        "Target":
            "লক্ষ্য",
        "Actual":
            "প্রকৃত",
        "Contribution":
            "অবদান",
        "Cumulative":
            "ক্রমসঞ্চিত",
        "Period":
            "সময়কাল",
        "Difference":
            "পার্থক্য",
        "Others":
            "অন্যান্য",
        "Asset class":
            "সম্পদ শ্রেণি",
        "Weight":
            "ওজন",
        "Value":
            "মূল্য",
        "Fees":
            "ফি",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "কার্যকারিতা মূল্যায়নের জন্য ব্যবহৃত একটি রেফারেন্স মিশ্রণ। এটি অতিক্রম করার অর্থ একই ঝুঁকির স্তরে আপনার পোর্টফোলিও বাজারের চেয়ে ভালো ফল করেছে।",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "পোর্টফোলিওর প্রতিটি অংশ মোট রিটার্নে কতটা যোগ করেছে বা তা থেকে কতটা কমিয়েছে। অবদানগুলির যোগফলই আপনার প্রকৃতপক্ষে পাওয়া রিটার্ন।",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "আপনার ঝুঁকি প্রোফাইলের জন্য সম্মত দীর্ঘমেয়াদি মিশ্রণ। বাজার ওঠানামা করলে অবস্থানগুলি এটি থেকে সরে যায় এবং পুনঃভারসাম্যের সময় ফিরিয়ে আনা হয়।",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "দেখানো সমস্ত রিটার্ন ফি কেটে নেওয়ার পরের, তাই এটি আপনার প্রকৃত উপার্জন প্রতিফলিত করে।",
        "Valuations":
            "মূল্যায়ন",
        "as at":
            "তারিখে",
        "Portfolio vs benchmark":
            "পোর্টফোলিও বনাম বেঞ্চমার্ক",
        "last column is drift from target":
            "শেষ কলামটি লক্ষ্য থেকে বিচ্যুতি দেখায়",
        "Strategic target":
            "কৌশলগত লক্ষ্য",
        "Net of fees":
            "ফি কাটার পর",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "অতীতের কার্যকারিতা ভবিষ্যৎ ফলাফলের নির্দেশক নয়। অন্যভাবে উল্লেখ না থাকলে সংখ্যাগুলি ফি কাটার পরের।",
        "Give me a quick summary of this report.":
            "এই প্রতিবেদনের একটি সংক্ষিপ্ত সারসংক্ষেপ দিন।",
        "Explain the fees I paid this period.":
            "এই সময়কালে আমি যে ফি দিয়েছি তা ব্যাখ্যা করুন।",
        "How did I do against the benchmark?":
            "বেঞ্চমার্কের তুলনায় আমার ফলাফল কেমন হয়েছে?",
        "Allocation donut":
            "বণ্টনের ডোনাট চার্ট",
        "Actual vs target":
            "প্রকৃত বনাম লক্ষ্য",
        "Return drivers":
            "রিটার্নের চালিকাশক্তি",
        "Holdings treemap":
            "হোল্ডিংয়ের ট্রিম্যাপ",
        "You vs benchmark":
            "আপনি বনাম বেঞ্চমার্ক",
        "Fee breakdown":
            "ফির বিশ্লেষণ",
        "Money in and out":
            "অর্থের আগমন ও নির্গমন",
        "Show me my asset allocation as a donut chart.":
            "আমার সম্পদ বণ্টন ডোনাট চার্ট হিসেবে দেখান।",
        "Show me my allocation against target as a bar chart.":
            "লক্ষ্যের সাপেক্ষে আমার বণ্টন বার চার্ট হিসেবে দেখান।",
        "Show me what drove my return as a waterfall chart.":
            "আমার রিটার্নের চালিকাশক্তি জলপ্রপাত চার্ট হিসেবে দেখান।",
        "Show me my largest holdings as a treemap.":
            "আমার বৃহত্তম হোল্ডিংগুলি ট্রিম্যাপ হিসেবে দেখান।",
        "Plot my return over time as a line chart.":
            "সময়ের সাথে আমার রিটার্ন লাইন চার্ট হিসেবে আঁকুন।",
        "Chart my return against the benchmark as a bar chart.":
            "বেঞ্চমার্কের সাপেক্ষে আমার রিটার্ন বার চার্ট হিসেবে আঁকুন।",
        "Show me what I paid as a donut chart.":
            "আমি যা পরিশোধ করেছি তা ডোনাট চার্ট হিসেবে দেখান।",
        "Show me my cash flow in and out as a donut chart.":
            "আমার অর্থের আগমন ও নির্গমন ডোনাট চার্ট হিসেবে দেখান।",
        "How your portfolio is invested":
            "আপনার পোর্টফোলিও কীভাবে বিনিয়োগ করা হয়েছে",
        "Where you sit against your target":
            "আপনার লক্ষ্যের সাপেক্ষে আপনার অবস্থান",
        "What drove your return":
            "কী আপনার রিটার্ন চালিত করেছে",
        "Your largest holdings":
            "আপনার বৃহত্তম হোল্ডিং",
        "Your return over time":
            "সময়ের সাথে আপনার রিটার্ন",
        "You against your benchmark":
            "আপনি আপনার বেঞ্চমার্কের সাপেক্ষে",
        "since":
            "থেকে",
        "vs":
            "বনাম",
        "benchmark":
            "বেঞ্চমার্ক",
        "Quarterly Portfolio Review":
            "ত্রৈমাসিক পোর্টফোলিও পর্যালোচনা",
        "Conservative":
            "রক্ষণশীল",
        "Moderate":
            "মাঝারি",
        "Growth":
            "প্রবৃদ্ধি",
        "Aggressive":
            "আক্রমণাত্মক",
    },

    # ── Swahili ─────────────────────────────────────────────────
    "sw": {
        "US Equity":
            "Hisa za Marekani",
        "Intl Equity":
            "Hisa za kimataifa",
        "Fixed Income":
            "Dhamana za mapato thabiti",
        "Alternatives":
            "Uwekezaji mbadala",
        "Real Assets":
            "Mali halisi",
        "Cash":
            "Fedha taslimu",
        "Asset allocation":
            "Ugawaji wa mali",
        "Allocation detail":
            "Maelezo ya ugawaji",
        "Allocation vs strategic target":
            "Ugawaji dhidi ya lengo la kimkakati",
        "Fees and costs":
            "Ada na gharama",
        "What you paid":
            "Ulicholipa",
        "At a glance":
            "Kwa muhtasari",
        "Performance vs benchmark":
            "Utendaji dhidi ya kipimo",
        "Contribution to return":
            "Mchango kwa faida",
        "Return by period":
            "Faida kwa kipindi",
        "Return over time":
            "Faida kwa muda",
        "Return this period":
            "Faida ya kipindi hiki",
        "Ahead of benchmark":
            "Juu ya kipimo",
        "Risk":
            "Hatari",
        "Top contributors to return":
            "Vichangiaji vikuu vya faida",
        "Top detractors from return":
            "Vipunguzaji vikuu vya faida",
        "Behind benchmark":
            "Chini ya kipimo",
        "Portfolio Growth":
            "Ukuaji wa portfolio",
        "Portfolio value and recent performance":
            "Thamani ya portfolio na utendaji wa hivi karibuni",
        "Key takeaways":
            "Mambo makuu",
        "What these terms mean":
            "Maana ya maneno haya",
        "Advisory fee":
            "Ada ya ushauri",
        "Fund expenses":
            "Gharama za mfuko",
        "Total":
            "Jumla",
        "Portfolio value":
            "Thamani ya portfolio",
        "Portfolio return":
            "Faida ya portfolio",
        "Portfolio":
            "Portfolio",
        "Benchmark":
            "Kipimo",
        "Return":
            "Faida",
        "Risk level":
            "Kiwango cha hatari",
        "Target":
            "Lengo",
        "Actual":
            "Halisi",
        "Contribution":
            "Mchango",
        "Cumulative":
            "Jumlisho",
        "Period":
            "Kipindi",
        "Difference":
            "Tofauti",
        "Others":
            "Nyingine",
        "Asset class":
            "Aina ya mali",
        "Weight":
            "Uzito",
        "Value":
            "Thamani",
        "Fees":
            "Ada",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Mchanganyiko wa marejeleo unaotumika kupima utendaji. Kuupita kunamaanisha portfolio yako ilifanya vizuri zaidi kuliko soko katika kiwango kile kile cha hatari.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Kiasi ambacho kila sehemu ya portfolio iliongeza au ilipunguza kwenye faida ya jumla. Jumla ya michango ni sawa na faida uliyoipata kweli.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Mchanganyiko wa muda mrefu uliokubaliwa kwa wasifu wako wa hatari. Nafasi hujitenga nao soko linaposonga, na hurudishwa wakati wa kurekebisha uwiano.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Faida zote zinazoonyeshwa ni baada ya kutolewa kwa ada, hivyo zinaonyesha ulichopata kweli.",
        "Valuations":
            "Tathmini",
        "as at":
            "kufikia",
        "Portfolio vs benchmark":
            "Portfolio dhidi ya kipimo",
        "last column is drift from target":
            "safu ya mwisho inaonyesha mkengeuko kutoka lengo",
        "Strategic target":
            "Lengo la kimkakati",
        "Net of fees":
            "Baada ya ada",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Utendaji wa awali si kiashiria cha matokeo ya baadaye. Takwimu ni baada ya kutolewa kwa ada isipokuwa imeelezwa vinginevyo.",
        "Give me a quick summary of this report.":
            "Nipe muhtasari mfupi wa ripoti hii.",
        "Explain the fees I paid this period.":
            "Eleza ada nilizolipa katika kipindi hiki.",
        "How did I do against the benchmark?":
            "Nilifanyaje ikilinganishwa na kipimo?",
        "Allocation donut":
            "Chati ya duara ya ugawaji",
        "Actual vs target":
            "Halisi dhidi ya lengo",
        "Return drivers":
            "Vichochezi vya faida",
        "Holdings treemap":
            "Ramani ya umiliki",
        "You vs benchmark":
            "Wewe dhidi ya kipimo",
        "Fee breakdown":
            "Mchanganuo wa ada",
        "Money in and out":
            "Fedha zinazoingia na kutoka",
        "Show me my asset allocation as a donut chart.":
            "Nionyeshe ugawaji wa mali zangu kama chati ya duara.",
        "Show me my allocation against target as a bar chart.":
            "Nionyeshe ugawaji wangu dhidi ya lengo kama chati ya safu.",
        "Show me what drove my return as a waterfall chart.":
            "Nionyeshe kilichochochea faida yangu kama chati ya maporomoko.",
        "Show me my largest holdings as a treemap.":
            "Nionyeshe umiliki wangu mkubwa zaidi kama ramani ya mti.",
        "Plot my return over time as a line chart.":
            "Chora faida yangu kwa muda kama chati ya mstari.",
        "Chart my return against the benchmark as a bar chart.":
            "Chora faida yangu dhidi ya kipimo kama chati ya safu.",
        "Show me what I paid as a donut chart.":
            "Nionyeshe nilicholipa kama chati ya duara.",
        "Show me my cash flow in and out as a donut chart.":
            "Nionyeshe fedha zangu zinazoingia na kutoka kama chati ya duara.",
        "How your portfolio is invested":
            "Jinsi portfolio yako ilivyowekezwa",
        "Where you sit against your target":
            "Ulipo ikilinganishwa na lengo lako",
        "What drove your return":
            "Kilichochochea faida yako",
        "Your largest holdings":
            "Umiliki wako mkubwa zaidi",
        "Your return over time":
            "Faida yako kwa muda",
        "You against your benchmark":
            "Wewe dhidi ya kipimo chako",
        "since":
            "tangu",
        "vs":
            "dhidi ya",
        "benchmark":
            "kipimo",
        "Quarterly Portfolio Review":
            "Mapitio ya Portfolio ya Robo Mwaka",
        "Conservative":
            "Tahadhari",
        "Moderate":
            "Wastani",
        "Growth":
            "Ukuaji",
        "Aggressive":
            "Ujasiri",
    },

    # ── Albanian ────────────────────────────────────────────────
    "sq": {
        "US Equity":
            "Aksione amerikane",
        "Intl Equity":
            "Aksione ndërkombëtare",
        "Fixed Income":
            "Obligacione",
        "Alternatives":
            "Investime alternative",
        "Real Assets":
            "Asete reale",
        "Cash":
            "Para të gatshme",
        "Asset allocation":
            "Shpërndarja e aseteve",
        "Allocation detail":
            "Detajet e shpërndarjes",
        "Allocation vs strategic target":
            "Shpërndarja kundrejt objektivit strategjik",
        "Fees and costs":
            "Tarifat dhe kostot",
        "What you paid":
            "Çfarë keni paguar",
        "At a glance":
            "Me një vështrim",
        "Performance vs benchmark":
            "Performanca kundrejt indeksit të referencës",
        "Contribution to return":
            "Kontributi në kthim",
        "Return by period":
            "Kthimi sipas periudhave",
        "Return over time":
            "Kthimi me kalimin e kohës",
        "Return this period":
            "Kthimi i kësaj periudhe",
        "Ahead of benchmark":
            "Mbi indeksin e referencës",
        "Risk":
            "Rreziku",
        "Top contributors to return":
            "Kontribuesit kryesorë në kthim",
        "Top detractors from return":
            "Faktorët kryesorë që ulën kthimin",
        "Behind benchmark":
            "Nën indeksin e referencës",
        "Portfolio Growth":
            "Ecuria e portofolit",
        "Portfolio value and recent performance":
            "Vlera e portofolit dhe performanca e fundit",
        "Key takeaways":
            "Përfundimet kryesore",
        "What these terms mean":
            "Çfarë nënkuptojnë këto terma",
        "Advisory fee":
            "Tarifa e këshillimit",
        "Fund expenses":
            "Shpenzimet e fondeve",
        "Total":
            "Totali",
        "Portfolio value":
            "Vlera e portofolit",
        "Portfolio return":
            "Kthimi i portofolit",
        "Portfolio":
            "Portofoli",
        "Benchmark":
            "Indeksi i referencës",
        "Return":
            "Kthimi",
        "Risk level":
            "Niveli i rrezikut",
        "Target":
            "Objektivi",
        "Actual":
            "Faktik",
        "Contribution":
            "Kontributi",
        "Cumulative":
            "Kumulativ",
        "Period":
            "Periudha",
        "Difference":
            "Diferenca",
        "Others":
            "Të tjera",
        "Asset class":
            "Klasa e aseteve",
        "Weight":
            "Pesha",
        "Value":
            "Vlera",
        "Fees":
            "Tarifat",
        "A reference mix used to judge performance. Beating it means your portfolio did better than the market did at that level of risk.":
            "Një përbërje referencë e përdorur për të vlerësuar performancën. Tejkalimi i saj do të thotë se portofoli juaj pati një rezultat më të mirë se tregu në të njëjtin nivel rreziku.",
        "How much each part of the portfolio added to, or took from, the total return. Contributions add up to the return you actually received.":
            "Sa shtoi ose sa hoqi secila pjesë e portofolit nga kthimi total. Shuma e kontributeve është e barabartë me kthimin që keni marrë në të vërtetë.",
        "The long-term mix agreed for your risk profile. Holdings drift away from it as markets move, and are brought back at rebalancing.":
            "Përbërja afatgjatë e rënë dakord për profilin tuaj të rrezikut. Pozicionet largohen prej saj ndërsa tregjet lëvizin dhe kthehen gjatë ribalancimit.",
        "Every return shown is after fees have been deducted, so it reflects what you actually earned.":
            "Të gjitha kthimet e paraqitura janë pas zbritjes së tarifave dhe pasqyrojnë atë që keni fituar realisht.",
        "Valuations":
            "Vlerësimet",
        "as at":
            "më datë",
        "Portfolio vs benchmark":
            "Portofoli kundrejt indeksit të referencës",
        "last column is drift from target":
            "kolona e fundit tregon devijimin nga objektivi",
        "Strategic target":
            "Objektivi strategjik",
        "Net of fees":
            "Pas tarifave",
        "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.":
            "Performanca e kaluar nuk është tregues i rezultateve të ardhshme. Shifrat janë pas zbritjes së tarifave, përveç rasteve kur specifikohet ndryshe.",
        "Give me a quick summary of this report.":
            "Më jep një përmbledhje të shkurtër të këtij raporti.",
        "Explain the fees I paid this period.":
            "Shpjego tarifat që kam paguar në këtë periudhë.",
        "How did I do against the benchmark?":
            "Si dola kundrejt indeksit të referencës?",
        "Allocation donut":
            "Grafik unazor i shpërndarjes",
        "Actual vs target":
            "Faktik kundrejt objektivit",
        "Return drivers":
            "Nxitësit e kthimit",
        "Holdings treemap":
            "Harta e pozicioneve",
        "You vs benchmark":
            "Ju kundrejt indeksit të referencës",
        "Fee breakdown":
            "Ndarja e tarifave",
        "Money in and out":
            "Hyrjet dhe daljet e parave",
        "Show me my asset allocation as a donut chart.":
            "Më trego shpërndarjen e aseteve të mia si grafik unazor.",
        "Show me my allocation against target as a bar chart.":
            "Më trego shpërndarjen time kundrejt objektivit si grafik me shtylla.",
        "Show me what drove my return as a waterfall chart.":
            "Më trego çfarë nxiti kthimin tim si grafik ujëvarë.",
        "Show me my largest holdings as a treemap.":
            "Më trego pozicionet e mia më të mëdha si hartë peme.",
        "Plot my return over time as a line chart.":
            "Vizato kthimin tim me kalimin e kohës si grafik linear.",
        "Chart my return against the benchmark as a bar chart.":
            "Vizato kthimin tim kundrejt indeksit të referencës si grafik me shtylla.",
        "Show me what I paid as a donut chart.":
            "Më trego çfarë kam paguar si grafik unazor.",
        "Show me my cash flow in and out as a donut chart.":
            "Më trego hyrjet dhe daljet e mia të parave si grafik unazor.",
        "How your portfolio is invested":
            "Si është investuar portofoli juaj",
        "Where you sit against your target":
            "Ku ndodheni kundrejt objektivit tuaj",
        "What drove your return":
            "Çfarë nxiti kthimin tuaj",
        "Your largest holdings":
            "Pozicionet tuaja më të mëdha",
        "Your return over time":
            "Kthimi juaj me kalimin e kohës",
        "You against your benchmark":
            "Ju kundrejt indeksit tuaj të referencës",
        "since":
            "që nga",
        "vs":
            "kundrejt",
        "benchmark":
            "indeksi i referencës",
        "Quarterly Portfolio Review":
            "Rishikimi Tremujor i Portofolit",
        "Conservative":
            "Konservator",
        "Moderate":
            "I moderuar",
        "Growth":
            "Rritje",
        "Aggressive":
            "Agresiv",
    },

}


# The labels a reviewer should look at before anything else, by English key.
# Chosen because a wrong rendering here is either regulatory (the disclosure,
# the net-of-fees statement) or is a term whose everyday sense differs from
# its financial sense — the failure mode where machine translation reads
# fluent and means something else entirely.
REVIEW_FIRST = (
    "Past performance is not indicative of future results. Figures are net of fees unless stated otherwise.",
    "Every return shown is after fees have been deducted, so it reflects what you actually earned.",
    "Fixed Income",
    "Cash",
    "Real Assets",
    "Alternatives",
    "Benchmark",
    "Net of fees",
    "Advisory fee",
    "Fund expenses",
    "Strategic target",
    "Risk level",
    "Conservative",
    "Moderate",
    "Aggressive",
)


def merge_into(labels: Dict[str, Dict[str, str]]) -> None:
    """Fold the drafts into the main LABELS table.

    Writes into the per-English-string dict that labels.py already built, so
    lookup stays one dict access and nothing downstream needs to know these
    languages arrived from a different file.

    Never overwrites: if a language ever gets promoted into labels.py after
    review, the reviewed string there wins over the draft here, and this
    module can be trimmed at leisure instead of urgently.
    """
    for lang, table in DRAFTS.items():
        for english, translated in table.items():
            entry = labels.get(english)
            if entry is None:          # a label added to labels.py later
                continue               # and not yet drafted here
            entry.setdefault(lang, translated)
