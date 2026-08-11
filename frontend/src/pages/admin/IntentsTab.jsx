import { useEffect, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

function toPascalCase(name) {
  return String(name || "")
    .replace(/[^a-zA-Z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join("");
}

export default function IntentsTab({ notify }) {
  const [rows, setRows] = useState([]);
  const [intentId, setId] = useState("");
  const [description, setD] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  const [suggestions, setSuggestions] = useState([]);
  const [sugLoad, setSugLoad] = useState(false);

  async function refresh() {
    try {
      setRows(await api.listIntents());
    } catch (err) {
      notify("Load failed: " + err.message, "error");
    }
  }

  async function refreshSuggestions() {
    setSugLoad(true);
    try {
      setSuggestions((await api.unmappedIntents(30, 50)).suggestions || []);
    } catch (err) {
      notify("Suggestions load failed: " + err.message, "error");
    } finally {
      setSugLoad(false);
    }
  }

  useEffect(() => { refresh(); refreshSuggestions(); }, []);

  function resetForm() {
    setId("");
    setD("");
    setEditing(false);
  }

  function loadIntoForm(row) {
    setId(row.intent_id || row.entity_id);
    setD(row.description || "");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function loadSuggestionIntoForm(s) {
    const topics = (s.top_topics || []).map((t) => t.topic).slice(0, 3).join(", ");
    setId(toPascalCase(s.suggested_intent));
    setD(topics ? `Promoted from unmapped - seen on: ${topics}` : "Promoted from unmapped backlog");
    setEditing(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const id = intentId.trim();
    if (!id) return;
    setBusy(true);
    try {
      await api.upsertIntent({
        intent_id: id,
        description: description.trim(),
      });
      notify(`Intent "${id}" ${editing ? "updated" : "saved"}`);
      resetForm();
      refresh();
      refreshSuggestions();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(row) {
    const id = row.intent_id || row.entity_id;
    try {
      await api.deleteIntent(id);
      notify(`Intent "${id}" deleted`);
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
          Intents define the question types the classifier may emit. Strategy
          mappings are managed on the Policies tab.
        </p>
        <ul className="col-legend">
          <li><strong>Intent ID</strong> - PascalCase label the classifier may emit. Must match exactly what the classifier returns.
            <em> e.g. Decision, Comparison, Explanation, Instructional, Definitional, Evaluation.</em></li>
          <li><strong>Description</strong> - one-line meaning of this intent, shown to admins reviewing the list.
            <em> e.g. "Comparing the portfolio against its benchmark".</em></li>
        </ul>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Intent ID
              <input
                type="text"
                placeholder="e.g. benchmark_comparison"
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
              {busy ? "Saving..." : (editing ? "Update intent" : "Save intent")}
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
        <div className="admin-section-head">
          <h2 className="admin-section-title">
            Suggested intents - unmapped backlog ({suggestions.length})
          </h2>
          <button type="button" className="btn-secondary" onClick={refreshSuggestions} disabled={sugLoad}>
            {sugLoad ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        <p className="admin-section-sub">
          Questions the classifier could not map to an existing intent over the
          last 30 days, grouped by its best-guess label. Promote only labels
          that should become part of the canonical taxonomy.
        </p>
        {suggestions.length === 0 ? (
          <p className="admin-empty">
            {sugLoad ? "Loading..." : "No unmapped intents in the last 30 days - your taxonomy is covering traffic."}
          </p>
        ) : (
          <AdminTable
            columns={[
              { key: "suggested_intent", label: "Suggested intent", width: "200px",
                render: (s) => <code>{s.suggested_intent}</code> },
              { key: "count", label: "Hits", width: "80px",
                render: (s) => <span className="ts">{s.count}</span> },
              { key: "unique_users", label: "Users", width: "80px",
                render: (s) => <span className="ts">{s.unique_users}</span> },
              { key: "avg_confidence", label: "Avg conf.", width: "100px",
                render: (s) => <span className="ts">{s.avg_confidence}</span> },
              { key: "top_topics", label: "Top topics",
                render: (s) => (s.top_topics || []).map((t) => `${t.topic} (${t.count})`).join(", ") || "-" },
              { key: "last_seen", label: "Last seen", width: "180px",
                render: (s) => <span className="ts">{(s.last_seen || "").slice(0, 19).replace("T", " ")}</span> },
              { key: "_use", label: "", width: "150px",
                render: (s) => (
                  <button type="button" className="btn-secondary" onClick={() => loadSuggestionIntoForm(s)}>
                    Use as new intent
                  </button>
                ) },
            ]}
            rows={suggestions}
            emptyText="No unmapped intents in the window."
          />
        )}
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Active intents ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "intent_id", label: "ID", width: "180px" },
            { key: "description", label: "Description" },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="intent"
                  entityId={r.intent_id || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
            { key: "ts", label: "Updated", width: "180px",
              render: (r) => <span className="ts">{(r.ts || "").slice(0, 19).replace("T", " ")}</span> },
          ]}
          rows={rows}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete intent "${row.intent_id}"? Policy mappings for this intent will also be deleted.`}
          emptyText="No intents configured. Seed defaults via POST /admin/seed."
        />
      </div>
    </div>
  );
}
