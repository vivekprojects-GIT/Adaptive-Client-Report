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
          A report type is D1's <strong>decision context</strong> — the situation
          the bandit chooses under. It is <em>selected</em> when a report is
          requested, never inferred from language, so there is no classifier and
          no confidence score attached to it.
        </p>
        <div className="rule-box">
          <div><strong>Report type</strong> determines <em>which arms are eligible</em>.</div>
          <div><strong>Client evidence</strong> shapes what the composer builds — it no longer chooses between templates.</div>
        </div>
        <ul className="col-legend">
          <li><strong>Report type</strong> — snake_case identifier. Forms part of the bandit cell key (<code>scope#report_type</code>), so it can never change after first use.
            <em> e.g. quarterly_portfolio_review, risk_report, fees_cost_report.</em></li>
          <li><strong>Personalisable</strong> — whether D1 may choose a shape at all. Turn this <strong>off</strong> for prescribed reports whose format is set by regulation. Those are served their single mandated template directly and raise an error if anything tries to run selection on them, so a personalised statutory document cannot be produced by accident.</li>
          <li><strong>Cadence</strong> — how often it runs. A rare report type will never accumulate enough evidence of its own; it relies on the client preference profile, which is shared across <em>all</em> report types.</li>
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
            { key: "personalisable", label: "D1", width: "150px",
              render: (r) => (
                r.personalisable === false
                  ? <span className="pill pill-danger" title="Format set by regulation — D1 refuses to select a shape">prescribed</span>
                  : <span className="pill pill-ok">personalisable</span>
              ) },
            { key: "cadence", label: "Cadence", width: "120px",
              render: (r) => <code className="code-pill">{r.cadence}</code> },
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
