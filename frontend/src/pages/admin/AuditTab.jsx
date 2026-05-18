import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";

export default function AuditTab({ notify }) {
  const [rows, setRows] = useState([]);
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    try { setRows(await api.listAudit(date.trim() || "", 200)); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
    finally { setBusy(false); }
  }
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">Filter audit log</h2>
        <p className="admin-section-sub">
          Every config mutation through the admin API writes a before/after
          snapshot here. Filter by date or load all recent entries.
        </p>
        <form className="admin-form" onSubmit={(e) => { e.preventDefault(); refresh(); }}>
          <div className="form-row">
            <label>
              Date
              <input
                type="text"
                placeholder="YYYY-MM-DD (blank = all)"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Loading…" : "Refresh"}
            </button>
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Audit entries ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "ts",          label: "When",      width: "180px",
              render: (r) => <span className="ts">{(r.ts || "").slice(0, 19).replace("T", " ")}</span> },
            { key: "action_type", label: "Action",    width: "200px",
              render: (r) => <code className="code-pill">{r.action_type}</code> },
            { key: "entity_type", label: "Entity type", width: "140px" },
            { key: "entity_id",   label: "Entity ID",
              render: (r) => <code className="code-pill">{r.entity_id}</code> },
            { key: "changed_by",  label: "By",        width: "140px" },
          ]}
          rows={rows.map((r, i) => ({ ...r, _key: r.action_id || i }))}
          emptyText="No audit entries for this filter."
        />
      </div>
    </div>
  );
}
