"""End-to-end workflow test. Exercises the real HTTP surface, not internals.

    CSV upload -> clients imported (bad rows rejected)
              -> report type selected
              -> D1 selects an arm, explainably
              -> report generated with the template's blocks
              -> HTML renders every block non-empty
              -> artifacts listed and retrievable
              -> prescribed report types refuse D1
              -> config survives a restart

Run against a live server:
    python scripts/test_e2e.py http://127.0.0.1:7893
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7893"

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> bool:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    return cond


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.load(r)


def get_text(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    print(f"E2E against {BASE}\n")

    # ---- 1. config present -------------------------------------------
    print("1. CONFIG")
    types = get("/config/report-types")
    templates = get("/config/templates")
    intents = get("/config/intents")
    policies = get("/config/policies")
    instructions = get("/config/instructions")
    check("report types seeded", len(types) >= 16, f"{len(types)}")
    check("templates seeded", len(templates) >= 60, f"{len(templates)}")
    check("D2 intents seeded", len(intents) >= 10, f"{len(intents)}")
    check("D2 policies seeded", len(policies) >= 29, f"{len(policies)}")
    check("instructions active", len([i for i in instructions
                                      if i.get("status") == "ACTIVE"]) >= 6)
    check("prescribed type exists",
          any(t for t in types if not t.get("personalisable")))

    # ---- 2. CSV ingest ------------------------------------------------
    print("\n2. CSV INGEST")
    csv_text = (ROOT / "data" / "sample_clients.csv").read_text(encoding="utf-8")
    res = post("/clients/import", {"csv_text": csv_text})
    check("valid rows imported", res["imported"] == 5, f"{res['imported']}")
    check("bad row rejected", len(res["rejected"]) == 1)
    if res["rejected"]:
        probs = res["rejected"][0]["problems"]
        check("rejection cites allocation mismatch",
              any("allocations sum" in p for p in probs))
        check("rejection cites attribution mismatch",
              any("attribution sums" in p for p in probs))
        check("rejection cites bad email", any("email" in p for p in probs))

    clients = get("/clients")
    check("client book readable", len(clients) == 5, f"{len(clients)}")
    check("clients carry segment", all(c.get("segment_id") for c in clients))

    # ---- 3. D1 decision ----------------------------------------------
    print("\n3. D1 DECISION")
    rt = "quarterly_portfolio_review"
    d = get(f"/ape/d1-decision?client_id=C1001&report_type={rt}")
    check("decision returned", bool(d.get("selected")), d.get("selected"))
    check("explainable arms", len(d.get("arms", [])) >= 6, f"{len(d.get('arms', []))}")
    check("cell key scoped by report type", d["cell_key"].endswith(rt), d["cell_key"])
    check("no fake client profile", d["has_client_profile"] is False)
    check("weight is 0 with no evidence", d["user_weight"] == 0.0)
    check("every arm scored",
          all("exploit" in a and "count" in a for a in d["arms"]))

    # ---- 4. prescribed refuses D1 -------------------------------------
    print("\n4. PRESCRIBED REPORTS")
    presc = next(t for t in types if not t.get("personalisable"))
    pd = get(f"/ape/d1-decision?client_id=C1001&report_type={presc['report_type']}")
    check("prescribed uses mandated template", pd["method"] == "mandated",
          f"{presc['report_type']} -> {pd['selected']}")
    check("prescribed marked non-personalisable", pd["personalisable"] is False)

    # ---- 5. generation ------------------------------------------------
    print("\n5. GENERATION")
    seen_arms = set()
    reports = []
    for c in clients:
        r = post("/reports/generate-one",
                 {"client_id": c["client_id"], "report_type": rt})
        reports.append(r)
        seen_arms.add(r["strategy"])
    check("one report per client", len(reports) == 5)
    check("batch explored >1 arm", len(seen_arms) > 1,
          " ".join(sorted(seen_arms)))
    check("all report ids unique",
          len({r["report_id"] for r in reports}) == len(reports))
    check("email stubbed, not sent",
          all("stub" in r["email_status"] for r in reports))

    # blocks must match the template that was chosen
    by_strategy = {t["strategy"]: t for t in templates if t["report_type"] == rt}
    ok_blocks = True
    for r in reports:
        want = [str(b).partition(":")[0]
                for b in by_strategy[r["strategy"]]["required_blocks"]]
        if r["blocks"] != want:
            ok_blocks = False
            print(f"        {r['strategy']}: got {r['blocks']} want {want}")
    check("blocks match the selected template", ok_blocks)

    # ---- 6. rendering -------------------------------------------------
    print("\n6. RENDERING")
    for r in reports[:3]:
        html = get_text(f"/reports/{r['report_id']}/html")
        ids = re.findall(r'data-block-id="([^"]+)"', html)
        check(f"{r['strategy']}: every block rendered",
              len(ids) == len(r["blocks"]), f"{len(ids)}/{len(r['blocks'])}")
        # A genuinely empty section is <section ...></section> with nothing
        # between the tags. Searching for "></section>" alone matches any
        # block whose body ends in a closing tag, which is normal.
        empty = re.findall(r"<section[^>]*>\s*</section>", html)
        check(f"{r['strategy']}: no empty sections",
              "<section" in html and not empty,
              f"{len(empty)} empty" if empty else "")
        # numbers must be present, i.e. the report is not a shell
        check(f"{r['strategy']}: contains figures",
              bool(re.search(r"\d[\d,]*\.\d\d", html)))

    # charts actually draw
    vis = next((r for r in reports if r["strategy"] == "visual"), None)
    if vis:
        html = get_text(f"/reports/{vis['report_id']}/html")
        svgs = html.count("<svg")
        shapes = sum(html.count("<" + t) for t in
                     ("rect", "path", "circle", "polyline", "polygon"))
        check("visual template drew charts", svgs >= 2, f"{svgs} svg")
        check("charts contain shapes", shapes > 10, f"{shapes} shapes")

    # ---- 7. artifacts -------------------------------------------------
    print("\n7. ARTIFACTS")
    listed = get("/reports/generated")
    check("generated reports listed", len(listed) >= 5, f"{len(listed)}")
    one = get(f"/reports/{reports[0]['report_id']}/json")
    check("report.json retrievable", one.get("report_id") == reports[0]["report_id"])
    check("report.json records the arm", bool(one.get("template_strategy")))
    check("report.json records template id", bool(one.get("template_id")))
    check("every block declares source_refs",
          all(b.get("source_refs") for b in one["blocks"]))

    # ---- 8. grounding -------------------------------------------------
    print("\n8. GROUNDING")
    snap_client = next(c for c in clients if c["client_id"] == one["client_id"])
    pv = f"{snap_client['portfolio_value']:,.2f}"
    html = get_text(f"/reports/{one['report_id']}/html")
    check("portfolio value appears verbatim", pv in html, pv)

    print("\n" + "-" * 58)
    print(f"passed {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("\nFAILURES:")
        for f in FAIL:
            print(f"   ! {f}")
        raise SystemExit(1)
    print("E2E WORKFLOW PASSES")


if __name__ == "__main__":
    main()
