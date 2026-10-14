import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api.js";
import Toast from "../components/Toast.jsx";
import NotificationBell from "../components/NotificationBell.jsx";
import AppRail, { NAV } from "../components/AppRail.jsx";
const TemplateGallery = lazy(() => import("../components/TemplateGallery.jsx"));
import { BlockTree, PreferenceTree, SignalTree, TemplateTree }
  from "../components/RegistryTree.jsx";
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

// "balanced_growth" -> "Balanced growth": identifiers are for the system,
// sentence case is for people.
const ACRONYMS = new Set(["esg", "uk", "us", "eu", "etf", "ucb", "isa", "sipp", "pdf", "json"]);
function humanise(id) {
  const t = String(id || "").replace(/_/g, " ").trim()
    .split(" ").map((w) => ACRONYMS.has(w.toLowerCase()) ? w.toUpperCase() : w).join(" ");
  return t ? t[0].toUpperCase() + t.slice(1) : "";
}

// Delivery, as recorded when the report was actually sent. A report that
// has only been generated has not been emailed to anyone, and says so.
function emailLabel(st) {
  const v = String(st || "").toLowerCase();
  if (v === "sent") return "Sent";
  if (v === "written") return "Saved to file";
  if (["failed", "bounced", "error"].includes(v)) return "Failed";
  return "Not sent";
}

// Delivery state, as a tone the status pills understand.
function emailTone(st) {
  const v = String(st || "").toLowerCase();
  if (["sent", "delivered", "opened"].includes(v)) return "ok";
  if (["failed", "bounced", "error"].includes(v)) return "bad";
  if (["queued", "sending"].includes(v)) return "run";
  return "muted";
}

// Secondary row actions live behind one "more" control, so a long table
// keeps a single visible action per row and its columns stay readable.
function RowMenu({ label, items }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close);
                   document.removeEventListener("keydown", esc); };
  }, [open]);
  return (
    <span className="adv-menu" ref={ref}>
      <button type="button" className="adv-mini ghost adv-menu-btn" aria-label={label}
              aria-haspopup="menu" aria-expanded={open}
              onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}>
        <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
          <circle cx="3" cy="8" r="1.4" /><circle cx="8" cy="8" r="1.4" /><circle cx="13" cy="8" r="1.4" />
        </svg>
      </button>
      {open && (
        <div className="adv-menu-list" role="menu">
          {items.map((it) => it.href
            ? <a key={it.label} role="menuitem" href={it.href} target="_blank" rel="noreferrer"
                 onClick={() => setOpen(false)}>{it.label}</a>
            : <button key={it.label} type="button" role="menuitem" disabled={it.disabled}
                      onClick={(e) => { e.stopPropagation(); setOpen(false); it.onClick(); }}>
                {it.label}</button>)}
        </div>
      )}
    </span>
  );
}

export default function AdvisorPage() {
  // Configuration links back here naming the view to open.
  const location = useLocation();
  const [view, setView]         = useState(location.state?.view || "clients");
  const [clients, setClients]   = useState([]);
  const [query, setQuery]       = useState("");
  const [selected, setSelected] = useState(null);
  const [types, setTypes]       = useState([]);
  const [templates, setTemplates] = useState([]);
  const [reportType, setRt]     = useState("quarterly_portfolio_review");
  const [status, setStatus]     = useState({});
  const [generated, setGenerated] = useState([]);
  const [busy, setBusy]         = useState(false);
  const [importInfo, setImport] = useState(null);
  const [preview, setPreview]   = useState(null);
  const [period, setPeriod]     = useState("");        // "" = latest on file
  // English is the standing default, never inferred. Picking a country
  // preselects that country's language, but the advisor can still change
  // it — a Dutch client who wants English reporting is common.
  const [country,  setCountry]  = useState("GB");
  const [language, setLanguage] = useState("en");
  const [locales,  setLocales]  = useState({ countries: [], languages: [] });
  const [insight, setInsight]   = useState(null);
  const [note, setNote]         = useState("");
  // The template the advisor picked for this report type. "" means the
  // AI composes one instead — those are the only two routes now.
  const [templateId, setTemplateId] = useState("");
  // A template handed over from the gallery, applied once it is listed.
  const pendingTpl = useRef(null);
  // The three registries, loaded on demand: nothing needs them until
  // the advisor opens the view.
  const [reg, setReg] = useState({ blocks: null, templates: null, prefs: null, signals: null });
  const [regTab, setRegTab] = useState("templates");
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
  // Failing to load these must not block generation: the payload still
  // carries the current country/language, and the backend defaults to
  // English on its own.
  useEffect(() => {
    api.listLocales()
       .then(setLocales)
       .catch(() => setLocales({ countries: [], languages: [] }));
  }, []);

  useEffect(() => {
    if (!selected) { setInsight(null); return; }
    api.clientInsight(selected.client_id)
       .then((v) => { setInsight(v); setNote(v?.skill?.advisor_note || ""); })
       .catch(() => { setInsight(null); setNote(""); });
  }, [selected, reportType]);



  // Templates belong to one report type, so a pick cannot survive a change
  // of type. Defaults to the first authored template where one exists, so
  // the common case needs no interaction at all.
  useEffect(() => {
    const mine = templates.filter((t) => t.report_type === reportType);
    if (pendingTpl.current && mine.some((t) => t.template_id === pendingTpl.current)) {
      setTemplateId(pendingTpl.current);
      pendingTpl.current = null;
      return;
    }
    setTemplateId((cur) =>
      mine.some((t) => t.template_id === cur) ? cur
        : (mine.length ? mine[0].template_id : ""));
  }, [reportType, templates]);

  useEffect(() => {
    if (view !== "registry") return;
    Promise.all([api.registryTemplates(), api.registryBlocks(),
                 api.registryPreferences(), api.registrySignals()])
      .then(([t, b, pr, sg]) =>
        setReg({ templates: t, blocks: b, prefs: pr, signals: sg }))
      .catch((e) => notify("Registry load failed: " + e.message, "error"));
  }, [view]);

  // The report a client row should be showing RIGHT NOW, for the report
  // type and period currently selected in the toolbar.
  //
  // The row used to show `last_report_id` — the client's most recent report
  // of any type from any period — so changing either selector left the row
  // unchanged and Preview opened a document from a different quarter. The
  // toolbar is a filter; a row that ignores it is showing something else.
  const reportFor = useMemo(() => {
    const idx = {};
    generated.forEach((r) => {
      if (r.report_type !== reportType) return;
      (idx[r.client_id] ||= []).push(r);
    });
    Object.values(idx).forEach((rs) =>
      rs.sort((a, b) => String(b.period).localeCompare(String(a.period))));
    return (clientId) => {
      const rs = idx[clientId] || [];
      // "" = latest on file, which for a filter means the newest of THIS
      // report type — not the newest of anything.
      return period ? rs.find((r) => r.period === period) : rs[0];
    };
  }, [generated, reportType, period]);

  // The status panel follows the SELECTED CLIENT, not whatever ran last.
  //
  // It used to be written only by the generate handlers, so two things went
  // wrong at once. A batch run set a finished-looking pipeline with no
  // report_id — there are thirteen ids, not one — which left "Approve &
  // send" enabled and completely inert, because sendReport() begins with
  // `if (!reportId) return`. And selecting a different client never cleared
  // it, so that green pipeline stayed on screen describing somebody else's
  // report.
  //
  // A pipeline that says Passed while its button does nothing is worse than
  // an empty panel: the advisor believes the report went out.
  useEffect(() => {
    if (busy) return;                 // a run in progress owns the panel
    if (!selected) { setStatus({}); return; }
    const r = reportFor(selected.client_id);
    if (!r) { setStatus({}); return; }
    // ALREADY DESCRIBING THIS REPORT? Leave it alone.
    //
    // This effect re-runs the moment `busy` flips back to false, which is
    // exactly when generateOne and sendReport finish. Anything it writes
    // then replaces a fresher, richer status with one rebuilt from the
    // report row — losing the block list, the authors, the findings and
    // the delivery panel, and briefly the report_id along with them.
    //
    // The row-derived status is a FALLBACK for a client whose report was
    // made earlier or elsewhere. When the panel is already about this
    // report, whatever put it there knew more than we do.
    if (status.report_id === r.report_id) return;
    // UNKNOWN IS NOT PASSED.
    //
    // /reports/generated carries no `validation` and no `sent_at`. The
    // first version of this treated a missing validation as "passed",
    // which painted a green "Validation (grounding): Passed" for a report
    // nothing had checked in this session — an unfounded green of exactly
    // the kind the pipeline exists to avoid.
    //
    // Delivery is different: `email_status` and `sent_at` now come from the
    // record /send writes when an email actually goes out, so a "sent" here
    // is a fact, not a placeholder. Anything else stays Pending.
    //
    // A report opened from the list therefore shows what the row really
    // supports — it exists, it was generated, and whether it was sent.
    setStatus({
      snapshot: "done",
      generate: "done",
      validate: r.validation === "passed" ? "passed"
              : r.validation === "rejected_blocks" ? "caught"
              : r.validation === "failed" ? "failed"
              : "pending",
      validation_summary: r.validation === "rejected_blocks"
        ? "an unsourced figure was caught and replaced"
        : r.validation === "passed" ? "all blocks grounded"
        : "",
      review: r.email_status === "sent" ? "done" : "pending",
      email: r.email_status === "sent" ? "done" : "pending",
      report_id: r.report_id,
    });
  }, [selected, reportFor, busy, status.report_id]);

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
    // Generating for a client SELECTS them.
    //
    // The row's Generate button calls stopPropagation so the click does not
    // also count as selecting the row — which left the status panel
    // describing whoever happened to be selected before. Once the panel
    // started following the selection, that mismatch became visible in the
    // worst way: the freshly generated result was overwritten a moment
    // later, taking report_id with it, so "Approve & send" vanished the
    // instant generation finished.
    //
    // The panel should describe the client you just acted on. Selecting
    // here says that once, rather than teaching the effect a special case.
    setSelected(client);
    setBusy(true);
    setStatus({ snapshot: "done", generate: "running" });
    try {
      const r = await api.generateOneReport({
        client_id: client.client_id, report_type: reportType,
        ...(period ? { period } : {}),
        ...(templateId ? { template_id: templateId } : { composer: "llm" }),
        country, language });
      setStatus({ snapshot: "done", generate: "done",
                  // Three outcomes, not two. "rejected_blocks" means the
                  // gate CAUGHT an ungrounded draft and the code-built
                  // block was used instead — the report is still fully
                  // grounded, so calling that "Failed" reads as a broken
                  // report when it is the safety net doing its job.
                  // A genuine failure is generation erroring, which lands
                  // in the catch below.
                  validate: r.validation === "passed" ? "passed"
                          : r.validation === "rejected_blocks" ? "caught"
                          : "failed",
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
          ...(templateId ? { template_id: templateId } : { composer: "llm" }),
        country, language });
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
      // The report can be finished and approved while the EMAIL fails —
      // an unauthorised mail provider, most often. Saying "done" then
      // would tell an advisor their client had been written to when
      // nobody had, which is the one outcome worth being careful about.
      if (r.sent === false) {
        setStatus((st) => ({ ...st, review: "done", email: "failed", delivery: r }));
        notify(`Not emailed — ${r.remedy || r.error}. The link below still works.`,
               "error");
      } else {
        setStatus((st) => ({ ...st, review: "done", email: "done", delivery: r }));
        notify(r.provider === "file"
          ? `Written to ${r.path.split(/[\/]/).pop()} — open it in a mail client`
          : `Sent to ${r.to} via ${r.provider}`);
      }
    } catch (e) {
      setStatus((st) => ({ ...st, email: "failed" }));
      notify("Send failed: " + e.message, "error");
    } finally { setBusy(false); }
  }

  const armTemplates = templates.filter((t) => t.report_type === reportType);
  const selType = types.find((t) => t.report_type === reportType);

  return (
    <div className="adv">
      <AppRail active={view} onSelect={setView} />

      <div className="adv-body">
        {/* ── page header: where you are, and the two book-wide actions ── */}
        <header className="adv-head">
          <div className="adv-head-title">
            <h1>{(NAV.find(([id]) => id === view) || ["", "Clients"])[1]}</h1>
            <p>{view === "templates"
                 ? "Every report layout available, previewed with fictional demo data"
                 : view === "reports"
                 ? `${generated.length} report${generated.length === 1 ? "" : "s"} generated`
                 : view === "segments"
                 ? `${Object.keys(segments).length} segments across ${clients.length} clients`
                 : view === "registry"
                 ? "What the system can build, and what it has learned"
                 : clients.length
                 ? `${clients.length} client${clients.length === 1 ? "" : "s"} on file`
                 : "No clients imported yet"}</p>
          </div>
          <div className="adv-head-actions">
            {view === "clients" && <>
            <input ref={fileRef} type="file" accept=".csv,text/csv"
                   onChange={onFile} style={{ display: "none" }} />
            <button className="adv-btn ghost" disabled={busy}
                    onClick={() => fileRef.current?.click()}>
              Upload client CSV
            </button>
            <button className="adv-btn" disabled={busy || !clients.length}
                    onClick={generateAll}>
              Generate for all{clients.length ? ` ${clients.length}` : ""}
            </button>
            </>}
            {/* Pinned right by `margin-left:auto` on .nb-wrap, so it stays
                in the corner even when the controls beside it wrap. */}
            <NotificationBell />
          </div>
        </header>

        {/* ── report settings: what the next generation will produce ── */}
        {view === "clients" && <section className="adv-bar" aria-label="Report settings">
          <div className="adv-fg">
            <label className="adv-bar-lbl" htmlFor="f-rt">Report type</label>
            <select id="f-rt" value={reportType} onChange={(e) => setRt(e.target.value)}>
              {types.map((t) => (
                <option key={t.report_type} value={t.report_type}>
                  {t.label}{t.personalisable === false ? "  (prescribed)" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* One control, listing every template authored for this
              report type plus the composer. No bandit is involved: the
              advisor picks, or the model builds one. Templates are per
              report type because their blocks assume that type's facts,
              so the list changes with the type above it. */}
          <div className="adv-fg">
            <label className="adv-bar-lbl" htmlFor="f-tpl">Template</label>
            <select id="f-tpl" value={templateId}
                    onChange={(e) => setTemplateId(e.target.value)}>
              {armTemplates.map((t) => (
                <option key={t.template_id} value={t.template_id}>
                  {t.label || t.strategy}
                  {t.required_blocks?.length
                    ? `  (${t.required_blocks.length} blocks)` : ""}
                </option>
              ))}
              <option value="">AI composes a new one</option>
            </select>
          </div>

          <div className="adv-fg">
            <label className="adv-bar-lbl" htmlFor="f-per">Period</label>
            <select id="f-per" value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="">Latest on file</option>
              {[...new Set(clients.flatMap((c) => c.periods || []))]
                .sort().reverse().map((per) => (
                  <option key={per} value={per}>{per}</option>
                ))}
            </select>
          </div>

          {/* Country preselects a language; the advisor can still override.
              Auto-selection that could not be overridden would be worse
              than none — Belgium alone reads two languages. */}
          <div className="adv-fg">
            <label className="adv-bar-lbl" htmlFor="f-cty">Country</label>
            <select id="f-cty" value={country} onChange={(e) => {
                      const c = e.target.value;
                      setCountry(c);
                      const row = (locales.countries || [])
                                    .find((x) => x.code === c);
                      if (row) setLanguage(row.language);
                    }}>
              {(locales.countries || []).map((c) => (
                <option key={c.code} value={c.code}>{c.label}</option>
              ))}
            </select>
          </div>

          <div className="adv-fg">
            <label className="adv-bar-lbl" htmlFor="f-lang">Language</label>
            <select id="f-lang" value={language}
                    onChange={(e) => setLanguage(e.target.value)}>
              {(locales.languages || []).map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}{l.code !== "en" ? "  (" + l.endonym + ")" : ""}
                </option>
              ))}
            </select>
          </div>

          <p className="adv-bar-note">
            {templateId
              ? `${armTemplates.length} template`
                + `${armTemplates.length === 1 ? "" : "s"} for this report type.`
                + ` Edit them under Configuration.`
              : "The model designs a layout from the block registry, "
                + "guided by what this client has asked for."}
          </p>
        </section>}

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
                      <th>Client</th><th>Segment</th><th>Last report</th>
                      <th className="adv-th-actions"><span className="sr-only">Actions</span></th>
                    </tr></thead>
                    <tbody>
                      {visible.map((c) => (
                        <tr key={c.client_id}
                            className={selected?.client_id === c.client_id ? "sel" : ""}
                            onClick={() => setSelected(c)}>
                          <td><span className="adv-name">{c.display_name}</span>
                              <div className="adv-sub">{c.email}</div></td>
                          <td className="adv-nowrap">{humanise(c.segment_id)}</td>
                          <td>
                            {(() => {
                              const rep = reportFor(c.client_id);
                              // A template name is a label, not a status, so it
                              // is shown as plain text with its period, never in
                              // a coloured "success" chip.
                              return rep
                                ? <><span className="adv-cell-main" title={rep.label || rep.strategy}>
                                      {rep.label || rep.strategy}</span>
                                    <div className="adv-sub">{rep.period}</div></>
                                : <span className="adv-sub">
                                    {period ? `None for ${period}` : "Not generated"}
                                  </span>;
                            })()}
                          </td>
                          <td className="adv-row-actions">
                            <button className="adv-mini ghost" disabled={busy}
                                    onClick={(e) => { e.stopPropagation(); generateOne(c); }}>
                              Generate
                            </button>
                            {(() => {
                              const rep = reportFor(c.client_id);
                              return rep ? (
                                <button className="adv-mini link"
                                        title={`${rep.period} · ${rep.label || rep.strategy}`}
                                        onClick={(e) => { e.stopPropagation();
                                                          setPreview(rep.report_id); }}>
                                  Preview
                                </button>
                              ) : null;
                            })()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>

            <div>
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
                          <span>{humanise(dim)}</span>
                          <i style={{ width: `${Math.max(4, v * 100)}%`,
                                      background: v > 0.5 ? "var(--accent-active)" : "var(--line-strong)" }} />
                          <b>{v.toFixed(2)}</b>
                        </div>
                      ))}
                    {insight.reports.filter((r) => r.engagement > 0).length > 0 && (
                      <>
                        <div className="adv-sec-hd">Report engagement</div>
                        {insight.reports.filter((r) => r.engagement > 0).map((r) => (
                          <div key={r.report_id} className="adv-step-row">
                            <span className="adv-step-name">{r.period}
                              <span className="adv-sub"> · {humanise(r.template_arm)}</span></span>
                            <span className="adv-pill muted">
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
                            : v === "caught" ? "warn"
                            : v === "failed" ? "bad" : v === "running" ? "run" : "wait";
                  const txt = v === "done" ? "Completed" : v === "passed" ? "Passed"
                            : v === "caught" ? "Caught an unsourced figure"
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
                      <div style={{ marginTop: 4, color: "var(--warn)" }}>
                        ignored invalid block names:{" "}
                        {status.composer.rejected.join(", ")}
                      </div>
                    )}
                    {status.composer?.error && (
                      <div style={{ marginTop: 4, color: "var(--neg)" }}>
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
                    {status.delivery.sent === false && (
                      <div className="adv-import warn" style={{ margin: "8px 0 0" }}>
                        <b>The email did not go out.</b> {status.delivery.remedy}
                        <div className="adv-sub" style={{ marginTop: 4 }}>
                          {status.delivery.error}
                        </div>
                      </div>
                    )}
                    <div className="adv-sub">
                      {status.delivery.sent === false
                        ? "The report and this link are ready — you can send the link yourself."
                        : "This is the exact link the client receives. It carries a signed token and expires."}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        )}

        {/* ── TEMPLATES ─────────────────────────────────────────── */}
        {view === "templates" && (
          <div className="tg-wrap">
            <Suspense fallback={<section className="adv-panel"><div className="adv-none">Loading…</div></section>}>
              <TemplateGallery onUse={(t) => {
                pendingTpl.current = t.template_id;
                setRt(t.report_type);
                setTemplateId(t.template_id);
                setView("clients");
                notify(`"${t.label}" selected. Pick a client and generate.`);
              }} />
            </Suspense>
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
                    <th>Report</th><th>Client</th><th>Template</th>
                    <th>Email</th>
                    <th className="adv-th-actions"><span className="sr-only">Actions</span></th>
                  </tr></thead>
                  <tbody>
                    {generated.map((r) => (
                      <tr key={r.report_id}>
                        <td title={r.report_id}><span className="adv-name">{humanise(r.report_type)}</span>
                            <div className="adv-sub">{r.period}</div></td>
                        <td><span className="adv-name">{r.client_name}</span><div className="adv-sub">{r.email}</div></td>
                        <td><span className="adv-cell-main" title={r.label || r.strategy}>{r.label || humanise(r.strategy)}</span>
                            <div className="adv-sub" title={(r.blocks || []).join(" · ")}>
                              {(r.blocks || []).length} blocks</div></td>
                        <td><span className={`adv-pill ${emailTone(r.email_status)}`}>
                          {emailLabel(r.email_status)}</span>
                            {r.sent_at && <div className="adv-sub">
                              {new Date(r.sent_at + (r.sent_at.endsWith("Z") ? "" : "Z"))
                                .toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
                            </div>}</td>
                        <td className="adv-row-actions">
                          <button className="adv-mini ghost" onClick={() => setPreview(r.report_id)}>Preview</button>
                          <RowMenu label={`More actions for ${r.client_name}`} items={[
                            { label: "Open client view", onClick: () => openClientView(r.report_id) },
                            { label: "Send to client", disabled: busy, onClick: () => sendReport(r.report_id) },
                            { label: "Download JSON", href: `/reports/${r.report_id}/json` },
                            { label: "Copy report ID", onClick: () => navigator.clipboard?.writeText(r.report_id)
                                .then(() => notify(`Copied ${r.report_id}`)) },
                          ]} />
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
              Segments come from the <code>segment_id</code> column of the client
              CSV. A new client with no history of their own starts from their
              segment's preferences rather than the whole book's.
            </p>
            {Object.keys(segments).length === 0
              ? <div className="adv-none">Upload a CSV to populate segments.</div>
              : (
                <table className="adv-table">
                  <thead><tr>
                    <th>Segment</th><th className="num">Clients</th>
                    <th className="num">Reported</th><th className="num">Total value</th>
                  </tr></thead>
                  <tbody>
                    {Object.entries(segments).map(([s, v]) => (
                      <tr key={s}>
                        <td><span className="adv-name">{humanise(s)}</span></td>
                        <td className="num">{v.count}</td>
                        <td className="num">{v.reported} / {v.count}</td>
                        <td className="num">£{v.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </section>
        )}

        {/* ── ARMS ──────────────────────────────────────────────── */}
        {view === "registry" && (
          <section className="adv-panel">
            <div className="reg-tabs" role="tablist">
              {[["templates", "Templates by report type"],
                ["blocks", "Widget registry"],
                ["prefs", "Learned preferences"],
                ["signals", "Signals received"]].map(([id, label]) => (
                <button key={id} type="button" role="tab" aria-selected={regTab === id}
                        className={regTab === id ? "on" : ""}
                        onClick={() => setRegTab(id)}>{label}</button>
              ))}
            </div>

            {regTab === "templates" && (<>
              <p className="adv-note">
                A template belongs to exactly one report type, because its
                blocks assume that type's facts. Each one is an ordered list
                drawn from the widget registry. You choose which one to use when
                you generate. Read-only here; edit templates under Configuration.
              </p>
              {reg.templates ? <TemplateTree data={reg.templates} />
                             : <div className="adv-none">Loading…</div>}
            </>)}

            {regTab === "blocks" && (<>
              <p className="adv-note">
                Every widget a template or the composer can use, grouped by the
                fact category it covers. Coverage is enforced per category, so
                two blocks in the same group close the same gap.
              </p>
              {reg.blocks ? <BlockTree data={reg.blocks} />
                          : <div className="adv-none">Loading…</div>}
            </>)}

            {regTab === "prefs" && (<>
              <p className="adv-note">
                What has been learned, per client and per report type. Only
                scopes with real evidence are listed. “(all report types)” is
                the client-wide row a report type falls back on before it has
                history of its own.
              </p>
              {reg.prefs ? <PreferenceTree data={reg.prefs} />
                         : <div className="adv-none">Loading…</div>}
            </>)}

            {regTab === "signals" && (<>
              <p className="adv-note">
                Every signal a client has given, exactly as it was recorded.
                The tab beside this one shows what was CONCLUDED; this shows
                what was OBSERVED — the only way to check a conclusion is to
                see the clicks behind it. The coloured tag is the weight the
                system gives each class: quality verdicts count for far more
                than an open.
              </p>
              {reg.signals ? <SignalTree data={reg.signals} />
                           : <div className="adv-none">Loading…</div>}
            </>)}
          </section>
        )}

      </div>

      {preview && (
        <div className="adv-modal" onClick={() => setPreview(null)}
             onKeyDown={(e) => { if (e.key === "Escape") setPreview(null); }}>
          <div className="adv-modal-inner" role="dialog" aria-modal="true"
               aria-label="Report preview" onClick={(e) => e.stopPropagation()}>
            <div className="adv-modal-bar">
              <div className="adv-modal-title">
                <b>Report preview</b>
                <span title={preview}>{(() => {
                  const r = generated.find((g) => g.report_id === preview);
                  return r ? `${r.client_name} · ${humanise(r.report_type)} · ${r.period}` : preview;
                })()}</span>
              </div>
              <a href={`/reports/${preview}/html`} target="_blank" rel="noreferrer">Open in new tab</a>
              <a href={`/reports/${preview}/json`} target="_blank" rel="noreferrer">Download JSON</a>
              <button className="adv-mini ghost" autoFocus onClick={() => setPreview(null)}>Close</button>
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
