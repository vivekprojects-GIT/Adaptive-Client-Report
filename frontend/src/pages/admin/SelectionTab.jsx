import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * SelectionTab — the contextual-UCB policy's three knobs.
 *
 * The answer-format decision (D2) scores every arm as
 *
 *     mean + c * sqrt(2 ln N / n)
 *
 * where the declared style-fit enters the mean as pseudo-observations
 * (the prior strength) and n counts real selections plus those
 * pseudo-observations. Highest score wins, deterministically.
 *
 * Batch diversity: counts rise at selection time, so during a
 * generate-for-all run each pick shrinks its own bonus and the next
 * client can get a different arm. Templates are NOT selected this
 * way — an advisor picks one, or the composer builds one.
 */
export default function SelectionTab({ notify }) {
  const [cfg, setCfg]   = useState(null);
  const [d1, setD1]     = useState("");
  const [d2, setD2]     = useState("");
  const [c, setC]       = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr]   = useState(null);

  async function load() {
    try {
      const v = await api.getSelectionConfig();
      setCfg(v);
      setD1(String(v.prior_strength_d1));
      setD2(String(v.prior_strength_d2));
      setC(String(v.exploration_c));
      setErr(null);
    } catch (e) { setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function save() {
    setBusy(true);
    try {
      const r = await api.updateSelectionConfig({
        prior_strength_d1: Number(d1),
        prior_strength_d2: Number(d2),
        exploration_c: Number(c),
      });
      setCfg(r);
      notify?.("Selection parameters updated — applies on the next selection");
    } catch (e) { notify?.("Save failed: " + e.message, "error"); }
    finally { setBusy(false); }
  }

  const field = (label, val, set, hint) => (
    <label>
      {label}
      <input type="number" min="0.1" max="100" step="0.1" value={val}
             onChange={(e) => set(e.target.value)}
             style={{ display: "block", marginTop: 4, padding: "7px 10px",
                      width: 140 }} />
      <span style={{ display: "block", color: "#94a3b8", fontSize: 12,
                     marginTop: 3 }}>{hint}</span>
    </label>
  );

  return (
    <section>
      <div className="admin-explain">
        <div><strong>Answer-format policy: contextual UCB</strong> — every arm is
          scored mean + c·√(2 ln N / n); the highest score is served.
          The context is the report type (D1) or the question intent (D2),
          and the client's learned dimensions shape the prior mean.</div>
        <div>Cold arms carry a large uncertainty bonus, so exploration needs
          no randomness — and because counts rise at selection time, a batch
          run spreads across arms instead of sending the whole book the same
          template.</div>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {cfg && (
        <div style={{ maxWidth: 520, display: "grid", gap: 16, marginTop: 12 }}>
          {field("Exploration constant c", c, setC,
                 "Bigger explores longer; smaller commits to the current best sooner.")}
          {field("D1 prior strength (report templates)", d1, setD1,
                 "How many reports of pretend evidence the declared style-fit is worth.")}
          {field("D2 prior strength (answer formats)", d2, setD2,
                 "Kept small: answer strategies make no strong declared claim.")}
          <div>
            <button className="admin-btn" disabled={busy} onClick={save}>
              Save
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
