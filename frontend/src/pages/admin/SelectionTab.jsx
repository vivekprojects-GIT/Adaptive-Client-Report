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
    <label className="admin-field">
      {label}
      <input type="number" min="0.1" max="100" step="0.1" value={val}
             onChange={(e) => set(e.target.value)} />
      <span style={{ display: "block", color: "var(--muted)", fontSize: 12,
                     marginTop: 3 }}>{hint}</span>
    </label>
  );

  return (
    <section className="admin-section">
      <div className="admin-explain">
        <div><strong>How the system learns which answer style works.</strong> When
          a client asks their report a question, the system chooses between
          several answer styles and learns from their feedback which works best
          for each kind of question.</div>
        <div>Styles that have not been tried much are tried early, so the
          system keeps learning without guessing at random. These settings
          control how quickly it settles.</div>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {cfg && (
        <div style={{ maxWidth: 520, display: "grid", gap: 16, marginTop: 12 }}>
          {field("Exploration", c, setC,
                 "Higher keeps trying alternatives for longer; lower settles on the best performer sooner.")}
          {field("Starting confidence: report layouts", d1, setD1,
                 "How much the layout's declared fit counts before any client feedback arrives.")}
          {field("Starting confidence: answer styles", d2, setD2,
                 "Kept low, so real feedback takes over quickly.")}
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
