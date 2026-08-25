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
    # ── Portuguese ────────────────────────────────────────────────
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

    # ── Swedish ───────────────────────────────────────────────────
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

    # ── Danish ────────────────────────────────────────────────────
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

    # ── Norwegian (Bokmal) ────────────────────────────────────────
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

    # ── Finnish ───────────────────────────────────────────────────
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

    # ── Polish ────────────────────────────────────────────────────
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

    # ── Czech ─────────────────────────────────────────────────────
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

    # ── Greek ─────────────────────────────────────────────────────
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

    # ── Turkish ───────────────────────────────────────────────────
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

    # ── Japanese ──────────────────────────────────────────────────
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

    # ── Chinese (Simplified) ──────────────────────────────────────
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

    # ── Chinese (Traditional) ─────────────────────────────────────
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

    # ── Korean ────────────────────────────────────────────────────
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

    # ── Arabic ────────────────────────────────────────────────────
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

    # ── Hebrew ────────────────────────────────────────────────────
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
