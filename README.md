---
title: Adaptive Client Reporting
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Wealth reports that adapt to how each client reads them
---

# Adaptive Client Reporting

Quarterly wealth reports that are **written** rather than templated, that the
client can **talk to**, and that **learn** from how each client reads them.

## The loop

1. **Generate** — the advisor picks a report type and period; a contextual-UCB
   bandit picks the presentation template using what the client has taught us;
   an LLM writes the prose from a frozen fact sheet.
2. **Deliver & converse** — a signed, expiring link opens an interactive
   report. Highlight any section and ask about it; the answer is grounded in
   that block's own figures.
3. **Adapt** — engagement, thumbs and format requests become rewards for the
   template arm, the answer-format arm, and the client's preference profile,
   which shapes the next report.

## Two invariants, enforced structurally

Personalisation changes **how** facts are presented, never **which** facts:

- **Fidelity** — the model only ever sees a restricted fact sheet, and a
  validator rejects any block stating a number it cannot trace to the frozen
  snapshot. Rejected blocks are dropped, not corrected.
- **Coverage** — mandatory categories (costs, disclosures) are appended at
  build time if a template omits them. A mis-edited template yields a longer
  report, never a report missing the fees.

## Access

- `/r/{report_id}?token=…` — the client viewer. Public by design: each link is
  HMAC-signed for one report and expires.
- Everything else requires an advisor session (`ADVISOR_PASSWORD`).

See `DEPLOY.md` for required Space secrets. Without `APP_BASE_URL`, emailed
links point at localhost and open nowhere.
