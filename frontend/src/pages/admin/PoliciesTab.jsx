import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import StrategyPerformancePanel from "./StrategyPerformancePanel.jsx";

const DEFAULT_DOMAIN = "finance";

function intentKey(row) {
  return row.intent_id || row.entity_id;
}

function strategyKey(row) {
  return row.strategy_id || row.entity_id;
}

/**
 * PoliciesTab — Intent → candidate-strategies mapping.
 *
 * A policy row whitelists ONE strategy for ONE (domain, intent, topic) cell.
 * The bandit only considers strategies that have a policy row for the cell.
 *
 * The page has two views:
 *   1. GROUPED  — one card per (intent, topic) showing all its strategies as
 *                 chips. Add/remove right on the chip; no form to fill in.
 *                 This is the day-to-day editing surface.
 *   2. RAW LIST — the flat table of every policy row. Power-user view, with
 *                 Edit-into-form support for the rarer fields (policy_version,
 *                 exploration_constant C).
 */
export default function PoliciesTab({ notify }) {
  const [rows, setRows]       = useState([]);
  const [strats, setStrats]   = useState([]);
  const [intents, setIntents] = useState([]);

  async function refresh() {
    try {
      const [p, s, i] = await Promise.all([
        api.listPolicies(),
        api.listStrategies(),
        api.listIntents(),
      ]);
      setRows(p);
      setStrats(s);
      setIntents(i);
    } catch (err) {
      notify("Load failed: " + err.message, "error");
    }
  }
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  // ----- Group policies by (domain, intent, topic) -----
  const grouped = useMemo(() => {
    const activeIntentIds = new Set(intents.map(intentKey).filter(Boolean));
    const map = new Map();
    for (const r of rows) {
      const key = `${r.domain}|${r.intent}|${r.topic}`;
      if (!map.has(key)) {
        map.set(key, {
          domain: r.domain,
          intent: r.intent,
          topic:  r.topic,
          strategies: [],
          rows: [],
          intentActive: activeIntentIds.has(r.intent),
        });
      }
      const g = map.get(key);
      g.strategies.push(r.strategy_id);
      g.rows.push(r);
      g.intentActive = activeIntentIds.has(r.intent);
    }
    for (const intent of activeIntentIds) {
      const key = `${DEFAULT_DOMAIN}|${intent}|_default`;
      if (!map.has(key)) {
        map.set(key, {
          domain: DEFAULT_DOMAIN,
          intent,
          topic: "_default",
          strategies: [],
          rows: [],
          intentActive: true,
        });
      }
    }
    // Sort: intent name asc, then _default first within intent
    return Array.from(map.values()).sort((a, b) => {
      if (a.intent !== b.intent) return a.intent.localeCompare(b.intent);
      if (a.topic === "_default") return -1;
      if (b.topic === "_default") return  1;
      return a.topic.localeCompare(b.topic);
    });
  }, [rows, intents]);

  const strategyOptions = useMemo(
    () => strats.map(strategyKey).filter(Boolean),
    [strats],
  );

  // ----- Quick-add: add one strategy to an existing (intent, topic) cell -----
  async function quickAdd(group, strategyId) {
    if (!strategyId) return;
    try {
      await api.upsertPolicy({
        domain:               group.domain,
        intent:               group.intent,
        topic:                group.topic,
        strategy_id:          strategyId,
        policy_version:       "v1",
        exploration_constant: 1.0,
      });
      notify(`Added ${strategyId} to ${group.intent}#${group.topic}`);
      refresh();
    } catch (err) {
      notify("Add failed: " + err.message, "error");
    }
  }

  // ----- Quick-remove: drop one strategy from a cell -----
  async function quickRemove(group, strategyId) {
    if (!window.confirm(`Remove "${strategyId}" from ${group.intent}#${group.topic}? The bandit will stop considering it for this cell.`)) return;
    try {
      await api.deletePolicy(group.intent, group.topic, strategyId);
      notify(`Removed ${strategyId} from ${group.intent}#${group.topic}`);
      refresh();
    } catch (err) {
      notify("Remove failed: " + err.message, "error");
    }
  }

  async function saveGroup(group, desiredStrategies) {
    if (!desiredStrategies.length) {
      notify("Pick at least one candidate strategy before saving.", "error");
      return;
    }
    const desired = new Set(desiredStrategies);
    const existing = new Set(group.strategies);
    const toAdd = [...desired].filter((sid) => !existing.has(sid));
    const toRemove = [...existing].filter((sid) => !desired.has(sid));

    try {
      await Promise.all([
        ...toAdd.map((strategy_id) => api.upsertPolicy({
          domain: group.domain,
          intent: group.intent,
          topic: group.topic,
          strategy_id,
          policy_version: "v1",
          exploration_constant: 1.0,
        })),
        ...toRemove.map((strategy_id) => api.deletePolicy(group.intent, group.topic, strategy_id)),
      ]);
      notify(`Updated ${group.intent}#${group.topic}`);
      refresh();
    } catch (err) {
      notify("Update failed: " + err.message, "error");
    }
  }

  async function deleteGroup(group) {
    if (!group.strategies.length) {
      notify("No policy rows to delete for this mapping.", "error");
      return;
    }
    if (!window.confirm(`Delete all strategy mappings for ${group.intent}#${group.topic}?`)) return;
    try {
      await Promise.all(
        group.strategies.map((strategyId) => api.deletePolicy(group.intent, group.topic, strategyId)),
      );
      notify(`Deleted mappings for ${group.intent}#${group.topic}`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  // Helper: for a group, what strategies are NOT yet attached?
  function availableForGroup(group) {
    const have = new Set(group.strategies);
    return strategyOptions.filter((sid) => !have.has(sid));
  }

  // For "add a brand new intent → strategies row" at the top of the page
  const [newIntent, setNewIntent]   = useState("");
  const [newTopic, setNewTopic]     = useState("_default");
  const [newStrategy, setNewStrat]  = useState("");

  async function handleNewMapping() {
    if (!newIntent || !newStrategy) return;
    try {
      await api.upsertPolicy({
        domain:               DEFAULT_DOMAIN,
        intent:               newIntent,
        topic:                newTopic.trim() || "_default",
        strategy_id:          newStrategy,
        policy_version:       "v1",
        exploration_constant: 1.0,
      });
      notify(`Mapping ${newIntent}#${newTopic} → ${newStrategy} added`);
      setNewStrat("");
      refresh();
    } catch (err) {
      notify("Add failed: " + err.message, "error");
    }
  }

  // Pull global strategy performance once so we can color the chips by tier
  const [perfByStrategy, setPerfByStrategy] = useState({});
  useEffect(() => {
    (async () => {
      try {
        const d = await api.strategyPerformance();
        const map = {};
        for (const s of (d?.global || [])) map[s.strategy] = s;
        setPerfByStrategy(map);
      } catch { /* fall through — chips render without tier coloring */ }
    })();
  }, [rows]);   // re-fetch when policy list changes

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <StrategyPerformancePanel notify={notify} />
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Intent → Candidate strategies</h2>
        <p className="admin-section-sub">
          Each intent has a list of strategies the bandit may pick from. The classifier
          detects the intent, then the bandit chooses among these candidates based on
          past reward. Use the chips below to add or remove strategies per intent. The
          special topic <code>_default</code> applies to all topics under that intent
          unless overridden by a topic-specific mapping.
        </p>
        <ul className="col-legend">
          <li><strong>Intent</strong> — the question type this policy governs. Must already exist on the Intents tab.
            <em> e.g. Decision, Comparison, Definitional.</em></li>
          <li><strong>Topic</strong> — the subject the policy applies to. Use <code>_default</code> as a catch-all for the intent; use a real topic to override the default for that specific subject.
            <em> e.g. _default (applies to all topics under this intent), retirement_accounts (overrides for retirement questions only).</em></li>
          <li><strong>Strategy</strong> — the candidate response format the bandit may consider in this situation. Add multiple strategies per row to give the bandit choices.
            <em> e.g. for Decision · retirement_accounts you might whitelist decision_card, pros_cons_table, and analogy_explanation.</em></li>
          <li><strong>Chip color</strong> — strategy's tier from the global performance table. Green = HIGH, amber = MEDIUM, red = LOW, gray = EXPLORING (not enough data).
            <em> e.g. a green decision_card chip means "this is a proven winner platform-wide".</em></li>
          <li><strong>× on a chip</strong> — removes the strategy from this situation only. The bandit stops considering it here on the next /turn (existing pulls stay in history).</li>
        </ul>

        {/* ---- Add a brand-new cell + strategy ---- */}
        <div className="policy-add-row">
          <label>
            Intent
            <select value={newIntent} onChange={(e) => setNewIntent(e.target.value)}>
              <option value="">(pick)</option>
              {intents.map((x) => {
                const id = intentKey(x);
                return <option key={id} value={id}>{id}</option>;
              })}
            </select>
          </label>
          <label>
            Topic
            <input value={newTopic} onChange={(e) => setNewTopic(e.target.value)} placeholder="_default" />
          </label>
          <label>
            Strategy
            <select value={newStrategy} onChange={(e) => setNewStrat(e.target.value)}>
              <option value="">(pick)</option>
              {strats.map((s) => {
                const id = strategyKey(s);
                return <option key={id} value={id}>{id}</option>;
              })}
            </select>
          </label>
          <button
            className="btn-primary"
            onClick={handleNewMapping}
            disabled={!newIntent || !newStrategy}
          >
            Add mapping
          </button>
        </div>

        {/* ---- Grouped cards ---- */}
        {grouped.length === 0 ? (
          <div className="admin-empty">
            No policies yet. Add a mapping above or run <code>POST /admin/seed</code>.
          </div>
        ) : (
          <div className="policy-group-list">
            {grouped.map((g) => (
              <PolicyGroupCard
                key={`${g.domain}|${g.intent}|${g.topic}`}
                group={g}
                available={availableForGroup(g)}
                onAdd={(sid) => quickAdd(g, sid)}
                onRemove={(sid) => quickRemove(g, sid)}
                onSave={(desired) => saveGroup(g, desired)}
                onDeleteGroup={() => deleteGroup(g)}
                allStrategies={strategyOptions}
                perfByStrategy={perfByStrategy}
              />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}

// ============================================================================
// PolicyGroupCard — one row per (domain, intent, topic) showing all its
// strategies as chips. Inline add (dropdown) + remove (× on chip).
// ============================================================================
function PolicyGroupCard({
  group,
  available,
  onAdd,
  onRemove,
  onSave,
  onDeleteGroup,
  allStrategies,
  perfByStrategy = {},
}) {
  const [picking, setPicking] = useState("");
  const [editing, setEditing] = useState(false);
  const [draftStrategies, setDraftStrategies] = useState(group.strategies);
  const isDefault = group.topic === "_default";
  const hasStrategies = group.strategies.length > 0;
  const isOrphan = group.intentActive === false;

  function beginEdit() {
    setDraftStrategies(group.strategies);
    setEditing(true);
  }

  function toggleDraft(strategyId) {
    setDraftStrategies((current) => (
      current.includes(strategyId)
        ? current.filter((id) => id !== strategyId)
        : [...current, strategyId]
    ));
  }

  async function saveDraft() {
    await onSave(draftStrategies);
    setEditing(false);
  }

  return (
    <div className={`policy-group ${!hasStrategies ? "policy-group-missing" : ""} ${isOrphan ? "policy-group-orphan" : ""}`}>
      <div className="policy-group-head">
        <span className="intent-chip">{group.intent}</span>
        <span className="dot-sep">·</span>
        <span className={`topic-chip ${isDefault ? "topic-default" : ""}`}>
          {isDefault ? "all topics (_default)" : group.topic}
        </span>
        {isOrphan && <span className="policy-alert">intent inactive or missing</span>}
        {!isOrphan && !hasStrategies && <span className="policy-alert">needs strategy mapping</span>}
        <span className="policy-count">
          {group.strategies.length} {group.strategies.length === 1 ? "strategy" : "strategies"}
        </span>
        <span className="policy-group-actions">
          <button
            type="button"
            className="admin-row-btn"
            onClick={editing ? () => setEditing(false) : beginEdit}
          >
            {editing ? "Cancel" : "Edit"}
          </button>
          <button
            type="button"
            className="admin-row-btn admin-row-btn-danger"
            onClick={onDeleteGroup}
            disabled={!hasStrategies}
          >
            Delete
          </button>
        </span>
      </div>

      {editing && (
        <div className="policy-edit-panel">
          <div className="strategy-check-grid">
            {allStrategies.map((sid) => (
              <label key={sid} className="strategy-check">
                <input
                  type="checkbox"
                  checked={draftStrategies.includes(sid)}
                  onChange={() => toggleDraft(sid)}
                />
                <span className="strat-chip">{sid}</span>
              </label>
            ))}
          </div>
          <div className="policy-edit-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={saveDraft}
              disabled={draftStrategies.length === 0}
            >
              Save mapping
            </button>
            <button type="button" className="btn-secondary" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="policy-chip-row">
        {!hasStrategies && (
          <span className="mapping-warning-inline">
            No candidate strategies yet.
          </span>
        )}
        {group.strategies.map((sid) => {
          const perf = perfByStrategy[sid];
          const tier = (perf?.tier || "").toLowerCase();
          return (
            <span
              key={sid}
              className={`policy-chip ${tier ? `policy-chip-tier-${tier}` : ""}`}
              title={
                perf
                  ? `${sid}\nTier: ${perf.tier}\nPerformance: ${perf.performance_pct.toFixed(1)}%\nμ-reward: ${perf.avg_reward.toFixed(2)}\nPulls: ${perf.total_pulls} across ${perf.unique_users} users`
                  : `${sid}\nNo data yet`
              }
            >
              {sid}
              {perf && (
                <span className="chip-perf">{perf.performance_pct.toFixed(0)}</span>
              )}
              <button
                className="chip-x"
                onClick={() => onRemove(sid)}
                title={`Remove ${sid} from this cell`}
                aria-label={`Remove ${sid}`}
              >
                ×
              </button>
            </span>
          );
        })}

        {available.length > 0 && (
          <span className="policy-add">
            <select
              value={picking}
              onChange={(e) => {
                const sid = e.target.value;
                setPicking("");
                if (sid) onAdd(sid);
              }}
            >
              <option value="">+ add strategy…</option>
              {available.map((sid) => (
                <option key={sid} value={sid}>{sid}</option>
              ))}
            </select>
          </span>
        )}
      </div>
    </div>
  );
}
