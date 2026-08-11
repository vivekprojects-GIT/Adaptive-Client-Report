"""One-shot patch: persist full snapshots on client import + generate-one.

Kept as a script rather than done inline because the edits span three files
and need to be re-runnable if the API is regenerated.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# 1. Client import must store the WHOLE snapshot.
#
# It previously stored only summary fields (name, email, segment, value).
# Regenerating a report needs allocations, attribution, fees and flows too —
# without them there is nothing to build blocks from, and the advisor screen
# cannot generate for a client it has already imported.
# ---------------------------------------------------------------------------
api = ROOT / "ape" / "api.py"
s = api.read_text(encoding="utf-8")

old_import = '''        store.db["ape_clients"].update_one(
            {"client_id": s.client_id},
            {"$set": {
                "client_id": s.client_id, "display_name": s.display_name,
                "email": s.email, "segment_id": s.segment_id,
                "last_period": s.period, "portfolio_value": s.portfolio_value,
            }},
            upsert=True,
        )'''

new_import = '''        store.db["ape_clients"].update_one(
            {"client_id": s.client_id},
            {"$set": {
                "client_id": s.client_id, "display_name": s.display_name,
                "email": s.email, "segment_id": s.segment_id,
                "last_period": s.period, "portfolio_value": s.portfolio_value,
                # The FULL snapshot, so a report can be regenerated later
                # without re-uploading the CSV. Summary fields alone are not
                # enough to build blocks from.
                "snapshot": {
                    "client_id": s.client_id, "display_name": s.display_name,
                    "email": s.email, "segment_id": s.segment_id,
                    "period": s.period, "as_of": s.as_of,
                    "portfolio_value": s.portfolio_value,
                    "quarter_return_pct": s.quarter_return_pct,
                    "benchmark_return_pct": s.benchmark_return_pct,
                    "risk_level": s.risk_level,
                    "allocations": s.allocations,
                    "attribution": s.attribution,
                    "fees": s.fees, "cash_flows": s.cash_flows,
                },
            }},
            upsert=True,
        )'''

if old_import not in s:
    print("! client import block not found — already patched?")
else:
    s = s.replace(old_import, new_import)
    print("patched: /clients/import now stores the full snapshot")

# ---------------------------------------------------------------------------
# 2. Generate for ONE stored client.
# ---------------------------------------------------------------------------
generate_one = '''
@app.post("/reports/generate-one")
async def generate_one_report(request: Request):
    """Generate a single report for an already-imported client.

    The advisor screen works client-by-client, so it needs a path that does
    not require re-uploading a CSV. Reads the stored snapshot, runs D1, and
    writes the same artifacts as a batch run.
    """
    from .reporting.csv_source import ClientSnapshot
    from .reporting.d1 import cell_key, eligible_arms, select
    from .reporting.generate import build_report, render_html

    body = await request.json()
    client_id = body.get("client_id")
    report_type = body.get("report_type") or "quarterly_portfolio_review"

    store = _guard_store(); cfg = _guard_cfg()
    doc = store.db["ape_clients"].find_one({"client_id": client_id})
    if not doc or not doc.get("snapshot"):
        raise HTTPException(404, f"no stored snapshot for client '{client_id}'")

    rt = next((r for r in cfg.list_report_types()
               if r.get("report_type") == report_type), None)
    if rt is None:
        raise HTTPException(404, f"unknown report type '{report_type}'")

    snap = ClientSnapshot(**doc["snapshot"])
    templates = cfg.list_templates()
    arms = eligible_arms(templates, report_type)
    if not arms:
        raise HTTPException(400, f"no active templates for '{report_type}'")

    key = cell_key(report_type)
    state = {r.get("strategy"): {"count": int(r.get("count", 0)),
                                 "total_reward": float(r.get("total_reward", 0.0))}
             for r in store.bandit_state.find({"cell_key": key})}
    arm_state = {a["strategy"]: state.get(a["strategy"],
                                          {"count": 0, "total_reward": 0.0})
                 for a in arms}

    strategy, rows, method = select(
        templates, arm_state, report_type,
        bool(rt.get("personalisable", True)))

    # count rises at SELECTION so cold-start exploration advances even
    # before any reward lands.
    store.bandit_state.update_one(
        {"cell_key": key, "strategy": strategy},
        {"$inc": {"count": 1},
         "$setOnInsert": {"total_reward": 0.0, "report_type": report_type,
                          "scope": "_global"}},
        upsert=True,
    )

    template = next(t for t in arms if t["strategy"] == strategy)
    report = build_report(snap, template, report_type)

    out = Path(__file__).resolve().parents[1] / "data" / "generated"
    out.mkdir(parents=True, exist_ok=True)
    rid = report["report_id"]
    (out / f"{rid}.html").write_text(render_html(report), encoding="utf-8")
    (out / f"{rid}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    return {
        "report_id": rid, "client_id": client_id, "strategy": strategy,
        "method": method, "template_id": template.get("template_id"),
        "template_label": template.get("label"),
        "blocks": [b["type"] for b in report["blocks"]],
        "validation": "passed",
        "email_status": "sent (stub)",
        "arms": rows,
    }


'''

marker = '@app.post("/reports/generate")'
if "/reports/generate-one" in s:
    print("! generate-one already present")
else:
    s = s.replace(marker, generate_one.lstrip("\n") + marker, 1)
    print("patched: /reports/generate-one added")

api.write_text(s, encoding="utf-8")

import ast
ast.parse(s)
print("api.py parses OK")

# ---------------------------------------------------------------------------
# 3. Frontend wiring.
# ---------------------------------------------------------------------------
js = ROOT / "frontend" / "src" / "api.js"
t = js.read_text(encoding="utf-8")
if "generateOneReport" not in t:
    line = ('  generateOneReport:    (payload)                          '
            '=> request("POST",   "/reports/generate-one", payload),\n')
    t = t.replace("  listGeneratedReports:", line + "  listGeneratedReports:")
    js.write_text(t, encoding="utf-8")
    print("patched: api.js generateOneReport")

page = ROOT / "frontend" / "src" / "pages" / "AdvisorPage.jsx"
p = page.read_text(encoding="utf-8")
old_call = '''      const csv = await api.clientCsvFor(selected.client_id);
      setStatus({ snapshot: "done", generate: "running" });
      const r = await api.generateReports({ csv_text: csv, report_type: reportType });
      const ok = r.generated > 0;'''
new_call = '''      setStatus({ snapshot: "done", generate: "running" });
      const r = await api.generateOneReport({
        client_id: selected.client_id, report_type: reportType,
      });
      const ok = Boolean(r.report_id);'''
if old_call in p:
    p = p.replace(old_call, new_call)
    p = p.replace('report_id: r.results?.[0]?.report_id,', 'report_id: r.report_id,')
    p = p.replace('notify(ok ? `Generated ${r.results[0].strategy} report` : "Nothing generated", ok ? "ok" : "error");',
                  'notify(ok ? `Generated ${r.strategy} report` : "Nothing generated", ok ? "ok" : "error");')
    page.write_text(p, encoding="utf-8")
    print("patched: AdvisorPage uses generateOneReport")
else:
    print("! AdvisorPage call site not found — already patched?")

app = ROOT / "frontend" / "src" / "App.jsx"
a = app.read_text(encoding="utf-8")
if "AdvisorPage" not in a:
    a = a.replace('import ReportsPage from "./pages/ReportsPage.jsx";',
                  'import ReportsPage from "./pages/ReportsPage.jsx";\n'
                  'import AdvisorPage from "./pages/AdvisorPage.jsx";')
    a = a.replace('      <Route path="/"           element={<ReportsPage />} />',
                  '      <Route path="/"           element={<AdvisorPage />} />\n'
                  '      <Route path="/reports"    element={<ReportsPage />} />')
    app.write_text(a, encoding="utf-8")
    print("patched: App.jsx routing")
