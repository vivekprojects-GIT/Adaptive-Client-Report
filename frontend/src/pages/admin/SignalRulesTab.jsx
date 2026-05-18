import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

const CATEGORIES = [
  { value: "",                 label: "(none — NOT_RECORDED)" },
  { value: "strong_positive",  label: "strong_positive (+2)" },
  { value: "weak_positive",    label: "weak_positive (+1)" },
  { value: "weak_negative",    label: "weak_negative (-1)" },
  { value: "strong_negative",  label: "strong_negative (-2)" },
];

export default function SignalRulesTab({ notify }) {
  const [rows, setRows]     = useState([]);
  const [signalName, setN]  = useState("");
  const [fmtRel, setFr]     = useState(true);
  const [ctnRel, setCr]     = useState(true);
  const [fmtCat, setFc]     = useState("strong_positive");
  const [ctnCat, setCc]     = useState("strong_positive");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]     = useState(false);

  async function refresh() {
    try { setRows(await api.listSignalRules()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setN(""); setFr(true); setCr(true);
    setFc("strong_positive"); setCc("strong_positive");
    setEditing(false);
  }

  function loadIntoForm(row) {
    setN(row.signal_name || row.entity_id);
    setFr(!!row.format_relevant);
    setCr(!!row.content_relevant);
    setFc(row.format_category || "strong_positive");
    setCc(row.content_category || "strong_positive");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!signalName.trim()) return;
    setBusy(true);
    try {
      await api.upsertSignalRule({
        signal_name:      signalName.trim(),
        format_relevant:  fmtRel,
        content_relevant: ctnRel,
        format_category:  fmtRel ? (fmtCat || null) : null,
        content_category: ctnRel ? (ctnCat || null) : null,
      });
      notify(`Signal rule "${signalName}" ${editing ? "updated" : "saved"}`);
      resetForm();
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(row) {
    try {
      await api.deleteSignalRule(row.signal_name || row.entity_id);
      notify(`Signal rule "${row.signal_name || row.entity_id}" deleted`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing signal rule: ${signalName}` : "Add or update signal routing rule"}
        </h2>
        <p className="admin-section-sub">
          Each signal has two axes — <strong>format</strong> and{" "}
          <strong>content</strong>. Mark each as relevant or not, then pick
          a reward category. <code>NOT_RECORDED</code> means the axis isn't
          updated at all (the bandit counter stays frozen).
        </p>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Signal name
              <input
                type="text"
                placeholder="e.g. thumbs_up"
                value={signalName}
                onChange={(e) => setN(e.target.value)}
                disabled={editing}
                required
              />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={fmtRel} onChange={(e) => setFr(e.target.checked)} />
              format_relevant
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={ctnRel} onChange={(e) => setCr(e.target.checked)} />
              content_relevant
            </label>
          </div>
          <div className="form-row">
            <label className="grow">
              Format reward category
              <select value={fmtCat} onChange={(e) => setFc(e.target.value)} disabled={!fmtRel}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </label>
            <label className="grow">
              Content reward category
              <select value={ctnCat} onChange={(e) => setCc(e.target.value)} disabled={!ctnRel}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </label>
            <button type="submit" className="btn-primary" disabled={busy || !signalName.trim()}>
              {busy ? "Saving…" : (editing ? "Update rule" : "Save rule")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Active rules ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "signal_name",      label: "Signal",          width: "210px",
              render: (r) => <code className="code-pill">{r.signal_name}</code> },
            { key: "format_relevant",  label: "Format",          width: "70px",
              render: (r) => r.format_relevant ? "✓" : "—" },
            { key: "format_category",  label: "Format reward",   width: "160px",
              render: (r) => r.format_category || <span className="muted">—</span> },
            { key: "content_relevant", label: "Content",         width: "70px",
              render: (r) => r.content_relevant ? "✓" : "—" },
            { key: "content_category", label: "Content reward",  width: "150px",
              render: (r) => r.content_category || <span className="muted">—</span> },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="signal_routing"
                  entityId={r.signal_name || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
          ]}
          rows={rows.map((r, i) => ({ ...r, _key: i }))}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete signal rule "${row.signal_name}"? Future feedback with this signal will be ignored.`}
          emptyText="No signal rules configured."
        />
      </div>
    </div>
  );
}
