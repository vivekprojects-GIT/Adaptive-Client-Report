import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * UcbConfigTab - tune the UCB-based selection score formula live (no redeploy).
 *
 *   selection_score = avg_reward + c * width * sqrt(2 * ln N / count)
 *
 *   c     (exploration_c)      — exploration constant. Lower = exploit sooner.
 *   width (reward_range_width) — reward range (b−a); 4 because rewards span [-2,+2].
 *
 * Changes persist to MongoDB (bandit_config/ucb), are audited, and apply to the
 * running selector immediately. (Research / papers now live in the Research tab.)
 */
export default function UcbConfigTab({ notify }) {
  const [c, setC] = useState("");
  const [width, setWidth] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const cfg = await api.getUcbConfig();
      setC(String(cfg.exploration_c));
      setWidth(String(cfg.reward_range_width));
      setLoaded(true);
    } catch (err) {
      notify("Load failed: " + err.message, "error");
    }
  }

  useEffect(() => { refresh(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    const cNum = parseFloat(c);
    const wNum = parseFloat(width);
    if (Number.isNaN(cNum) || Number.isNaN(wNum)) {
      notify("Enter valid numbers", "error");
      return;
    }
    setBusy(true);
    try {
      const res = await api.updateUcbConfig({
        exploration_c: cNum,
        reward_range_width: wNum,
      });
      setC(String(res.exploration_c));
      setWidth(String(res.reward_range_width));
      notify(`Selection score updated - c=${res.exploration_c}, width=${res.reward_range_width} (applied live)`);
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  // Illustrative bonus at count=1, N=4 so the admin sees the effect live.
  const cNum = parseFloat(c), wNum = parseFloat(width);
  const sampleBonus = (!Number.isNaN(cNum) && !Number.isNaN(wNum))
    ? (cNum * wNum * Math.sqrt(2 * Math.log(4) / 1)).toFixed(2)
    : "—";

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">Selection score formula</h2>
        <p className="admin-section-sub">
          Controls how the bandit balances <strong>exploration</strong> vs{" "}
          <strong>exploitation</strong> when picking a strategy. Round-robin always
          tries every arm once first; these knobs govern what happens after that.
          The UI calls the computed number <strong>selection score</strong> so it is not
          confused with reward.
          The research basis, papers, and roadmap now live in the{" "}
          <strong>Research</strong> tab.
        </p>

        <div className="reward-scale-pointer">
          <strong>Formula:</strong>{" "}
          <code>selection_score = avg_reward + c * width * sqrt(2 * ln N / count)</code>
          <ul className="col-legend">
            <li><strong>c (exploration constant)</strong> — higher = more exploration (samples all strategies longer); lower = commits to the learned winner sooner.
              <em> c=1 is textbook-balanced; c≈0.25–0.5 suits sparse feedback.</em></li>
            <li><strong>width (reward range)</strong> — the span of the reward scale, <code>b−a</code>. Rewards are explicit ±2 / inferred ±1, so the range is <strong>4</strong>. Keep this matched to your reward scale.
              <em> Only change this if you change the reward tiers.</em></li>
          </ul>
        </div>

        {loaded && (
          <form className="admin-form" onSubmit={handleSubmit}>
            <div className="form-row">
              <label>
                Exploration constant (c)
                <input
                  type="number" step="0.05" min="0" max="10"
                  value={c} onChange={(e) => setC(e.target.value)} required
                />
              </label>
              <label>
                Reward range width (b−a)
                <input
                  type="number" step="0.5" min="0.5" max="100"
                  value={width} onChange={(e) => setWidth(e.target.value)} required
                />
              </label>
            </div>
            <div className="form-row">
              <span className="muted">
                Example exploration bonus at <code>count=1, N=4</code>:{" "}
                <strong>{sampleBonus}</strong> (vs reward range {width || "?"})
              </span>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Saving…" : "Save & apply live"}
              </button>
              <button type="button" className="btn-secondary" onClick={refresh} disabled={busy}>
                Reset
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
