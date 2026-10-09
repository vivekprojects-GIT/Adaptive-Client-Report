import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * D2StateTab — the answer-format decision's live posteriors.
 *
 * D1 (which template shapes the report) has its own state view. This is
 * the OTHER decision: when a client asks a question in the report viewer,
 * which answer strategy gets used, per question intent. Rows appear only
 * after real questions have been asked — an empty tab means clients have
 * not talked to their reports yet, and it says so instead of pretending.
 */
export default function D2StateTab({ notify }) {
  const [data, setData] = useState(null);
  const [err, setErr]   = useState(null);

  async function load() {
    try { setData(await api.d2State()); setErr(null); }
    catch (e) { setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  const contexts = Object.entries(data?.contexts || {});

  return (
    <section className="admin-section">
      <div className="admin-explain">
        <div><strong>What clients' feedback has taught the system about answer
          styles.</strong> Read-only. Each kind of question has its own table,
          showing how often each answer style was used and how often clients
          found it helpful.</div>
        <div>A "helpful" rating counts in a style's favour and "not really"
          counts against it. The settings that control this are under
          Learning settings.</div>
      </div>
      <div style={{ margin: "10px 0" }}>
        <button className="admin-btn" onClick={load}>Refresh</button>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {contexts.length === 0 && !err && (
        <div className="admin-empty">
          Nothing learned yet. Rows appear the first time a client asks a
          question about their report.
        </div>
      )}
      {contexts.map(([intent, arms]) => (
        <div key={intent} style={{ marginBottom: 18 }}>
          <h4 style={{ margin: "0 0 6px" }}>
            {(() => { const t = intent.replace(/_/g, " "); return t[0].toUpperCase() + t.slice(1); })()}
            <span style={{ color: "var(--muted)", fontWeight: 400, marginLeft: 8 }}>
              {arms.reduce((a, r) => a + r.selected, 0)} answers
            </span>
          </h4>
          <table className="admin-table">
            <thead><tr>
              <th>Answer style</th><th>Used</th><th>Rated</th>
              <th>Rated helpful</th><th>Helpful rate</th><th>Updated</th>
            </tr></thead>
            <tbody>
              {arms.map((a) => (
                <tr key={a.arm}>
                  <td>{(() => { const t = String(a.arm).replace(/_/g, " "); return t[0].toUpperCase() + t.slice(1); })()}</td>
                  <td>{a.selected}</td>
                  <td>{a.rewarded}</td>
                  <td>{a.total_reward}</td>
                  <td>
                    {/* With no ratings the stored mean is only the starting
                        assumption, so it is not shown as if it were a result. */}
                    {a.rewarded > 0 ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 90, height: 6, background: "var(--line)",
                                      borderRadius: 1 }}>
                          <div style={{ width: `${(a.total_reward / a.rewarded) * 100}%`,
                                        height: "100%", background: "var(--accent-active)",
                                        borderRadius: 1 }} />
                        </div>
                        {Math.round((a.total_reward / a.rewarded) * 100)}%
                      </div>
                    ) : <span style={{ color: "var(--subtle)" }}>No ratings yet</span>}
                  </td>
                  <td style={{ color: "var(--muted)", whiteSpace: "nowrap" }}>
                    {a.updated_at
                      ? new Date(a.updated_at + (/Z|[+-]\d\d:?\d\d$/.test(a.updated_at) ? "" : "Z"))
                          .toLocaleString(undefined, { day: "numeric", month: "short",
                                                       hour: "2-digit", minute: "2-digit" })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
}
