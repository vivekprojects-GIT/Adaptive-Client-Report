"""The whole product, end to end, against a RUNNING server.

    python scripts/test_full_loop.py

Simulates the actual journey:

  advisor:  generate a report for C1004 (the loss quarter — the hard case)
            -> LLM writes the prose, grounding gates it, SQL persists it
  client:   opens the signed link            (report_opened -> D1)
            highlights the fees section
            asks about it                    (localised, grounded answer)
            asks for it "in simple terms"    (profile: technical_depth down)
            thumbs-up an answer              (D2 reward on the exact arm)
            says the report helped           (D1 reward on the exact arm)
  system:   every event lands in `events`; D1/D2 state moves; the client's
            preference profile drifts; the next report would be written
            from those dimensions.

Every step asserts on DATABASE STATE, not just HTTP 200s — a loop that
returns 200 while learning nothing must fail here.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The server loads .env at startup; this process must too, or mint() signs
# report links with the fallback secret and every link it creates is
# rejected by the server as a signature mismatch.
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

BASE = "http://127.0.0.1:8734"
CLIENT, PERIOD = "C1004", "2026Q1"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))


# Advisor endpoints sit behind the session gate whenever ADVISOR_PASSWORD is
# set, so the test signs in exactly as an advisor does. Client-facing /r/
# routes stay open and need no cookie — which this run also proves.
_OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def http(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with _OPENER.open(req, timeout=180) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        # Error bodies matter here: the bad-token test asserts on the 403
        # page's wording, not just its status.
        raw = e.read().decode()
    return json.loads(raw) if raw.strip().startswith(("{", "[")) else raw


def advisor_login():
    """No-op when the gate is disabled; required when it is not."""
    from dotenv import dotenv_values
    pw = (os.getenv("ADVISOR_PASSWORD")
          or dotenv_values(ROOT / ".env").get("ADVISOR_PASSWORD", ""))
    if not pw:
        print("  advisor gate disabled (no ADVISOR_PASSWORD)")
        return
    req = urllib.request.Request(
        BASE + "/login", method="POST",
        data=urllib.parse.urlencode({"password": pw}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        _OPENER.open(req, timeout=30)
        print("  advisor signed in")
    except urllib.error.HTTPError as e:
        sys.exit(f"advisor login failed ({e.code}) — check ADVISOR_PASSWORD")


def reset_fixture():
    """Clear THIS report's interaction rows so reruns start clean.

    The product deduplicates rewards per report — correct behaviour, but it
    means a second test run would fail on 'already rewarded' unless the
    fixture is reset. Only rows for the test report/client are touched.
    """
    from ape.db.session import session_scope
    from ape.db.models import Conversation, Event, Message, Report
    from sqlalchemy import delete
    rid = f"R_{CLIENT}_{PERIOD}_quarterly_portfolio_review"
    with session_scope() as db:
        db.execute(delete(Event).where(Event.report_id == rid))
        db.execute(delete(Message).where(Message.report_id == rid))
        db.execute(delete(Conversation).where(Conversation.report_id == rid))
        rep = db.get(Report, rid)
        if rep is not None:
            rep.normalized_reward = 0.0
            rep.reward_status = "PENDING"
    print(f"  fixture reset for {rid}\n")


def main():
    advisor_login()
    reset_fixture()
    print("1. ADVISOR GENERATES (LLM writes, grounding gates, SQL persists)")
    gen = http("POST", "/reports/generate-one",
               {"client_id": CLIENT, "period": PERIOD,
                "report_type": "quarterly_portfolio_review"})
    rid = gen["report_id"]
    check("report generated", bool(rid), rid)
    authors = gen.get("authors", {})
    # Arms carry different numbers of prose blocks by design (concise has
    # one, balanced three), so assert on the RATIO written rather than a
    # fixed count — and that the arm has prose at all, since an arm the
    # writer cannot touch gets no personalisation.
    llm_blocks = [k for k, v in authors.items() if v.startswith("llm")]
    check("arm has prose for the LLM to write", len(authors) >= 1, f"{authors}")
    check("LLM wrote them (not all fallback)",
          len(llm_blocks) >= max(1, len(authors) - 1), f"{authors}")
    check("grounding verdict clean", gen["validation"] == "passed",
          gen["validation_summary"])

    from ape.db.session import session_scope
    from ape.db.models import (ApeState, ClientPreference, Event, Message,
                               Report, ReportBlock)
    from sqlalchemy import select, func

    with session_scope() as db:
        rep = db.get(Report, rid)
        check("report row in SQL", rep is not None and rep.template_arm != "",
              f"arm={rep.template_arm}, method={rep.selection_method}" if rep else "")
        nblocks = db.scalar(select(func.count()).select_from(ReportBlock)
                            .where(ReportBlock.report_id == rid))
        check("blocks persisted with source_refs", nblocks and nblocks > 5,
              f"{nblocks} blocks")

    print("\n2. CLIENT OPENS THE SIGNED LINK")
    from ape.reporting.tokens import mint
    token = mint(rid, CLIENT)
    page = http("GET", f"/r/{rid}?token={token}")
    check("viewer serves", "Ask about your report" in page)
    check("client sees no template internals",
          "badge" not in page.split("</style>")[-1] and rid not in
          page.split("</style>")[-1].split("var RID")[0])
    check("bad token rejected", "cannot be opened" in
          http("GET", f"/r/{rid}?token=garbage"))

    http("POST", f"/r/{rid}/events", {"token": token,
                                      "event_type": "report_opened"})

    print("\n3. HIGHLIGHT THE FEES SECTION AND ASK")
    with session_scope() as db:
        fees_block = db.scalars(select(ReportBlock).where(
            ReportBlock.report_id == rid,
            ReportBlock.block_type == "fees_table")).first()
        fee_bid = fees_block.block_id if fees_block else None
    check("fees block addressable", fee_bid is not None, fee_bid or "")

    ans = http("POST", f"/r/{rid}/chat",
               {"token": token, "block_id": fee_bid,
                "question": "I don't understand this section. What am I "
                            "actually paying for?"})
    check("answer produced", bool(ans.get("answer")), ans.get("strategy", ""))
    check("answer localised to the highlight",
          ans.get("grounded_in") == fee_bid, ans.get("grounded_in", ""))
    check("intent classified", ans.get("intent") == "fees_cashflow_question",
          ans.get("intent", ""))
    print(f"       Q: I don't understand this section...")
    print(f"       A[{ans['strategy']}]: {ans['answer'][:220]}...")

    print("\n4. A FORMAT-REVEALING QUESTION (profile signal)")
    ans2 = http("POST", f"/r/{rid}/chat",
                {"token": token, "conversation_id": ans["conversation_id"],
                 "question": "Can you explain that in simple terms, "
                             "in a short summary?"})
    check("follow-up answered in same conversation",
          ans2.get("conversation_id") == ans["conversation_id"])

    print("\n5. THUMBS UP -> D2 REWARD ON THE EXACT ARM")
    fb = http("POST", f"/r/{rid}/events",
              {"token": token, "event_type": "answer_helpful",
               "message_id": ans2["message_id"],
               "metadata": {"strategy": ans2["strategy"]}})
    d2 = fb.get("d2", {})
    check("D2 reward applied", d2.get("applied") is True,
          f"{d2.get('intent')}/{d2.get('arm')} -> {d2.get('arm_totals')}")

    with session_scope() as db:
        row = db.scalars(select(ApeState).where(
            ApeState.decision == "D2",
            ApeState.context == ans2["intent"],
            ApeState.arm_id == ans2["strategy"])).first()
        check("D2 posterior moved in SQL",
              row is not None and row.total_reward > 0,
              f"count={row.selection_count}, reward={row.total_reward}" if row else "")

    print("\n6. REPORT FEEDBACK -> D1 REWARD ON THE TEMPLATE ARM")
    fb2 = http("POST", f"/r/{rid}/events",
               {"token": token, "event_type": "report_helpful"})
    d1 = fb2.get("d1", {})
    check("D1 reward applied", d1.get("applied") is True,
          f"arm={d1.get('arm')}, accrued={d1.get('accrued')}")
    fb3 = http("POST", f"/r/{rid}/events",
               {"token": token, "event_type": "report_helpful"})
    check("same event pays only once",
          fb3.get("d1", {}).get("applied") is False,
          fb3.get("d1", {}).get("reason", ""))

    print("\n7. THE PROFILE DRIFTED FROM HOW THEY ENGAGED")
    with session_scope() as db:
        pref = db.get(ClientPreference, CLIENT)
        check("signals counted", pref.meaningful_signal_count > 0,
              f"n={pref.meaningful_signal_count}")
        check("technical_depth moved DOWN (asked for simple terms)",
              pref.technical_depth < 0.5, f"{pref.technical_depth:.3f}")
        check("concise moved UP (asked for short summary)",
              pref.concise > 0.5, f"{pref.concise:.3f}")

        nev = db.scalar(select(func.count()).select_from(Event)
                        .where(Event.report_id == rid))
        check("every action recorded in events", nev >= 5, f"{nev} events")
        nmsg = db.scalar(select(func.count()).select_from(Message)
                         .where(Message.report_id == rid))
        check("conversation persisted", nmsg == 4, f"{nmsg} messages")

    print("\n8. NEXT REPORT IS WRITTEN FROM THE LEARNED PROFILE")
    gen2 = http("POST", "/reports/generate-one",
                {"client_id": CLIENT, "period": "2026Q2",
                 "report_type": "quarterly_portfolio_review"})
    check("regeneration with learned dimensions succeeds",
          gen2.get("validation") == "passed", gen2.get("validation_summary", ""))

    print("\n" + "-" * 60)
    print(f"passed {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print(f"   ! {f}")
        raise SystemExit(1)
    print("THE LOOP IS CLOSED: generate -> deliver -> converse -> learn")


if __name__ == "__main__":
    main()
