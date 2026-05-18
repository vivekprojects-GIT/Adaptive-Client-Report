import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

const FORMAT_TYPES = [
  "paragraph", "bulleted_list", "numbered_steps",
  "comparison_table", "data_table", "decision_recommendation",
  "analogy_explainer", "hybrid",
];

export default function StrategiesTab({ notify }) {
  const [rows, setRows]      = useState([]);
  const [strategyId, setSid] = useState("");
  const [formatType, setFt]  = useState("paragraph");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]      = useState(false);

  async function refresh() {
    try { setRows(await api.listStrategies()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setSid(""); setFt("paragraph"); setEditing(false);
  }

  function loadIntoForm(row) {
    setSid(row.strategy_id || row.entity_id);
    setFt(row.format_type || "paragraph");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!strategyId.trim()) return;
    setBusy(true);
    try {
      await api.upsertStrategy({
        strategy_id: strategyId.trim(),
        format_type: formatType,
      });
      notify(`Strategy "${strategyId}" ${editing ? "updated" : "saved"}`);
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
      await api.deleteStrategy(row.strategy_id || row.entity_id);
      notify(`Strategy "${row.strategy_id || row.entity_id}" deleted (instructions removed too)`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing strategy: ${strategyId}` : "Add or update strategy"}
        </h2>
        <p className="admin-section-sub">
          A strategy is one of the bandit's arms. Each strategy has an
          associated <code>format_type</code> that the synthesizer LLM is
          expected to render. After creating a strategy here, publish an
          instruction for it under the <strong>Instructions</strong> tab.
        </p>
        <ul className="col-legend">
          <li><strong>Strategy ID</strong> — snake_case identifier for this answer-shape. Used as a bandit arm key, so it can never change after first use.
            <em> e.g. decision_card, comparison_table, analogy_explanation, one_liner, numbered_steps.</em></li>
          <li><strong>Format type</strong> — the structural shape the synthesizer should produce. Used by compute_format_compliance() to score how well the output matched.
            <em> e.g. paragraph (prose), bulleted_list (bullets), comparison_table (side-by-side), decision_recommendation (verdict + reasons), analogy_explainer (story-driven).</em></li>
        </ul>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Strategy ID
              <input
                type="text"
                placeholder="e.g. comparison_table"
                value={strategyId}
                onChange={(e) => setSid(e.target.value)}
                disabled={editing}
                required
              />
            </label>
            <label>
              Format type
              <select value={formatType} onChange={(e) => setFt(e.target.value)}>
                {FORMAT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <button type="submit" className="btn-primary" disabled={busy || !strategyId.trim()}>
              {busy ? "Saving…" : (editing ? "Update strategy" : "Save strategy")}
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
        <h2 className="admin-section-title">Active strategies ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "strategy_id", label: "ID",          width: "240px" },
            { key: "format_type", label: "Format type", width: "200px",
              render: (r) => <code className="code-pill">{r.format_type}</code> },
            { key: "status",      label: "Status",      width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="strategy"
                  entityId={r.strategy_id || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
            { key: "ts",          label: "Updated",
              render: (r) => <span className="ts">{(r.ts || "").slice(0, 19).replace("T", " ")}</span> },
          ]}
          rows={rows}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete strategy "${row.strategy_id}"? All instructions for it will also be removed.`}
          emptyText="No strategies configured."
        />
      </div>
    </div>
  );
}
