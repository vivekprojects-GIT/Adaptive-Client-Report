import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

const CADENCES = ["quarterly", "annual", "monthly", "ad_hoc", "on_demand"];

export default function ReportTypesTab({ notify }) {
  const [rows, setRows]   = useState([]);
  const [rid, setRid]     = useState("");
  const [label, setLabel] = useState("");
  const [pers, setPers]   = useState(true);
  const [cad, setCad]     = useState("quarterly");
  const [notes, setNotes] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]   = useState(false);

  async function refresh() {
    try { setRows(await api.listReportTypes()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setRid(""); setLabel(""); setPers(true); setCad("quarterly");
    setNotes(""); setEditing(false);
  }

  function loadIntoForm(row) {
    setRid(row.report_type || row.entity_id);
    setLabel(row.label || "");
    setPers(row.personalisable !== false);
    setCad(row.cadence || "quarterly");
    setNotes(row.notes || "");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!rid.trim()) return;
    setBusy(true);
    try {
      await api.upsertReportType({
        report_type: rid.trim(),
        label: label.trim(),
        personalisable: pers,
        cadence: cad,
        notes: notes.trim(),
      });
      notify(`Report type "${rid}" ${editing ? "updated" : "saved"}`);
      resetForm();
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally { setBusy(false); }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing report type: ${rid}` : "Add or update report type"}
        </h2>
        <p className="admin-section-sub">
          A report type is the kind of report an advisor generates, such as a
          quarterly review or a fees report. It is chosen when the report is
          requested, never guessed from the client's data.
        </p>
        <div className="rule-box">
          <div><strong>The report type</strong> decides which templates can be used.</div>
          <div><strong>Each client's history</strong> shapes how the AI lays out and words the report, never which figures it contains.</div>
        </div>
        <ul className="col-legend">
          <li><strong>Report type</strong> — a short ID in lowercase with underscores. It cannot change after first use, because what the system learns is stored against it.
            <em> e.g. quarterly_portfolio_review, risk_report, fees_cost_report.</em></li>
          <li><strong>Personalisable</strong> — turn this <strong>off</strong> for reports whose format is set by regulation. Those always use their single mandated template, so a personalised statutory document cannot be produced by accident.</li>
          <li><strong>Cadence</strong> — how often it runs. A report type that runs rarely leans on each client's overall preferences, which are shared across every report type.</li>
        </ul>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Report type
              <input type="text" placeholder="e.g. quarterly_portfolio_review"
                     value={rid} onChange={(e) => setRid(e.target.value)}
                     disabled={editing} required />
            </label>
            <label>
              Label
              <input type="text" placeholder="Quarterly Portfolio Review"
                     value={label} onChange={(e) => setLabel(e.target.value)} />
            </label>
            <label>
              Cadence
              <select value={cad} onChange={(e) => setCad(e.target.value)}>
                {CADENCES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label style={{ alignSelf: "end" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <input type="checkbox" checked={pers}
                       onChange={(e) => setPers(e.target.checked)} />
                Personalisable
              </span>
            </label>
          </div>
          <div className="form-row">
            <label style={{ flex: 1 }}>
              Notes
              <input type="text" placeholder="Why this type exists, volume, caveats"
                     value={notes} onChange={(e) => setNotes(e.target.value)} />
            </label>
            <button type="submit" className="btn-primary" disabled={busy || !rid.trim()}>
              {busy ? "Saving…" : (editing ? "Update report type" : "Save report type")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>Cancel</button>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Report types ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "report_type", label: "Report type", width: "260px",
              render: (r) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{r.label || r.report_type}</div>
                  <code className="code-pill">{r.report_type || r.entity_id}</code>
                </div>
              ) },
            { key: "personalisable", label: "Format", width: "150px",
              render: (r) => (
                r.personalisable === false
                  ? <span className="pill pill-danger" title="Format set by regulation; never personalised">Prescribed</span>
                  : <span className="pill pill-neutral">Personalisable</span>
              ) },
            { key: "cadence", label: "Cadence", width: "120px",
              render: (r) => { const t = String(r.cadence || "").replace(/_/g, " ");
                               return <span style={{ whiteSpace: "nowrap" }}>
                                 {t ? t[0].toUpperCase() + t.slice(1) : "—"}</span>; } },
            { key: "notes", label: "Notes",
              render: (r) => <span className="ts">{r.notes || "—"}</span> },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill entityType="report_type"
                            entityId={r.report_type || r.entity_id}
                            status={r.status} notify={notify} onChanged={refresh} />
              ) },
          ]}
          rows={rows}
          onEdit={loadIntoForm}
          emptyText="No report types configured. Seed defaults or add one above."
        />
      </div>
    </div>
  );
}
