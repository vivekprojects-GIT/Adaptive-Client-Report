"""Template previews use a fictional client, never a real one."""
from ape.reporting.demo_client import DEMO_CLIENT_ID, demo_snapshot
from ape.reporting.generate import build_report, enforce_mandatory, render_html
from ape.reporting.grounding import validate_report

EVERY_SECTION = [
    "hero_value", "verdict_banner", "kpi_grid", "performance_history", "returns_table",
    "comparison_chart", "allocation_donut", "allocation_vs_target", "holdings_table",
    "holdings_by_sector", "top_contributors", "top_detractors", "fees_table",
    "disclosures",
]


def test_demo_client_is_fictional_and_complete():
    s = demo_snapshot()
    assert s.client_id == DEMO_CLIENT_ID and s.display_name == "John Doe"
    assert s.email.endswith("@example.com")
    assert round(sum(a["weight_pct"] for a in s.allocations), 1) == 100.0
    assert s.holdings and len(s.history) >= 2 and s.targets


def test_every_section_renders_and_passes_the_figure_check():
    s = demo_snapshot()
    template = {"template_id": "t", "strategy": "t", "label": "t", "brief": "",
                "required_blocks": EVERY_SECTION}
    report = build_report(s, template, "quarterly_portfolio_review")
    report["language"] = ""
    enforce_mandatory(report, s)
    verdict = validate_report(report, s.numeric_facts(), s.label_terms())
    assert not verdict.rejected
    ids = [b["block_id"] for b in report["blocks"]]
    missing = [b for b in EVERY_SECTION if not any(i.startswith(b) for i in ids)
               and b not in {x["type"] for x in report["blocks"]}]
    assert not missing
    assert "John Doe" in render_html(report, internal=False)
