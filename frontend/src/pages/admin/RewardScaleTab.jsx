import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

export default function RewardScaleTab({ notify }) {
  const [rows, setRows] = useState([]);
  const [cat, setCat]   = useState("");
  const [norm, setNorm] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try { setRows(await api.listRewardScale()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!cat.trim() || norm === "") return;
    setBusy(true);
    try {
      await api.upsertRewardValue({
        category:          cat.trim(),
        normalized_reward: parseFloat(norm),
      });
      notify(`Reward category "${cat}" saved`);
      setCat(""); setNorm("");
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function loadIntoForm(row) {
    setCat(row.reward_category || row.entity_id);
    setNorm(row.normalized_reward != null ? String(row.normalized_reward) : "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleDelete(row) {
    try {
      await api.deleteRewardValue(row.reward_category || row.entity_id);
      notify(`Reward category "${row.reward_category || row.entity_id}" deleted`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">Add or update reward value</h2>
        <p className="admin-section-sub">
          Maps an evidence tier (e.g. <code>explicit_positive</code>) to the
          reward value applied to the bandit. Per the reward doc: explicit
          evidence = <code>±2</code>, inferred valence = <code>±1</code>.
        </p>
        <ul className="col-legend">
          <li><strong>Category</strong> — snake_case name referenced by signal-routing rules. Must match exactly what those rules emit.
            <em> e.g. explicit_positive, inferred_positive, inferred_negative, explicit_negative.</em></li>
          <li><strong>Reward</strong> — the value the bandit adds to <code>total_reward</code> when this category fires.
            <em> Defaults: explicit = ±2.0, inferred = ±1.0. Adjust if you want a tighter or looser learning rate.</em></li>
        </ul>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Category
              <input
                type="text"
                placeholder="e.g. explicit_positive"
                value={cat}
                onChange={(e) => setCat(e.target.value)}
                required
              />
            </label>
            <label>
              Reward
              <input
                type="number"
                step="0.5"
                min="-2"
                max="2"
                placeholder="e.g. 2.0"
                value={norm}
                onChange={(e) => setNorm(e.target.value)}
                required
              />
            </label>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save reward"}
            </button>
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Active reward categories ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "reward_category", label: "Category",
              render: (r) => <code className="code-pill">{r.reward_category}</code> },
            { key: "normalized_reward", label: "Reward", width: "120px",
              render: (r) => r.normalized_reward != null
                ? <span className="num"><strong>{fmtSigned(r.normalized_reward)}</strong></span>
                : "—" },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="reward_scale"
                  entityId={r.reward_category || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
          ]}
          rows={rows.map((r, i) => ({ ...r, _key: i }))}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete reward category "${row.reward_category}"? Future signals mapped to it will record no reward.`}
          emptyText="No reward values configured."
        />
      </div>
    </div>
  );
}

function fmtSigned(v) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const num = Number(v);
  const sign = num > 0 ? "+" : num < 0 ? "−" : "";
  return `${sign}${Math.abs(num).toFixed(2)}`;
}
