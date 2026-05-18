import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";

/**
 * BanditStateTab — read-only inspection of `ape_user_bandit_state` rows.
 *
 * This is a DEBUG surface, not a normal admin workflow. Bandit state is
 * runtime data — written by Path A (lazy create) and Path B (reward update).
 * The admin doesn't normally touch it. But when something looks wrong
 * (e.g. "why did the bandit pick X?", "this strategy got corrupted by bad
 * feedback") this tab makes the raw state visible and allows targeted resets.
 *
 * View modes:
 *   GLOBAL  (empty user input)  → every pulled cell across every user
 *   USER    (user_id typed)     → just that user, grouped by (intent, topic)
 *
 * Per-cell actions (USER mode only):
 *   Reset cell      — drops the whole (intent, topic) cell for the user.
 *   Reset one arm   — drops a single (intent, topic, strategy) row.
 *   Next /turn lazy-creates fresh cold-start rows, so this is a safe "fix"
 *   when an instruction was rewritten and you want fresh learning.
 */
export default function BanditStateTab({ notify }) {
  const [rows, setRows]             = useState([]);
  const [userQuery, setUserQuery]   = useState("");
  const [onlyPulled, setOnlyPulled] = useState(true);
  const [busy, setBusy]             = useState(false);
  const [err, setErr]               = useState(null);

  const hasUser = Boolean(userQuery && userQuery.trim());

  async function load() {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.banditState(userQuery.trim(), onlyPulled);
      setRows(Array.isArray(r) ? r : []);
    } catch (e) {
      setErr(e.message);
      setRows([]);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  // Group rows by (user, intent, topic) → cells
  const cells = useMemo(() => {
    const map = new Map();
    for (const r of rows) {
      const key = `${r.user_id_hash}|${r.domain}|${r.intent}|${r.topic}`;
      if (!map.has(key)) {
        map.set(key, {
          user_id_hash: r.user_id_hash,
          display_name: r.display_name,
          domain:       r.domain,
          intent:       r.intent,
          topic:        r.topic,
          arms:         [],
          total_pulls:  0,
        });
      }
      const cell = map.get(key);
      cell.arms.push(r);
      cell.total_pulls += r.count;
    }
    // Sort: by user, then by total_pulls desc
    const groups = Array.from(map.values());
    groups.sort((a, b) => {
      const an = (a.display_name || a.user_id_hash || "").toLowerCase();
      const bn = (b.display_name || b.user_id_hash || "").toLowerCase();
      if (an !== bn) return an.localeCompare(bn);
      return b.total_pulls - a.total_pulls;
    });
    // Sort arms within each cell by cached_ucb desc (= next-pick order)
    for (const g of groups) {
      g.arms.sort((a, b) => b.cached_ucb - a.cached_ucb);
    }
    return groups;
  }, [rows]);

  async function resetCell(cell, strategy) {
    const label = strategy
      ? `the ${strategy} arm of ${cell.intent}#${cell.topic}`
      : `the entire ${cell.intent}#${cell.topic} cell`;
    if (!window.confirm(
      `Reset ${label} for ${cell.display_name || cell.user_id_hash}?\n\n` +
      `The bandit will re-create cold-start rows on this user's next /turn.`
    )) return;
    try {
      const res = await api.resetBanditCell(
        cell.user_id_hash, cell.domain, cell.intent, cell.topic, strategy || ""
      );
      notify(`Reset · ${res.deleted} row(s) deleted (${res.scope})`);
      await load();
    } catch (e) {
      notify("Reset failed: " + e.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">Bandit state inspector</h2>
        <p className="admin-section-sub">
          Read-only view of <code>ape_user_bandit_state</code> — every per-user cell
          with its arms' <code>count</code>, <code>avg_reward</code>, and
          <code> cached_ucb</code>. The arm with the highest <code>cached_ucb</code>
          is the one UCB will pick on the user's next <code>/turn</code> in that cell.
          Useful for debugging "why did the bandit pick X" or recovering from a
          poisoned cell after a bad-feedback session.
        </p>

        <div className="admin-form">
          <div className="form-row">
            <label className="grow">
              Filter to user (raw user_id or u_&lt;hash&gt;)
              <input
                type="text"
                placeholder="empty = all users"
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") load(); }}
              />
            </label>
            <label className="check-inline">
              <input
                type="checkbox"
                checked={onlyPulled}
                onChange={(e) => setOnlyPulled(e.target.checked)}
              />
              <span>Only pulled cells (hide count=0 cold-start rows)</span>
            </label>
            <button className="btn-primary" onClick={load} disabled={busy}>
              {busy ? "Loading…" : "Reload"}
            </button>
          </div>
        </div>

        {err && (
          <div className="error-banner">
            <strong>Failed</strong> <code>/admin/bandit-state</code>
            <div className="error-detail">{err}</div>
          </div>
        )}

        <div className="bandit-summary">
          {cells.length} cell{cells.length === 1 ? "" : "s"} ·
          {" "}{rows.length} arm row{rows.length === 1 ? "" : "s"} ·
          {" "}{new Set(rows.map((r) => r.user_id_hash)).size} unique user{new Set(rows.map((r) => r.user_id_hash)).size === 1 ? "" : "s"}
        </div>
      </div>

      {cells.length === 0 ? (
        <div className="admin-section">
          <div className="admin-empty">
            {hasUser
              ? `No bandit cells for "${userQuery}". Either the user has no activity yet, or the user_id you typed doesn't hash to anything we have.`
              : "No bandit state in the database. The very first /turn from any user will lazy-create cells."}
          </div>
        </div>
      ) : (
        <div className="admin-section">
          {cells.map((cell) => (
            <div key={`${cell.user_id_hash}#${cell.intent}#${cell.topic}`} className="bandit-cell">
              <div className="bandit-cell-head">
                <span className="bandit-cell-user">
                  {cell.display_name || cell.user_id_hash}
                  {cell.display_name && (
                    <code className="bandit-cell-hash">{cell.user_id_hash}</code>
                  )}
                </span>
                <span className="dot-sep">·</span>
                <code className="intent-chip">{cell.intent}</code>
                <code className="topic-chip">{cell.topic}</code>
                <span className="bandit-cell-summary">
                  {cell.arms.length} arms · {cell.total_pulls} total pulls
                </span>
                {hasUser && (
                  <button
                    className="admin-row-btn admin-row-btn-danger"
                    onClick={() => resetCell(cell)}
                    title="Drop the whole cell — next /turn re-creates with cold-start"
                  >
                    Reset cell
                  </button>
                )}
              </div>
              <table className="admin-table bandit-arms-tbl">
                <thead>
                  <tr>
                    <th style={{ width: "30px" }}></th>
                    <th>Strategy</th>
                    <th className="num">Pulls</th>
                    <th className="num">μ-reward</th>
                    <th className="num">total_reward</th>
                    <th className="num" title="UCB1 score. Highest wins on next /turn.">cached UCB</th>
                    <th>Last updated</th>
                    {hasUser && <th style={{ width: "100px" }}>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {cell.arms.map((a, idx) => {
                    const isWinner = idx === 0;
                    return (
                      <tr key={a.strategy} className={isWinner ? "winner-row" : ""}>
                        <td title={isWinner ? "Next pick — highest cached_ucb" : ""}>
                          {isWinner ? <span className="winner-arrow">▶</span> : ""}
                        </td>
                        <td><code className="code-pill">{a.strategy}</code></td>
                        <td className="num">{a.count}</td>
                        <td className={`num ${a.avg_reward >= 0.3 ? "pos-num" : a.avg_reward < 0 ? "neg-num" : ""}`}>
                          {a.avg_reward.toFixed(3)}
                        </td>
                        <td className="num">{a.total_reward.toFixed(2)}</td>
                        <td className="num"><strong>{a.cached_ucb.toFixed(3)}</strong></td>
                        <td className="ts">
                          {a.last_updated_at ? a.last_updated_at.slice(0, 19).replace("T", " ") : "—"}
                        </td>
                        {hasUser && (
                          <td>
                            <button
                              className="admin-row-btn admin-row-btn-danger"
                              onClick={() => resetCell(cell, a.strategy)}
                              title="Drop just this arm — bandit re-explores it"
                            >
                              Reset arm
                            </button>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
