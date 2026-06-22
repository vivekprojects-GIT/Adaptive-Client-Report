import { useEffect, useState } from "react";
import { api } from "../../api.js";

// Research references behind the UCB formula — shown in the tab so the
// formula choices are traceable to the literature.
const CORE_REFS = [
  {
    title: "Auer, Cesa-Bianchi & Fischer (2002) — Finite-time Analysis of the Multiarmed Bandit Problem",
    note: "Defines UCB1: x̄ⱼ + √(2·ln n / nⱼ). The algorithm we use.",
    url: "https://link.springer.com/article/10.1023/A:1013689704352",
  },
  {
    title: "Sutton & Barto (2018) — Reinforcement Learning: An Introduction, §2.7",
    note: "Writes UCB as Q(a) + c·√(ln t / N(a)) — the source of the tunable c knob.",
    url: "http://incompleteideas.net/book/the-book-2nd.html",
  },
  {
    title: "Hoeffding (1963) — Probability Inequalities for Sums of Bounded Random Variables",
    note: "The confidence bound scales with the reward range (b−a) — basis for our width factor.",
    url: "https://doi.org/10.1080/01621459.1963.10500830",
  },
  {
    title: "Lai & Robbins (1985) — Asymptotically efficient adaptive allocation rules",
    note: "Established the logarithmic regret lower bound that UCB achieves.",
    url: "https://doi.org/10.1016/0196-8858(85)90002-8",
  },
  {
    title: "Lattimore & Szepesvári (2020) — Bandit Algorithms (Cambridge Univ. Press)",
    note: "Comprehensive modern textbook; derives UCB1, range scaling, and the variants. Free PDF.",
    url: "https://tor-lattimore.com/downloads/book/book.pdf",
  },
];

const VARIANT_REFS = [
  {
    title: "Garivier & Moulines (2011) — On Upper-Confidence Bound Policies for Switching Bandit Problems",
    note: "Discounted / sliding-window UCB for non-stationary rewards (preference drift).",
    url: "https://arxiv.org/abs/0805.3415",
  },
  {
    title: "Audibert, Munos & Szepesvári (2009) — Exploration–exploitation with variance estimates",
    note: "UCB-V: adds a per-arm variance term.",
    url: "https://doi.org/10.1016/j.tcs.2009.01.016",
  },
  {
    title: "Garivier & Cappé (2011) — The KL-UCB Algorithm for Bounded Stochastic Bandits",
    note: "Tighter confidence bounds via KL divergence.",
    url: "https://arxiv.org/abs/1102.2490",
  },
  {
    title: "Agrawal & Goyal (2012) — Analysis of Thompson Sampling for the Multi-armed Bandit Problem",
    note: "Bayesian alternative to UCB (the analytics page's Beta-curve view nods to this).",
    url: "https://arxiv.org/abs/1111.1797",
  },
  {
    title: "Li, Chu, Langford & Schapire (2010) — A Contextual-Bandit Approach (LinUCB)",
    note: "Contextual bandits — the natural next step if signal feature_ids become context.",
    url: "https://arxiv.org/abs/1003.0146",
  },
];

/**
 * UcbConfigTab — tune the UCB selection formula live (no redeploy).
 *
 *   ucb = avg_reward + c · width · √(2 · ln N / count)
 *
 *   c     (exploration_c)      — exploration constant. Lower = exploit sooner.
 *   width (reward_range_width) — reward range (b−a); 4 because rewards span [-2,+2].
 *
 * Changes are persisted to MongoDB (bandit_config/ucb), audited, and applied
 * to the running selector immediately.
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
      notify(`UCB updated — c=${res.exploration_c}, width=${res.reward_range_width} (applied live)`);
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
        <h2 className="admin-section-title">UCB selection formula</h2>
        <p className="admin-section-sub">
          Controls how the bandit balances <strong>exploration</strong> vs{" "}
          <strong>exploitation</strong> when picking a strategy. Round-robin always
          tries every arm once first; these knobs govern what happens after that.
        </p>

        <div className="reward-scale-pointer">
          <strong>Formula:</strong>{" "}
          <code>ucb = avg_reward + c · width · √(2 · ln N / count)</code>
          <ul className="col-legend">
            <li><strong>c (exploration constant)</strong> — higher = more exploration (samples all strategies longer); lower = commits to the learned winner sooner.
              <em> c=1 is textbook-balanced; c≈0.25–0.5 suits sparse feedback.</em></li>
            <li><strong>width (reward range)</strong> — the span of the reward scale, <code>b−a</code>. Rewards are explicit ±2 / inferred ±1, so the range is <strong>4</strong>. Keep this matched to your reward scale; it keeps the exploration bonus on the same scale as the rewards.
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

      {/* ── Research basis ─────────────────────────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Research basis</h2>
        <p className="admin-section-sub">
          Our score <code>ucb = avg + c · (b−a) · √(2 · ln N / count)</code> is
          standard UCB1 with two grounded adjustments: the tunable exploration
          constant <code>c</code> and the reward-range scaling <code>(b−a)</code>.
          Each piece traces directly to the literature.
        </p>

        <h3 className="admin-subhead">Core — the formula we run</h3>
        <ul className="ref-list">
          {CORE_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <span className="ref-note"> — {r.note}</span>
            </li>
          ))}
        </ul>

        <h3 className="admin-subhead">Variants — extra knobs if we extend</h3>
        <ul className="ref-list">
          {VARIANT_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <span className="ref-note"> — {r.note}</span>
            </li>
          ))}
        </ul>

        <div className="reward-scale-pointer">
          <strong>Conclusion.</strong> For standard UCB1 the only meaningful
          tunables are <code>c</code> (exploration) and <code>(b−a)</code>
          (reward-range scaling) — both exposed above; everything else
          (<code>avg</code>, <code>count</code>, <code>N</code>, the
          <code> ln</code>/<code>√</code> shape) is either live data or the
          fixed UCB1 definition, so there is nothing more to tune within UCB1
          itself. Different sources write the constant as 2, √2, or fold it into
          <code> c</code> — same algorithm, different bookkeeping — which is why
          there is no single "correct" c. If we later need to handle
          <strong> preference drift</strong> (users changing their minds over
          time), the most useful upgrade is a <strong>discounted / sliding-window
          UCB</strong> (Garivier &amp; Moulines); for richer adaptivity,
          variance-aware (UCB-V), tighter (KL-UCB), Bayesian (Thompson), or
          contextual (LinUCB) variants are the established next steps.
        </div>
      </div>
    </div>
  );
}
