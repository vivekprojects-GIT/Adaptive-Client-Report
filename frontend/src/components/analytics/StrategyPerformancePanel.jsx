/**
 * StrategyPerformancePanel — per-strategy bandit performance for the current
 * domain scope. This is the most direct "is the bandit adapting?" view:
 * each row is a response format with its average reward, tier, and the cells
 * where it does best/worst. `standard_llm` is the no-format baseline — compare
 * structured formats against it to see whether the bandit is earning its keep.
 */
export default function StrategyPerformancePanel({ data, error, domainLabel }) {
  const rows = data?.global || [];

  return (
    <section className="section">
      <h2>
        Strategy performance{domainLabel ? ` — ${domainLabel}` : ""}
      </h2>
      <p className="section-sub">
        Average reward per response format in the selected scope. Tiers:
        HIGH ≥ 0.60 · MEDIUM ≥ 0.00 · LOW &lt; 0.00 · EXPLORING (too few pulls).
        Compare structured formats against <code>standard_llm</code> (the
        free-form baseline) to gauge adaptation.
      </p>

      {error && <div className="error-banner"><div className="error-detail">{error}</div></div>}

      {rows.length === 0 ? (
        <div className="empty-state">
          No strategy data with enough pulls in this scope yet. Send a few turns
          (and feedback) for this domain, then Recompute.
        </div>
      ) : (
        <table className="tbl">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Tier</th>
              <th style={{ textAlign: "right" }}>Avg reward</th>
              <th style={{ textAlign: "right" }}>Pulls</th>
              <th style={{ textAlign: "right" }}>Users</th>
              <th style={{ textAlign: "right" }}>Cells</th>
              <th>Best cell</th>
              <th>Worst cell</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.strategy}>
                <td>
                  <code>{r.strategy}</code>
                  {r.strategy === "standard_llm" && (
                    <span className="iq-totals"> · baseline</span>
                  )}
                </td>
                <td>
                  <span className={`tier-chip tier-${(r.tier || "").toLowerCase()}`}>
                    {r.tier}
                  </span>
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {r.avg_reward?.toFixed(3)}
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {r.total_pulls}
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {r.unique_users}
                </td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {r.unique_cells}
                </td>
                <td>{fmtCell(r.best_cell)}</td>
                <td>{fmtCell(r.worst_cell)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function fmtCell(c) {
  if (!c) return "—";
  return `${c.intent} / ${c.topic} (${c.avg_reward >= 0 ? "+" : ""}${c.avg_reward}, n=${c.count})`;
}
