import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Toast from "../components/Toast.jsx";
import "../styles/advisor.css";

/**
 * Advisor back office.
 *
 * The workflow is: upload a CSV -> clients appear -> pick a report type ->
 * generate for one client or the whole book -> preview -> send.
 *
 * Every nav destination here is real. A nav item that goes nowhere is worse
 * than no nav item, so anything not built yet is not listed.
 */
const PIPELINE = [
  ["Data snapshot", "snapshot"],
  ["Report generation", "generate"],
  ["Validation (grounding)", "validate"],
  ["Advisor review", "review"],
  ["Email to client", "email"],
];

export default function AdvisorPage() {
  const [view, setView]         = useState("clients");
  const [clients, setClients]   = useState([]);
  const [query, setQuery]       = useState("");
  const [selected, setSelected] = useState(null);
  const [types, setTypes]       = useState([]);
  const [templates, setTemplates] = useState([]);
  const [reportType, setRt]     = useState("quarterly_portfolio_review");
  const [decision, setDecision] = useState(null);
  const [status, setStatus]     = useState({});
  const [generated, setGenerated] = useState([]);
  const [busy, setBusy]         = useState(false);
  const [importInfo, setImport] = useState(null);
  const [preview, setPreview]   = useState(null);
  const [period, setPeriod]     = useState("");        // "" = latest on file
  // "" = APE selects a written template (and the choice is a rewardable
  // arm). "llm" = the model composes a bespoke one from the block registry.
  const [composer, setComposer] = useState("");
  const [insight, setInsight]   = useState(null);
  const [note, setNote]         = useState("");
  // Which modes this deployment offers. Read from the server rather
  // than assumed, so a control that the server would override is
  // never drawn in the first place.
  const [selectorOn, setSelectorOn] = useState(true);
  const [toast, setToast]       = useState({ msg: null, kind: "" });
  const fileRef = useRef(null);
  const notify = (msg, kind = "ok") => setToast({ msg, kind });

  async function refreshAll() {
    const [c, t, g, tpl] = await Promise.all([
      api.listClients(), api.listReportTypes(),
      api.listGeneratedReports(), api.listTemplates(),
    ]);
    setClients(c); setTypes(t); setGenerated(g); setTemplates(tpl);
    if (c.length && !selected) setSelected(c[0]);
  }

  useEffect(() => { refreshAll().catch((e) => notify("Load failed: " + e.message, "error")); }, []);

  useEffect(() => {
    api.features()
       .then((f) => {
         const on = f.template_selection !== false;
         setSelectorOn(on);
         if (!on) {
           setComposer("llm");            // the only mode left
           setView((v) => (v === "arms" ? "clients" : v));
         }
       })
       .catch(() => setSelectorOn(true));
  }, []);

  useEffect(() => {
    if (!selected) { setDecision(null); setInsight(null); return; }
    if (selectorOn) {
      api.d1Decision(selected.client_id, reportType)
         .then(setDecision)
         .catch((e) => notify("Decision failed: " + e.message, "error"));
    } else {
      setDecision(null);
    }
    api.clientInsight(selected.client_id)
       .then((v) => { setInsight(v); setNote(v?.skill?.advisor_note || ""); })
       .catch(() => { setInsight(null); setNote(""); });
  }, [selected, reportType, selectorOn]);

  async function openClientView(reportId) {
    try {
      const r = await api.reportClientLink(reportId);
      window.open(r.url, "_blank", "noreferrer");
    } catch (e) { notify("Link failed: " + e.message, "error"); }
  }

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return clients;
    return clients.filter((c) =>
      [c.display_name, c.client_id, c.email, c.segment_id]
        .some((v) => (v || "").toLowerCase().includes(q)));
  }, [clients, query]);

  const segments = useMemo(() => {
    const m = {};
    clients.forEach((c) => {
      const s = c.segment_id || "unsegmented";
      (m[s] ||= { count: 0, reported: 0, value: 0 });
      m[s].count += 1;
      m[s].value += Number(c.portfolio_value || 0);
      if (c.last_report_id) m[s].reported += 1;
    });
    return m;
  }, [clients]);

  async function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const text = await f.text();
    setBusy(true);
    try {
      const r = await api.importClients({ csv_text: text });
      setImport({ ...r, fileName: f.name });
      await refreshAll();
      notify(`Imported ${r.imported} client${r.imported === 1 ? "" : "s"}`
             + (r.rejected.length ? `, ${r.rejected.length} rejected` : ""));
    } catch (err) {
      notify("Import failed: " + err.message, "error");
    } finally { setBusy(false); e.target.value = ""; }
  }

  async function generateOne(client) {
    setBusy(true);
    setStatus({ snapshot: "done", generate: "running" });
    try {
      const r = await api.generateOneReport({
        client_id: client.client_id, report_type: reportType,
        ...(period ? { period } : {}),
        ...(composer ? { composer } : {}) });
      setStatus({ snapshot: "done", generate: "done",
                  validate: r.validation === "passed" ? "passed" : "failed",
                  validation_summary: r.validation_summary,
                  validation_findings: r.validation_findings || [],
                  authors: r.authors || {},
                  method: r.method, arm: r.strategy,
                  blocks: r.blocks || [],
                  composer: r.composer || null,
                  review: "pending", email: "pending", report_id: r.report_id });
      await refreshAll();
      notify(`${client.display_name}: ${r.strategy}`);
      return r;
    } catch (e) {
      setStatus((s) => ({ ...s, generate: "failed" }));
      notify("Generation failed: " + e.message, "error");
    } finally { setBusy(false); }
  }

  async function generateAll() {
    if (!clients.length) return;
    setBusy(true);
    const arms = {};
    try {
      for (const c of clients) {
        const r = await api.generateOneReport({
          client_id: c.client_id, report_type: reportType,
          ...(period ? { period } : {}),
          ...(composer ? { composer } : {}) });
        arms[r.strategy] = (arms[r.strategy] || 0) + 1;
      }
      await refreshAll();
      setStatus({ snapshot: "done", generate: "done", validate: "passed",
                  validation_summary: "all blocks grounded",
                  review: "pending", email: "pending" });
      notify(`Generated ${clients.length} reports — `
             + Object.entries(arms).map(([k, v]) => `${k} ${v}`).join(", "));
    } catch (e) {
      notify("Batch failed: " + e.message, "error");
    } finally { setBusy(false); }
  }

  async function sendReport(reportId) {
    if (!reportId) return;
    setBusy(true);
    setStatus((st) => ({ ...st, email: "running" }));
    try {
      const r = await api.sendReport(reportId);
      setStatus((st) => ({ ...st, review: "done", email: "done", delivery: r }));
      notify(r.provider === "file"
        ? `Written to ${r.path.split(/[\/]/).pop()} — open it in a mail client`
        : `Sent to ${r.to} via ${r.provider}`);
    } catch (e) {
      setStatus((st) => ({ ...st, email: "failed" }));
      notify("Send failed: " + e.message, "error");
    } finally { setBusy(false); }
  }

  const armTemplates = templates.filter((t) => t.report_type === reportType);
  const maxExploit = Math.max(...(decision?.arms || []).map((a) => Math.abs(a.exploit)), 0.01);
  const selType = types.find((t) => t.report_type === reportType);

  return (
    <div className="adv">
      <aside className="adv-nav">
        <div className="adv-brand"><span className="adv-logo">APE</span> Advisor</div>
        <nav>
          {/* The arms page is the selector's own config surface. With
              selection off it edits machinery nothing consults, which is
              exactly the kind of nav item this app does not carry. */}
          {[["clients", "Clients"], ["reports", "Reports"],
            ["segments", "Segments"],
            ...(selectorOn ? [["arms", "Templates (Arms)"]] : [])
           ].map(([id, label]) => (
            <button key={id} className={`adv-nav-item ${view === id ? "on" : ""}`}
                    onClick={() => setView(id)}>{label}</button>
          ))}
          <a className="adv-nav-item" href="/admin">Configuration</a>
        </nav>
        <div className="adv-user">
          <b>Advisor Admin</b><span>admin@wealth.com</span>
        </div>
      </aside>

      <div className="adv-body">
        {/* ── toolbar: upload + report type + batch ─────────────── */}
        <header className="adv-bar">
          <input ref={fileRef} type="file" accept=".csv,text/csv"
                 onChange={onFile} style={{ display: "none" }} />
          <button className="adv-btn" disabled={busy}
                  onClick={() => fileRef.current?.click()}>
            Upload client CSV
          </button>

          <label className="adv-bar-lbl">Report type</label>
          <select value={reportType} onChange={(e) => setRt(e.target.value)}>
            {types.map((t) => (
              <option key={t.report_type} value={t.report_type}>
                {t.label}{t.personalisable === false ? "  (prescribed)" : ""}
              </option>
            ))}
          </select>

          {/* Two mutually exclusive modes, so a toggle rather than a
              select: both options stay visible, and which one is active
              is readable without opening anything. Hidden entirely when
              arm selection is switched off — a two-state control with one
              reachable state is not a control. */}
          {selectorOn && <label className="adv-bar-lbl">Template</label>}
          {selectorOn &&
          <div className="adv-toggle" role="group" aria-label="Template mode">
            {[["", "APE selects", "Learns from engagement"],
              ["llm", "AI composes", "One-off, teaches D1 nothing"]]
              .map(([value, label, hint]) => (
                <button
                  key={value || "ape"}
                  type="button"
                  title={hint}
                  aria-pressed={composer === value}
                  className={composer === value ? "on" : ""}
                  onClick={() => setComposer(value)}
                >{label}</button>
              ))}
          </div>}

          <label className="adv-bar-lbl">Period</label>
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            <option value="">Latest on file</option>
            {[...new Set(clients.flatMap((c) => c.periods || []))]
              .sort().reverse().map((per) => (
                <option key={per} value={per}>{per}</option>
              ))}
          </select>

          <button className="adv-btn ghost" disabled={busy || !clients.length}
                  onClick={generateAll}>
            Generate for all {clients.length || ""}
          </button>
          <span className="adv-bar-note">
            {!selectorOn
              ? "Arm selection is off in this environment — every report is "
                + "composed from the block registry."
              : <>
                  {composer === "llm"
                    ? "Composed layouts are one-offs — no arm to reward, so they teach APE nothing. "
                    : ""}
                  {selType?.personalisable === false
                    ? "Prescribed — mandated template, D1 not consulted"
                    : `${armTemplates.length} arms available`}
                </>}
          </span>
        </header>

        {importInfo && (
          <div className={`adv-import ${importInfo.rejected.length ? "warn" : "ok"}`}>
            <b>{importInfo.fileName}</b> — imported {importInfo.imported}
            {importInfo.rejected.length > 0 && (
              <>, <b>{importInfo.rejected.length} rejected</b>
                <ul>
                  {importInfo.rejected.map((r) => (
                    <li key={r.row}>Row {r.row} ({r.client_id}): {r.problems.join("; ")}</li>
                  ))}
                </ul>
              </>
            )}
            <button className="adv-x" onClick={() => setImport(null)}>×</button>
          </div>
        )}

        {/* ── CLIENTS ───────────────────────────────────────────── */}
        {view === "clients" && (
          <div className="adv-two">
            <section className="adv-panel">
              <div className="adv-panel-hd">
                <h2>Clients</h2><span className="adv-count">{clients.length}</span>
              </div>
              {clients.length === 0 ? (
                <div className="adv-empty-state">
                  <b>No clients yet</b>
                  <p>Upload a CSV — one row per client, with an email column and
                     that client's portfolio facts. Rows whose figures do not
                     reconcile are rejected rather than generated.</p>
                  <button className="adv-btn" onClick={() => fileRef.current?.click()}>
                    Upload client CSV
                  </button>
                </div>
              ) : (
                <>
                  <input className="adv-search" placeholder="Search clients…"
                         value={query} onChange={(e) => setQuery(e.target.value)} />
                  <table className="adv-table">
                    <thead><tr>
                      <th>Client</th><th>Segment</th><th>Last report</th><th></th>
                    </tr></thead>
                    <tbody>
                      {visible.map((c) => (
                        <tr key={c.client_id}
                            className={selected?.client_id === c.client_id ? "sel" : ""}
                            onClick={() => setSelected(c)}>
                          <td><b>{c.display_name}</b>
                              <div className="adv-sub">{c.email}</div></td>
                          <td>{(c.segment_id || "").replace(/_/g, " ")}</td>
                          <td>
                            {c.last_report_id
                              ? <><span className="adv-pill ok">{c.last_strategy}</span>
                                  <div className="adv-sub">{c.last_report_period}</div></>
                              : <span className="adv-pill wait">none</span>}
                          </td>
                          <td className="adv-row-actions">
                            <button className="adv-mini" disabled={busy}
                                    onClick={(e) => { e.stopPropagation(); generateOne(c); }}>
                              Generate
                            </button>
                            {c.last_report_id && (
                              <button className="adv-mini ghost"
                                      onClick={(e) => { e.stopPropagation(); setPreview(c.last_report_id); }}>
                                Preview
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>

            <div>
              {selectorOn && <section className="adv-panel">
                <div className="adv-panel-hd"><h2>APE decision (D1)</h2></div>
                {!decision ? <div className="adv-none">Select a client.</div> : (
                  <>
                    <div className="adv-d1">
                      <div className="adv-d1-hd">Selected arm</div>
                      <div className="adv-d1-arm">{decision.selected}</div>
                      <div className="adv-d1-method">via <b>{decision.method}</b></div>
                    </div>
                    <div className="adv-ctx">
                      <div><span>Client</span><b>{decision.client_name}</b></div>
                      <div><span>Segment</span><b>{(decision.segment_id || "").replace(/_/g, " ")}</b></div>
                      <div><span>Cell</span><code>{decision.cell_key}</code></div>
                    </div>
                    <div className="adv-sec-hd">Arms performance</div>
                    {decision.arms.map((a) => (
                      <div key={a.strategy} className="adv-bar-row">
                        <span>{a.label}</span>
                        {a.strategy === decision.selected && <em>selected</em>}
                        <i style={{ width: `${Math.max(3, (Math.abs(a.exploit) / maxExploit) * 100)}%`,
                                    background: a.strategy === decision.selected ? "#1d4ed8" : "#93c5fd" }} />
                        <b>{a.exploit.toFixed(2)}</b>
                      </div>
                    ))}
                  </>
                )}
              </section>}

              <section className="adv-panel">
                <div className="adv-panel-hd"><h2>What we've learned</h2></div>
                {!insight || insight.signals === 0 ? (
                  <div className="adv-none">
                    No preference dimension has moved off the population
                    prior yet. Dimensions shift on quality signals — a
                    rating, or a report marked unhelpful — not on opens and
                    highlights alone, so a client can have interaction
                    history here and still show none.
                  </div>
                ) : (
                  <>
                    <div className="adv-sub" style={{ marginBottom: 8 }}>
                      {insight.signals} meaningful signal{insight.signals === 1 ? "" : "s"}.
                      These dimensions shape how the next report is written —
                      never which facts it contains.
                    </div>
                    {Object.entries(insight.dimensions)
                      .filter(([, v]) => Math.abs(v - 0.5) > 0.02)
                      .sort((a, b) => Math.abs(b[1] - 0.5) - Math.abs(a[1] - 0.5))
                      .map(([dim, v]) => (
                        <div key={dim} className="adv-bar-row">
                          <span>{dim.replace(/_/g, " ")}</span>
                          <i style={{ width: `${Math.max(4, v * 100)}%`,
                                      background: v > 0.5 ? "#047857" : "#b45309" }} />
                          <b>{v.toFixed(2)}</b>
                        </div>
                      ))}
                    {insight.reports.filter((r) => r.engagement > 0).length > 0 && (
                      <>
                        <div className="adv-sec-hd">Report engagement</div>
                        {insight.reports.filter((r) => r.engagement > 0).map((r) => (
                          <div key={r.report_id} className="adv-step-row">
                            <span className="adv-step-name">{r.period}
                              <span className="adv-sub"> · {r.template_arm}</span></span>
                            <span className="adv-pill ok">
                              {Math.round(r.engagement * 100)}% engaged
                              · {r.questions} question{r.questions === 1 ? "" : "s"}
                            </span>
                          </div>
                        ))}
                      </>
                    )}
                  </>
                )}
              </section>

              <section className="adv-panel">
                <div className="adv-panel-hd">
                  <h2>Client skill</h2>
                  <span className="adv-sub">
                    {insight?.skill?.evidence_count || 0} interactions
                  </span>
                </div>
                <div className="adv-sub" style={{ marginBottom: 8 }}>
                  What this client's own behaviour has taught us, in words.
                  The AI composer reads this before designing their next
                  report. It shapes layout and wording only — never which
                  facts appear.
                </div>
                <pre className="adv-skill">
                  {insight?.skill?.brief || "No interaction history yet."}
                </pre>
                <div className="adv-sec-hd">Your own note</div>
                <div className="adv-sub" style={{ marginBottom: 6 }}>
                  Anything you write here takes precedence — you have met
                  this client, their click history has not.
                </div>
                <textarea
                  className="adv-skill-note"
                  value={note}
                  placeholder="e.g. Prefers one page. Skip the jargon — reads the fee line first."
                  onChange={(e) => setNote(e.target.value)}
                />
                <button
                  className="adv-btn"
                  disabled={!selected}
                  onClick={async () => {
                    try {
                      await api.setSkillNote(selected.client_id, note);
                      notify("Note saved — it will shape the next report.");
                    } catch (e) { notify("Save failed: " + e.message, "error"); }
                  }}
                >Save note</button>
              </section>

              <section className="adv-panel">
                <div className="adv-panel-hd"><h2>Report status</h2></div>
                {PIPELINE.map(([label, key]) => {
                  const v = status[key];
                  const cls = v === "done" || v === "passed" ? "ok"
                            : v === "failed" ? "bad" : v === "running" ? "run" : "wait";
                  const txt = v === "done" ? "Completed" : v === "passed" ? "Passed"
                            : v === "failed" ? "Failed" : v === "running" ? "Running…" : "Pending";
                  return (
                    <div key={key} className="adv-step-row">
                      <span className={`adv-dot ${cls}`} />
                      <span className="adv-step-name">{label}</span>
                      <span className={`adv-pill ${cls}`}>{txt}</span>
                    </div>
                  );
                })}
                {status.validation_summary && (
                  <div className="adv-sub" style={{ margin: "6px 0 10px" }}>
                    Grounding: {status.validation_summary}
                  </div>
                )}
                {status.method && (
                  <div className="adv-sub" style={{ margin: "0 0 8px" }}>
                    <b>{status.method === "llm_composed"
                        ? "AI composed this layout"
                        : `APE chose "${status.arm}" via ${status.method}`}</b>
                    {status.blocks?.length > 0 && (
                      <div style={{ marginTop: 3 }}>
                        {status.blocks.length} blocks: {status.blocks.join(" · ")}
                      </div>
                    )}
                    {status.composer?.reasoning && (
                      <div style={{ marginTop: 4, fontStyle: "italic" }}>
                        "{status.composer.reasoning}"
                      </div>
                    )}
                    {status.composer?.rejected?.length > 0 && (
                      <div style={{ marginTop: 4, color: "#b45309" }}>
                        ignored invalid block names:{" "}
                        {status.composer.rejected.join(", ")}
                      </div>
                    )}
                    {status.composer?.error && (
                      <div style={{ marginTop: 4, color: "#b91c1c" }}>
                        composer fell back — {status.composer.error}
                      </div>
                    )}
                  </div>
                )}
                {status.authors && Object.keys(status.authors).length > 0 && (
                  <div className="adv-sub" style={{ margin: "0 0 10px" }}>
                    Written by the model:{" "}
                    {Object.entries(status.authors).map(([bid, who]) => (
                      <span key={bid}
                            className={`adv-pill ${who.startsWith("llm") ? "arm" : "wait"}`}
                            style={{ marginRight: 4 }} title={who}>
                        {bid.replace(/_[0-9]+$/, "").replace(/_/g, " ")}
                        {who === "fallback" ? " (code)" : ""}
                      </span>
                    ))}
                  </div>
                )}
                {status.validation_findings?.length > 0 && (
                  <div className="adv-import warn" style={{ margin: "0 0 10px" }}>
                    <b>{status.validation_findings.length} block(s) dropped</b>
                    <ul>{status.validation_findings.slice(0, 5).map((f, i) => (
                      <li key={i}>{f.block_id}: {f.detail}</li>))}</ul>
                  </div>
                )}
                <div className="adv-actions">
                  <button className="adv-btn"
                          disabled={busy || status.generate !== "done"}
                          onClick={() => sendReport(status.report_id)}>
                    Approve &amp; send
                  </button>
                  {status.report_id && (
                    <>
                      <button className="adv-btn ghost"
                              onClick={() => setPreview(status.report_id)}>Preview</button>
                      <button className="adv-btn ghost"
                              onClick={() => openClientView(status.report_id)}>
                        Client view
                      </button>
                    </>
                  )}
                </div>
                {status.delivery && (
                  <div className="adv-delivery">
                    <b>{status.delivery.provider}</b> &middot; {status.delivery.status}
                    &middot; {status.delivery.to}
                    <a href={status.delivery.url} target="_blank" rel="noreferrer">
                      open the client link &rarr;
                    </a>
                    <div className="adv-sub">
                      This is the exact link the client receives. It carries a
                      signed token and expires.
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        )}

        {/* ── REPORTS ───────────────────────────────────────────── */}
        {view === "reports" && (
          <section className="adv-panel">
            <div className="adv-panel-hd">
              <h2>Generated reports</h2><span className="adv-count">{generated.length}</span>
            </div>
            {generated.length === 0
              ? <div className="adv-none">Nothing generated yet.</div>
              : (
                <table className="adv-table">
                  <thead><tr>
                    <th>Report</th><th>Client</th><th>Arm</th><th>Blocks</th>
                    <th>Email</th><th></th>
                  </tr></thead>
                  <tbody>
                    {generated.map((r) => (
                      <tr key={r.report_id}>
                        <td><code className="adv-code">{r.report_id}</code>
                            <div className="adv-sub">{r.report_type?.replace(/_/g, " ")}</div></td>
                        <td><b>{r.client_name}</b><div className="adv-sub">{r.email}</div></td>
                        <td><span className="adv-pill arm">{r.strategy}</span></td>
                        <td className="adv-blocks">{(r.blocks || []).join(" · ")}</td>
                        <td><span className="adv-pill ok">{r.email_status}</span></td>
                        <td className="adv-row-actions">
                          <button className="adv-mini" onClick={() => setPreview(r.report_id)}>Preview</button>
                          <button className="adv-mini" onClick={() => openClientView(r.report_id)}>
                            Client view
                          </button>
                          <button className="adv-mini ghost" disabled={busy}
                                  onClick={() => sendReport(r.report_id)}>Send</button>
                          <a className="adv-mini ghost" href={`/reports/${r.report_id}/json`}
                             target="_blank" rel="noreferrer">JSON</a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </section>
        )}

        {/* ── SEGMENTS ──────────────────────────────────────────── */}
        {view === "segments" && (
          <section className="adv-panel">
            <div className="adv-panel-hd">
              <h2>Segments</h2>
              <span className="adv-count">{Object.keys(segments).length}</span>
            </div>
            <p className="adv-note">
              Segments come from the CSV's <code>segment_id</code> column. They
              are the middle prior in D1 — a new client with no history of their
              own is served their segment's shape rather than the whole book's.
            </p>
            {Object.keys(segments).length === 0
              ? <div className="adv-none">Upload a CSV to populate segments.</div>
              : (
                <table className="adv-table">
                  <thead><tr>
                    <th>Segment</th><th>Clients</th><th>Reported</th><th>Total value</th>
                  </tr></thead>
                  <tbody>
                    {Object.entries(segments).map(([s, v]) => (
                      <tr key={s}>
                        <td><b>{s.replace(/_/g, " ")}</b></td>
                        <td>{v.count}</td>
                        <td>{v.reported} / {v.count}</td>
                        <td>£{v.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </section>
        )}

        {/* ── ARMS ──────────────────────────────────────────────── */}
        {view === "arms" && (
          <section className="adv-panel">
            <div className="adv-panel-hd">
              <h2>Template arms — {selType?.label}</h2>
              <span className="adv-count">{armTemplates.length}</span>
            </div>
            <p className="adv-note">
              The arms D1 chooses between for this report type. Edit them under
              <a href="/admin"> Configuration → Templates</a>.
            </p>
            <table className="adv-table">
              <thead><tr><th>Arm</th><th>Label</th><th>Blocks</th></tr></thead>
              <tbody>
                {armTemplates.map((t) => (
                  <tr key={t.template_id}>
                    <td><span className="adv-pill arm">{t.strategy}</span></td>
                    <td><b>{t.label}</b><div className="adv-sub">{t.description}</div></td>
                    <td className="adv-blocks">{(t.required_blocks || []).join(" · ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>

      {preview && (
        <div className="adv-modal" onClick={() => setPreview(null)}>
          <div className="adv-modal-inner" onClick={(e) => e.stopPropagation()}>
            <div className="adv-modal-bar">
              <b>{preview}</b>
              <a href={`/reports/${preview}/html`} target="_blank" rel="noreferrer">open</a>
              <a href={`/reports/${preview}/json`} target="_blank" rel="noreferrer">json</a>
              <button onClick={() => setPreview(null)}>Close</button>
            </div>
            <iframe title="report" src={`/reports/${preview}/html`} />
          </div>
        </div>
      )}

      <Toast message={toast.msg} kind={toast.kind}
             onClose={() => setToast({ msg: null, kind: "" })} />
    </div>
  );
}
