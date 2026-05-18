import { useEffect, useState } from "react";
import { api } from "../../api.js";
import UserAutocomplete from "../../components/UserAutocomplete.jsx";

/**
 * StrategyPerformancePanel — shows which strategies are paying off, both
 * globally and (optionally) for one user.
 *
 * Performance is mapped from avg_reward ∈ [-1, +1] onto a 0-100 percentage:
 *   performance_pct = (avg_reward + 1) / 2 × 100
 *
 *   HIGH       ≥ 80    green  — keep
 *   MEDIUM     50-80   amber  — refine instruction
 *   LOW        < 50    red    — pause or rewrite
 *   EXPLORING  < min_pulls    gray  — not enough data yet
 *
 * Each row also shows the strategy's best and worst cells so the admin
 * can see where it shines and where it bombs — a hint for instruction
 * refinement (maybe the strategy works for Comparisons but bombs on
 * Definitional, so the instruction needs tightening).
 */
export default function StrategyPerformancePanel({ notify }) {
  const [data, setData]     = useState(null);
  const [err, setErr]       = useState(null);
  const [busy, setBusy]     = useState(false);
  const [userId, setUserId] = useState("");
  const [minPulls, setMinPulls] = useState(3);

  async function load(overrideUser = null) {
    setBusy(true);
    setErr(null);
    try {
      const u = (overrideUser !== null ? overrideUser : userId).trim();
      const d = await api.strategyPerformance(u, minPulls);
      setData(d);
    } catch (e) {
      setErr(e.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const tierThresholds = data?.tier_thresholds || {};

  return (
    <div className="strategy-perf">
      <div className="strategy-perf-head">
        <h2 className="admin-section-title">Strategy performance</h2>
        <p className="admin-section-sub">
          Which strategies are paying off across users (and for one specific user).
          Performance = <code>(avg_reward + 1) / 2 × 100</code>. Tiers:
          <span className="tier-legend">
            <span className="tier-chip tier-high">HIGH</span>
            <span className="tier-chip tier-medium">MEDIUM</span>
            <span className="tier-chip tier-low">LOW</span>
            <span className="tier-chip tier-exploring">EXPLORING</span>
          </span>
          High strategies are keepers; medium ones might benefit from instruction tightening;
          low ones are candidates to pause or rewrite. Exploring = not enough pulls (&lt; {tierThresholds.min_pulls_for_tier ?? 3}) to tier yet.
        </p>

        <div className="strategy-perf-controls">
          <label>
            Filter to user (optional)
            <UserAutocomplete
              value={userId}
              onApply={(picked) => {
                setUserId(picked);
                load(picked);
              }}
              placeholder="empty = all users"
              allowEmpty
            />
          </label>
          <label>
            Min pulls for tier
            <input
              type="number"
              min="1"
              max="50"
              value={minPulls}
              onChange={(e) => setMinPulls(parseInt(e.target.value) || 3)}
            />
          </label>
          <button className="btn-primary" onClick={() => load()} disabled={busy}>
            {busy ? "Loading…" : "Refresh"}
          </button>
        </div>
      </div>

      {err && (
        <div className="error-banner">
          <strong>Failed</strong> <code>/analytics/strategy-performance</code>
          <div className="error-detail">{err}</div>
        </div>
      )}

      {data && (
        <>
          <PerfTable
            title={`Global · all users (${data.global.length} strategies pulled)`}
            rows={data.global}
          />
          {data.per_user !== null && (
            <PerfTable
              title={`Per-user · ${userId} (${data.per_user.length} strategies)`}
              rows={data.per_user}
              perUser
            />
          )}
        </>
      )}
    </div>
  );
}

function PerfTable({ title, rows, perUser = false }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="strategy-perf-block">
        <div className="strategy-perf-block-head">{title}</div>
        <div className="admin-empty">No strategies have been pulled yet.</div>
      </div>
    );
  }

  return (
    <div className="strategy-perf-block">
      <div className="strategy-perf-block-head">{title}</div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th style={{ width: "200px" }}>Strategy</th>
              <th style={{ width: "110px" }}>Tier</th>
              <th style={{ width: "240px" }}>Performance</th>
              <th style={{ width: "70px", textAlign: "right" }}>Pulls</th>
              {!perUser && <th style={{ width: "70px", textAlign: "right" }}>Users</th>}
              <th style={{ width: "60px", textAlign: "right" }}>Cells</th>
              <th>Best / worst cell</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.strategy}>
                <td>
                  <code className="code-pill">{s.strategy}</code>
                </td>
                <td>
                  <span className={`tier-chip tier-${s.tier.toLowerCase()}`}>
                    {s.tier}
                  </span>
                </td>
                <td>
                  <PerfBar pct={s.performance_pct} tier={s.tier} avg={s.avg_reward} />
                </td>
                <td className="num">{s.total_pulls}</td>
                {!perUser && <td className="num">{s.unique_users}</td>}
                <td className="num">{s.unique_cells}</td>
                <td className="cell-best-worst">
                  {s.best_cell && (
                    <div className="cell-best">
                      ↑ <code className="intent-chip">{s.best_cell.intent}</code>
                      <code className="topic-chip">{s.best_cell.topic}</code>
                      <span className="cell-mu">μ={s.best_cell.avg_reward.toFixed(2)}</span>
                    </div>
                  )}
                  {s.worst_cell && s.worst_cell !== s.best_cell &&
                   s.worst_cell.avg_reward < s.best_cell?.avg_reward && (
                    <div className="cell-worst">
                      ↓ <code className="intent-chip">{s.worst_cell.intent}</code>
                      <code className="topic-chip">{s.worst_cell.topic}</code>
                      <span className="cell-mu">μ={s.worst_cell.avg_reward.toFixed(2)}</span>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PerfBar({ pct, tier, avg }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="perf-bar-wrap">
      <div className="perf-bar-track">
        {/* tier-threshold gridlines */}
        <div className="perf-bar-gridline" style={{ left: "50%" }} />
        <div className="perf-bar-gridline" style={{ left: "80%" }} />
        <div
          className={`perf-bar-fill tier-${tier.toLowerCase()}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="perf-bar-label">
        <strong>{clamped.toFixed(1)}</strong>
        <span className="perf-bar-mu">μ={avg.toFixed(2)}</span>
      </span>
    </div>
  );
}
