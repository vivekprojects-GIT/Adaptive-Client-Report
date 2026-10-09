import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";

// Codes such as BANDIT_RESET are what the system records; an auditor reads
// "Learning reset". The raw code stays on hover for anyone matching logs.
const WORDS = { bandit: "learning", arm: "option", ucb: "learning",
                d1: "layout", d2: "answer", config: "setting" };
function readable(code) {
  const t = String(code || "").toLowerCase().split(/[_\s]+/).filter(Boolean)
    .map((w) => WORDS[w] || w).join(" ");
  return t ? t[0].toUpperCase() + t.slice(1) : "";
}
function when(ts) {
  if (!ts) return "";
  const d = new Date(ts + (/Z|[+-]\d\d:?\d\d$/.test(ts) ? "" : "Z"));
  return isNaN(d) ? ts : d.toLocaleString(undefined, { day: "numeric", month: "short",
    year: "numeric", hour: "2-digit", minute: "2-digit" });
}

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
          Every change to configuration is recorded here with a before and
          after snapshot. Pick a date, or leave it blank for the most recent
          entries.
        </p>
        <form className="admin-form" onSubmit={(e) => { e.preventDefault(); refresh(); }}>
          <div className="form-row">
            <label>
              Date
              <input
                type="date"
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
            { key: "ts",          label: "When",      width: "170px",
              render: (r) => <span className="audit-ts">{when(r.ts)}</span> },
            { key: "action_type", label: "Action",    width: "160px",
              render: (r) => <span title={r.action_type}>{readable(r.action_type)}</span> },
            { key: "entity_type", label: "Item",      width: "150px",
              render: (r) => <span title={r.entity_type}>{readable(r.entity_type)}</span> },
            { key: "entity_id",   label: "Reference",
              render: (r) => <code className="code-pill audit-ref" title={r.entity_id}>{r.entity_id}</code> },
            { key: "changed_by",  label: "By",        width: "110px" },
          ]}
          rows={rows.map((r, i) => ({ ...r, _key: r.action_id || i }))}
          emptyText="No audit entries for this filter."
        />
      </div>
    </div>
  );
}
