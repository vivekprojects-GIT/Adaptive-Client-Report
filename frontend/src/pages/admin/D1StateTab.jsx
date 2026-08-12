import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * D1StateTab — the template decision's live posteriors, per report type.
 *
 * Context = report type (the advisor's dropdown selection). Arms = that
 * type's templates. Selections rise when a report is generated; reward is
 * the client's capped engagement with the delivered document (opened,
 * stayed, asked, downloaded, said it helped — at most 1.0 per report).
 */
export default function D1StateTab({ notify }) {
  const [data, setData] = useState(null);
  const [err, setErr]   = useState(null);

  async function load() {
    try { setData(await api.d1State()); setErr(null); }
    catch (e) { setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  const contexts = Object.entries(data?.contexts || {});

  return (
    <section>
      <div className="admin-explain">
        <div><strong>What the system has learned about report templates</strong> —
          read-only. Templates are edited in the Templates tab; this shows
          how each one is performing, per report type, under contextual UCB.</div>
        <div>Reward is the client's engagement with the delivered report,
          capped at 1.0 per report so a chatty client cannot make a template
          look better than it is. Rows appear per report type as reports are
          generated for it.</div>
      </div>
      <div style={{ margin: "10px 0" }}>
        <button className="admin-btn" onClick={load}>Refresh</button>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {contexts.length === 0 && !err && (
        <div className="admin-empty">
          No D1 selections recorded yet — generate a report and this fills in.
        </div>
      )}
      {contexts.map(([rt, arms]) => (
        <div key={rt} style={{ marginBottom: 18 }}>
          <h4 style={{ margin: "0 0 6px" }}>
            {rt.replace(/_/g, " ")}
            <span style={{ color: "#94a3b8", fontWeight: 400, marginLeft: 8 }}>
              {arms.reduce((a, r) => a + r.selected, 0)} reports
            </span>
          </h4>
          <table className="admin-table">
            <thead><tr>
              <th>Template arm</th><th>Reports</th><th>Rewarded</th>
              <th>Total reward</th><th>Reward mean</th><th>Updated</th>
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
                                      height: "100%", background: "#047857",
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
