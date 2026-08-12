import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * ThompsonTab — the selection policy's two knobs.
 *
 * Both decisions pick an arm by drawing once from each arm's Beta posterior
 * and taking the highest draw. The only tunable is how many
 * pseudo-observations the PRIOR is worth before real rewards outvote it:
 *
 *   D1 (report template)  — the prior is the template's declared style-fit
 *     against the client's learned dimensions. Strength 4 means "trust the
 *     declaration like 4 reports' worth of evidence".
 *   D2 (answer format)    — near-uniform prior; answer strategies make no
 *     strong declared claim, so data should take over fast.
 *
 * There is no exploration constant to tune — exploration comes from the
 * width of the posterior itself and narrows as evidence arrives.
 */
export default function ThompsonTab({ notify }) {
  const [cfg, setCfg]   = useState(null);
  const [d1, setD1]     = useState("");
  const [d2, setD2]     = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr]   = useState(null);

  async function load() {
    try {
      const c = await api.getThompsonConfig();
      setCfg(c); setD1(String(c.prior_strength_d1));
      setD2(String(c.prior_strength_d2)); setErr(null);
    } catch (e) { setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function save() {
    setBusy(true);
    try {
      const r = await api.updateThompsonConfig({
        prior_strength_d1: Number(d1), prior_strength_d2: Number(d2) });
      setCfg(r);
      notify?.("Thompson priors updated — applies on the next selection");
    } catch (e) { notify?.("Save failed: " + e.message, "error"); }
    finally { setBusy(false); }
  }

  return (
    <section>
      <div className="admin-explain">
        <div><strong>Selection policy: Thompson sampling</strong> — one Beta
          draw per arm, highest draw wins. Used by both decisions; there is
          no separate exploration constant, and no UCB anywhere in the
          serving path.</div>
        <div>The prior strength is how many pseudo-observations the declared
          style-fit is worth. Raise it and new templates are trusted longer;
          lower it and real rewards take over sooner. Changes apply live.</div>
      </div>
      {err && <div className="admin-error">{err}</div>}
      {cfg && (
        <div style={{ maxWidth: 460, display: "grid", gap: 14, marginTop: 12 }}>
          <label>
            D1 prior strength (report template selection)
            <input type="number" min="0.1" max="100" step="0.5" value={d1}
                   onChange={(e) => setD1(e.target.value)}
                   style={{ display: "block", marginTop: 4, padding: "7px 10px",
                            width: 140 }} />
          </label>
          <label>
            D2 prior strength (answer format selection)
            <input type="number" min="0.1" max="100" step="0.5" value={d2}
                   onChange={(e) => setD2(e.target.value)}
                   style={{ display: "block", marginTop: 4, padding: "7px 10px",
                            width: 140 }} />
          </label>
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
