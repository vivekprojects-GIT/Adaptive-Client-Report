import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import StrategyPerformancePanel from "./StrategyPerformancePanel.jsx";

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
        });
      }
      const g = map.get(key);
      g.strategies.push(r.strategy_id);
      g.rows.push(r);
    }
    // Sort: intent name asc, then _default first within intent
    return Array.from(map.values()).sort((a, b) => {
      if (a.intent !== b.intent) return a.intent.localeCompare(b.intent);
      if (a.topic === "_default") return -1;
      if (b.topic === "_default") return  1;
      return a.topic.localeCompare(b.topic);
    });
  }, [rows]);

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

  // Helper: for a group, what strategies are NOT yet attached?
  function availableForGroup(group) {
    const have = new Set(group.strategies);
    return strats.map((s) => s.strategy_id).filter((sid) => !have.has(sid));
  }

  // For "add a brand new intent → strategies row" at the top of the page
  const [newIntent, setNewIntent]   = useState("");
  const [newTopic, setNewTopic]     = useState("_default");
  const [newStrategy, setNewStrat]  = useState("");

  async function handleNewMapping() {
    if (!newIntent || !newStrategy) return;
    try {
      await api.upsertPolicy({
        domain:               "finance",
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

        {/* ---- Add a brand-new cell + strategy ---- */}
        <div className="policy-add-row">
          <label>
            Intent
            <select value={newIntent} onChange={(e) => setNewIntent(e.target.value)}>
              <option value="">(pick)</option>
              {intents.map((x) => <option key={x.intent_id} value={x.intent_id}>{x.intent_id}</option>)}
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
              {strats.map((s) => <option key={s.strategy_id} value={s.strategy_id}>{s.strategy_id}</option>)}
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
function PolicyGroupCard({ group, available, onAdd, onRemove, perfByStrategy = {} }) {
  const [picking, setPicking] = useState("");
  const isDefault = group.topic === "_default";

  return (
    <div className="policy-group">
      <div className="policy-group-head">
        <span className="intent-chip">{group.intent}</span>
        <span className="dot-sep">·</span>
        <span className={`topic-chip ${isDefault ? "topic-default" : ""}`}>
          {isDefault ? "all topics (_default)" : group.topic}
        </span>
        <span className="policy-count">
          {group.strategies.length} {group.strategies.length === 1 ? "strategy" : "strategies"}
        </span>
      </div>

      <div className="policy-chip-row">
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
