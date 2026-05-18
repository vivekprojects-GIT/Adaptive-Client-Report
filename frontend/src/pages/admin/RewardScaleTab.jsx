import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

export default function RewardScaleTab({ notify }) {
  const [rows, setRows]   = useState([]);
  const [cat, setCat]     = useState("");
  const [raw, setRaw]     = useState("");
  const [norm, setNorm]   = useState("");
  const [busy, setBusy]   = useState(false);

  async function refresh() {
    try { setRows(await api.listRewardScale()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!cat.trim() || raw === "") return;
    setBusy(true);
    try {
      const payload = {
        category:    cat.trim(),
        raw_reward:  parseFloat(raw),
      };
      if (norm !== "") payload.normalized_reward = parseFloat(norm);
      await api.upsertRewardValue(payload);
      notify(`Reward category "${cat}" saved`);
      setCat(""); setRaw(""); setNorm("");
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function loadIntoForm(row) {
    setCat(row.reward_category || row.entity_id);
    setRaw(String(row.raw_reward ?? ""));
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
          Maps a category name (e.g. <code>strong_positive</code>) to a
          raw reward and the normalized value used by the bandit math.
          Leave <strong>Normalized</strong> blank to default to{" "}
          <code>raw / 2.0</code>.
        </p>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Category
              <input
                type="text"
                placeholder="e.g. strong_positive"
                value={cat}
                onChange={(e) => setCat(e.target.value)}
                required
              />
            </label>
            <label>
              Raw reward
              <input
                type="number"
                step="0.5"
                placeholder="e.g. 2"
                value={raw}
                onChange={(e) => setRaw(e.target.value)}
                required
              />
            </label>
            <label>
              Normalized (optional)
              <input
                type="number"
                step="0.1"
                placeholder="raw / 2 by default"
                value={norm}
                onChange={(e) => setNorm(e.target.value)}
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
            { key: "reward_category",   label: "Category",
              render: (r) => <code className="code-pill">{r.reward_category}</code> },
            { key: "raw_reward",        label: "Raw",        width: "100px" },
            { key: "normalized_reward", label: "Normalized", width: "120px",
              render: (r) => r.normalized_reward != null ? r.normalized_reward.toFixed(2) : "—" },
            { key: "status",            label: "Status",     width: "130px",
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
