import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

// snake_case / lower words -> PascalCase, for prefilling the Intent ID field
function toPascalCase(name) {
  return String(name || "")
    .replace(/[^a-zA-Z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join("");
}

const DEFAULT_DOMAIN = "finance";

function intentKey(row) {
  return row.intent_id || row.entity_id;
}

function strategyKey(row) {
  return row.strategy_id || row.entity_id;
}

export default function IntentsTab({ notify }) {
  const [rows, setRows]       = useState([]);
  const [strats, setStrats]   = useState([]);
  const [policies, setPolicies] = useState([]);
  const [intentId, setId]     = useState("");
  const [description, setD]   = useState("");
  const [selectedStrategies, setSelectedStrategies] = useState([]);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]       = useState(false);

  // Unmapped-intent backlog (classifier saw these but the taxonomy lacks them)
  const [suggestions, setSuggestions] = useState([]);
  const [sugLoad, setSugLoad]         = useState(false);

  async function refresh() {
    try {
      const [intents, strategies, policyRows] = await Promise.all([
        api.listIntents(),
        api.listStrategies(),
        api.listPolicies(),
      ]);
      setRows(intents);
      setStrats(strategies);
      setPolicies(policyRows);
    }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }

  async function refreshSuggestions() {
    setSugLoad(true);
    try { setSuggestions((await api.unmappedIntents(30, 50)).suggestions || []); }
    catch (err) { notify("Suggestions load failed: " + err.message, "error"); }
    finally { setSugLoad(false); }
  }

  useEffect(() => { refresh(); refreshSuggestions(); }, []);

  const defaultMappings = useMemo(() => {
    const map = new Map();
    for (const row of policies) {
      if (row.domain !== DEFAULT_DOMAIN || row.topic !== "_default") continue;
      if (!map.has(row.intent)) map.set(row.intent, []);
      map.get(row.intent).push(row.strategy_id);
    }
    for (const [intent, ids] of map.entries()) {
      map.set(intent, Array.from(new Set(ids)).sort());
    }
    return map;
  }, [policies]);

  const missingDefaultMappings = useMemo(() => (
    rows
      .map(intentKey)
      .filter((id) => id && (defaultMappings.get(id) || []).length === 0)
      .sort()
  ), [rows, defaultMappings]);

  function preferredDefaultStrategies() {
    const ids = strats.map(strategyKey).filter(Boolean);
    if (ids.includes("standard_llm")) return ["standard_llm"];
    return ids.slice(0, 1);
  }

  useEffect(() => {
    if (!editing && !intentId && selectedStrategies.length === 0 && strats.length > 0) {
      setSelectedStrategies(preferredDefaultStrategies());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strats, editing, intentId, selectedStrategies.length]);

  function resetForm() {
    setId("");
    setD("");
    setSelectedStrategies(preferredDefaultStrategies());
    setEditing(false);
  }

  function loadIntoForm(row) {
    const id = intentKey(row);
    setId(id);
    setD(row.description || "");
    setSelectedStrategies(defaultMappings.get(id) || preferredDefaultStrategies());
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function loadSuggestionIntoForm(s) {
    const topics = (s.top_topics || []).map((t) => t.topic).slice(0, 3).join(", ");
    setId(toPascalCase(s.suggested_intent));
    setD(topics ? `Promoted from unmapped — seen on: ${topics}` : "Promoted from unmapped backlog");
    setSelectedStrategies(preferredDefaultStrategies());
    setEditing(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toggleStrategy(strategyId) {
    setSelectedStrategies((current) => (
      current.includes(strategyId)
        ? current.filter((id) => id !== strategyId)
        : [...current, strategyId]
    ));
  }

  async function syncDefaultPolicies(intent, strategyIds) {
    const desired = new Set(strategyIds);
    const existing = new Set(defaultMappings.get(intent) || []);
    const toAdd = [...desired].filter((sid) => !existing.has(sid));
    const toRemove = [...existing].filter((sid) => !desired.has(sid));

    await Promise.all([
      ...toAdd.map((strategy_id) => api.upsertPolicy({
        domain: DEFAULT_DOMAIN,
        intent,
        topic: "_default",
        strategy_id,
        policy_version: "v1",
        exploration_constant: 1.0,
      })),
      ...toRemove.map((strategy_id) => api.deletePolicy(intent, "_default", strategy_id)),
    ]);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const id = intentId.trim();
    if (!id) return;
    if (selectedStrategies.length === 0) {
      notify("Pick at least one default candidate strategy for this intent.", "error");
      return;
    }
    setBusy(true);
    try {
      await api.upsertIntent({
        intent_id:   id,
        description: description.trim(),
      });
      await syncDefaultPolicies(id, selectedStrategies);
      notify(`Intent "${id}" ${editing ? "updated" : "saved"} with ${selectedStrategies.length} default strategies`);
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
          <code>Decision</code>, <code>Comparison</code>). The bandit's situation
          key includes intent, so each one builds its own learning state.
        </p>
        <ul className="col-legend">
          <li><strong>Intent ID</strong> — PascalCase label the classifier may emit. Must match exactly what the classifier returns.
            <em> e.g. Decision, Comparison, Explanation, Instructional, Definitional, Evaluation.</em></li>
          <li><strong>Description</strong> — one-line meaning of this intent, shown to admins reviewing the list.
            <em> e.g. "Should I X / Which X is right for me — recommendation requests".</em></li>
          <li><strong>Default strategies</strong> — accepted candidate strategies for this intent's <code>_default</code> policy.
            <em> Pick at least one. The bandit only chooses among these mapped strategies.</em></li>
        </ul>
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
            <button type="submit" className="btn-primary" disabled={busy || !intentId.trim() || selectedStrategies.length === 0}>
              {busy ? "Saving…" : (editing ? "Update intent" : "Save intent")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
          <div className="strategy-check-panel">
            <div className="strategy-check-head">
              <strong>Default strategy mappings</strong>
              <span>
                {selectedStrategies.length} selected for <code>{intentId.trim() || "new intent"}</code>
              </span>
            </div>
            {strats.length === 0 ? (
              <p className="admin-empty admin-empty-compact">
                No strategies configured yet. Add strategies before creating intents.
              </p>
            ) : (
              <div className="strategy-check-grid">
                {strats.map((strategy) => {
                  const sid = strategyKey(strategy);
                  return (
                    <label key={sid} className="strategy-check">
                      <input
                        type="checkbox"
                        checked={selectedStrategies.includes(sid)}
                        onChange={() => toggleStrategy(sid)}
                      />
                      <span className="strat-chip">{sid}</span>
                      <small>{strategy.format_type || "*"}</small>
                    </label>
                  );
                })}
              </div>
            )}
            {selectedStrategies.length === 0 && (
              <div className="mapping-warning">
                Pick at least one candidate strategy. Without this policy mapping,
                the bandit has no arm to select for the intent.
              </div>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <div className="admin-section-head">
          <h2 className="admin-section-title">
            Suggested intents — unmapped backlog ({suggestions.length})
          </h2>
          <button type="button" className="btn-secondary" onClick={refreshSuggestions} disabled={sugLoad}>
            {sugLoad ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <p className="admin-section-sub">
          Questions the classifier couldn't map to an existing intent over the
          last 30 days, grouped by its best-guess label. High-volume rows are
          good candidates to promote — click <strong>Use as new intent</strong>{" "}
          to prefill the form above.
        </p>
        {suggestions.length === 0 ? (
          <p className="admin-empty">
            {sugLoad ? "Loading…" : "No unmapped intents in the last 30 days — your taxonomy is covering traffic."}
          </p>
        ) : (
          <AdminTable
            columns={[
              { key: "suggested_intent", label: "Suggested intent", width: "200px",
                render: (s) => <code>{s.suggested_intent}</code> },
              { key: "count",        label: "Hits",  width: "80px",
                render: (s) => <span className="ts">{s.count}</span> },
              { key: "unique_users", label: "Users", width: "80px",
                render: (s) => <span className="ts">{s.unique_users}</span> },
              { key: "avg_confidence", label: "Avg conf.", width: "100px",
                render: (s) => <span className="ts">{s.avg_confidence}</span> },
              { key: "top_topics",   label: "Top topics",
                render: (s) => (s.top_topics || []).map((t) => `${t.topic} (${t.count})`).join(", ") || "—" },
              { key: "last_seen",    label: "Last seen", width: "180px",
                render: (s) => <span className="ts">{(s.last_seen || "").slice(0, 19).replace("T", " ")}</span> },
              { key: "_use",         label: "", width: "150px",
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
        {missingDefaultMappings.length > 0 && (
          <div className="mapping-warning mapping-warning-block">
            {missingDefaultMappings.length} active intent{missingDefaultMappings.length === 1 ? "" : "s"} need a default strategy mapping:{" "}
            {missingDefaultMappings.slice(0, 8).map((id) => (
              <code key={id}>{id}</code>
            ))}
            {missingDefaultMappings.length > 8 && <span> +{missingDefaultMappings.length - 8} more</span>}
          </div>
        )}
        <AdminTable
          columns={[
            { key: "intent_id",   label: "ID",          width: "180px" },
            { key: "description", label: "Description"                   },
            { key: "_default_strategies", label: "Default strategies",
              render: (r) => {
                const id = intentKey(r);
                const mapped = defaultMappings.get(id) || [];
                return mapped.length > 0 ? (
                  <div className="strategy-chip-list">
                    {mapped.map((sid) => <span key={sid} className="strat-chip">{sid}</span>)}
                  </div>
                ) : (
                  <span className="mapping-warning-inline">Needs mapping</span>
                );
              } },
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
