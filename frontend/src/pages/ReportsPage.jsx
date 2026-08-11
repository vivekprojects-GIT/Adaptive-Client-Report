import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Toast from "../components/Toast.jsx";
import "../styles/app-shell.css";
import "../styles/admin.css";
import "../styles/reports.css";

export default function ReportsPage() {
  const [types, setTypes]       = useState([]);
  const [reportType, setRt]     = useState("quarterly_portfolio_review");
  const [csvText, setCsvText]   = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult]     = useState(null);
  const [existing, setExisting] = useState([]);
  const [busy, setBusy]         = useState(false);
  const [preview, setPreview]   = useState(null);
  const [toast, setToast]       = useState({ msg: null, kind: "" });
  const fileRef = useRef(null);

  const notify = (msg, kind = "ok") => setToast({ msg, kind });

  useEffect(() => {
    (async () => {
      try {
        setTypes(await api.listReportTypes());
        setExisting(await api.listGeneratedReports());
      } catch (e) { notify("Load failed: " + e.message, "error"); }
    })();
  }, []);

  const selectedType = useMemo(
    () => types.find((t) => t.report_type === reportType),
    [types, reportType]
  );

  function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFileName(f.name);
    const r = new FileReader();
    r.onload = () => setCsvText(String(r.result || ""));
    r.readAsText(f);
  }

  const rowCount = useMemo(() => {
    const lines = csvText.trim().split(/\r?\n/).filter(Boolean);
    return Math.max(0, lines.length - 1);
  }, [csvText]);

  async function generate() {
    if (!csvText.trim()) { notify("Upload a CSV first", "error"); return; }
    setBusy(true); setResult(null); setPreview(null);
    try {
      const r = await api.generateReports({ csv_text: csvText, report_type: reportType });
      setResult(r);
      setExisting(await api.listGeneratedReports());
      notify(`Generated ${r.generated} report${r.generated === 1 ? "" : "s"}`);
    } catch (e) {
      notify("Generation failed: " + e.message, "error");
    } finally { setBusy(false); }
  }

  const rows = result?.results ?? [];

  return (
    <div className="app-page">
      <header className="app-header">
        <div className="app-header-row">
          <div className="app-brand">
            <span className="app-brand-name">APE</span>
            <span className="app-brand-dot">/</span>
            <span className="app-brand-page">Client Reporting</span>
          </div>
          <div className="app-actions">
            <Link to="/admin"     className="app-link">Configuration</Link>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="rp-grid">
          {/* ---- left: run a batch ---- */}
          <div>
            <div className="admin-section">
              <h2 className="admin-section-title">1 &middot; Report type</h2>
              <p className="admin-section-sub">
                Selected, not inferred. This is D1's decision context — it decides
                which template arms are eligible.
              </p>
              <select value={reportType} onChange={(e) => setRt(e.target.value)}>
                {types.map((t) => (
                  <option key={t.report_type} value={t.report_type}>
                    {t.label}{t.personalisable === false ? "  (prescribed)" : ""}
                  </option>
                ))}
              </select>
              {selectedType && (
                <div className="rp-note">
                  {selectedType.personalisable === false
                    ? <><b>Prescribed.</b> Format is set by regulation — the single
                        mandated template is served and D1 never runs.</>
                    : <>{selectedType.notes}</>}
                </div>
              )}
            </div>

            <div className="admin-section">
              <h2 className="admin-section-title">2 &middot; Client data</h2>
              <p className="admin-section-sub">
                One row per client. Each row carries the delivery email and that
                client's frozen portfolio facts for the period.
              </p>
              <div className="rp-drop" onClick={() => fileRef.current?.click()}>
                <input ref={fileRef} type="file" accept=".csv,text/csv"
                       onChange={onFile} style={{ display: "none" }} />
                {fileName
                  ? <><b>{fileName}</b><span>{rowCount} client row{rowCount === 1 ? "" : "s"}</span></>
                  : <><b>Choose a CSV</b><span>client_id, email, portfolio_value, alloc_*, attr_* …</span></>}
              </div>
            </div>

            <div className="admin-section">
              <h2 className="admin-section-title">3 &middot; Generate</h2>
              <button className="btn-primary" onClick={generate}
                      disabled={busy || !csvText.trim()}>
                {busy ? "Generating…" : `Generate ${rowCount || ""} report${rowCount === 1 ? "" : "s"}`}
              </button>
              <div className="rp-note">
                Email is <b>stubbed</b> — reports are generated and marked sent,
                but nothing is dispatched.
              </div>
            </div>
          </div>

          {/* ---- right: results ---- */}
          <div>
            {result?.rejected?.length > 0 && (
              <div className="admin-section rp-reject">
                <h2 className="admin-section-title">
                  Rejected rows ({result.rejected.length})
                </h2>
                <p className="admin-section-sub">
                  Not generated. A row whose figures do not reconcile would produce
                  a report that looks correct and is wrong.
                </p>
                {result.rejected.map((r) => (
                  <div key={r.row} className="rp-reject-row">
                    <b>Row {r.row} — {r.client_id}</b>
                    <ul>{r.problems.map((p, i) => <li key={i}>{p}</li>)}</ul>
                  </div>
                ))}
              </div>
            )}

            {result && (
              <div className="admin-section">
                <h2 className="admin-section-title">
                  Arm distribution
                  <span className="rp-cell">{result.cell_key}</span>
                </h2>
                <div className="rp-dist">
                  {Object.entries(result.arm_distribution).map(([arm, n]) => {
                    const max = Math.max(...Object.values(result.arm_distribution), 1);
                    return (
                      <div key={arm} className="rp-dist-row">
                        <span>{arm}</span>
                        <i style={{ width: `${(n / max) * 100}%` }} />
                        <b>{n}</b>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="admin-section">
              <h2 className="admin-section-title">
                {rows.length ? `Generated (${rows.length})` : `Previously generated (${existing.length})`}
              </h2>
              <table className="rp-table">
                <thead>
                  <tr><th>Client</th><th>Template</th><th>Blocks</th><th>Email</th><th></th></tr>
                </thead>
                <tbody>
                  {(rows.length ? rows : existing).map((r) => (
                    <tr key={r.report_id}>
                      <td>
                        <b>{r.client_name}</b>
                        <div className="rp-sub">{r.email}</div>
                      </td>
                      <td>
                        <span className="rp-arm">{r.strategy}</span>
                        {r.method && <div className="rp-sub">{r.method}</div>}
                      </td>
                      <td className="rp-blocks">{(r.blocks || []).join(" · ")}</td>
                      <td><span className="rp-sent">{r.email_status}</span></td>
                      <td>
                        <button className="btn-secondary"
                                onClick={() => setPreview(r.report_id)}>
                          Preview
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {preview && (
          <div className="rp-modal" onClick={() => setPreview(null)}>
            <div className="rp-modal-inner" onClick={(e) => e.stopPropagation()}>
              <div className="rp-modal-bar">
                <b>{preview}</b>
                <a href={`/reports/${preview}/json`} target="_blank" rel="noreferrer">report.json</a>
                <a href={`/reports/${preview}/html`} target="_blank" rel="noreferrer">open</a>
                <button onClick={() => setPreview(null)}>Close</button>
              </div>
              <iframe title="report preview" src={`/reports/${preview}/html`} />
            </div>
          </div>
        )}
      </main>

      <Toast message={toast.msg} kind={toast.kind}
             onClose={() => setToast({ msg: null, kind: "" })} />
    </div>
  );
}
