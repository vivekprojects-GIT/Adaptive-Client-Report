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
    <section>
      <div className="admin-explain">
        <div><strong>Decision D2</strong> — how an answer is formatted when a
          client asks a question in the report viewer.</div>
        <div><strong>Context</strong> = the question's intent (classified).
          <strong> Arms</strong> = answer strategies. Selection is a Thompson
          draw over each arm's Beta posterior; a 👍 on an answer is reward 1
          to the exact arm that wrote it, a 👎 is reward 0 — evidence, not
          punishment.</div>
      </div>
      <div style={{ margin: "10px 0" }}>
        <button className="admin-btn" onClick={load}>Refresh</button>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {contexts.length === 0 && !err && (
        <div className="admin-empty">
          No D2 evidence yet. Rows appear the first time a client asks a
          question in the report viewer — selection until then is the
          uniform prior.
        </div>
      )}
      {contexts.map(([intent, arms]) => (
        <div key={intent} style={{ marginBottom: 18 }}>
          <h4 style={{ margin: "0 0 6px" }}>
            {intent.replace(/_/g, " ")}
            <span style={{ color: "#94a3b8", fontWeight: 400, marginLeft: 8 }}>
              {arms.reduce((a, r) => a + r.selected, 0)} selections
            </span>
          </h4>
          <table className="admin-table">
            <thead><tr>
              <th>Answer strategy</th><th>Selected</th><th>Feedback</th>
              <th>Total reward</th><th>Posterior mean</th><th>Updated</th>
            </tr></thead>
            <tbody>
              {arms.map((a) => (
                <tr key={a.arm}>
                  <td><code>{a.arm}</code></td>
                  <td>{a.selected}</td>
                  <td>{a.rewarded}</td>
                  <td>{a.total_reward}</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 90, height: 7, background: "#e2e8f0",
                                    borderRadius: 3 }}>
                        <div style={{ width: `${a.posterior_mean * 100}%`,
                                      height: "100%", background: "#2563eb",
                                      borderRadius: 3 }} />
                      </div>
                      {a.posterior_mean}
                    </div>
                  </td>
                  <td style={{ color: "#94a3b8" }}>{a.updated_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
}
