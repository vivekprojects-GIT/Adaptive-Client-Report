import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

export default function IntentsTab({ notify }) {
  const [rows, setRows]       = useState([]);
  const [intentId, setId]     = useState("");
  const [description, setD]   = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]       = useState(false);

  async function refresh() {
    try { setRows(await api.listIntents()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }

  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setId(""); setD(""); setEditing(false);
  }

  function loadIntoForm(row) {
    setId(row.intent_id || row.entity_id);
    setD(row.description || "");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!intentId.trim()) return;
    setBusy(true);
    try {
      await api.upsertIntent({
        intent_id:   intentId.trim(),
        description: description.trim(),
      });
      notify(`Intent "${intentId}" ${editing ? "updated" : "saved"}`);
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
      await api.deleteIntent(row.intent_id || row.entity_id);
      notify(`Intent "${row.intent_id || row.entity_id}" deleted`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing intent: ${intentId}` : "Add or update intent"}
        </h2>
        <p className="admin-section-sub">
          Intents define the question types the classifier may emit (e.g.
          <code>Decision</code>, <code>Comparison</code>). The bandit's cell
          key includes intent, so each one builds its own learning state.
        </p>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Intent ID
              <input
                type="text"
                placeholder="e.g. Comparison"
                value={intentId}
                onChange={(e) => setId(e.target.value)}
                disabled={editing}
                required
              />
            </label>
            <label className="grow">
              Description
              <input
                type="text"
                placeholder="What does this intent mean?"
                value={description}
                onChange={(e) => setD(e.target.value)}
              />
            </label>
            <button type="submit" className="btn-primary" disabled={busy || !intentId.trim()}>
              {busy ? "Saving…" : (editing ? "Update intent" : "Save intent")}
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
        <h2 className="admin-section-title">Active intents ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "intent_id",   label: "ID",          width: "180px" },
            { key: "description", label: "Description"                   },
            { key: "status",      label: "Status",      width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="intent"
                  entityId={r.intent_id || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
            { key: "ts",          label: "Updated",     width: "180px",
              render: (r) => <span className="ts">{(r.ts || "").slice(0, 19).replace("T", " ")}</span> },
          ]}
          rows={rows}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete intent "${row.intent_id}"? Existing bandit cells using this intent will become orphans.`}
          emptyText="No intents configured. Seed defaults via POST /admin/seed."
        />
      </div>
    </div>
  );
}
