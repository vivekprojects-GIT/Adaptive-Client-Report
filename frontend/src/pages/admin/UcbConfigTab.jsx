import { useEffect, useState } from "react";
import { api } from "../../api.js";

// Research references behind the UCB formula — shown in the tab so the
// formula choices are traceable to the literature. `plain` = layman's terms.
const CORE_REFS = [
  {
    title: "Auer, Cesa-Bianchi & Fischer (2002) — Finite-time Analysis of the Multiarmed Bandit Problem",
    plain: "The recipe we use. It proved that if you score each option by its average result PLUS a 'how unsure am I about this one' bonus, you reliably find the best option while wasting very few tries.",
    url: "https://link.springer.com/article/10.1023/A:1013689704352",
  },
  {
    title: "Sutton & Barto (2018) — Reinforcement Learning: An Introduction, §2.7",
    plain: "A famous textbook that writes the same idea with a single dial called c for 'how adventurous to be.' That dial is the c knob in the form above.",
    url: "http://incompleteideas.net/book/the-book-2nd.html",
  },
  {
    title: "Hoeffding (1963) — Probability Inequalities for Sums of Bounded Random Variables",
    plain: "A math rule for 'how far can an average realistically be from the truth.' It's the reason the exploration bonus must be scaled to the size of your scores (our ×4 reward-range factor).",
    url: "https://doi.org/10.1080/01621459.1963.10500830",
  },
  {
    title: "Lai & Robbins (1985) — Asymptotically efficient adaptive allocation rules",
    plain: "Proved the best any method can possibly do: you can't avoid testing the losers more than a tiny (logarithmic) amount. UCB hits that ideal limit.",
    url: "https://doi.org/10.1016/0196-8858(85)90002-8",
  },
  {
    title: "Lattimore & Szepesvári (2020) — Bandit Algorithms (Cambridge Univ. Press)",
    plain: "The modern go-to textbook that explains UCB and all its cousins in one place. Free PDF — the best single starting point.",
    url: "https://tor-lattimore.com/downloads/book/book.pdf",
  },
];

const VARIANT_REFS = [
  {
    title: "Garivier & Moulines (2011) — UCB Policies for Switching Bandit Problems",
    plain: "A version that slowly FORGETS old feedback — useful when people change their minds over time, so the bandit doesn't cling to a preference from months ago.",
    url: "https://arxiv.org/abs/0805.3415",
  },
  {
    title: "Audibert, Munos & Szepesvári (2009) — Exploration with variance estimates (UCB-V)",
    plain: "Explores the unpredictable/noisy options more and the steady, consistent ones less — it pays attention to how much results bounce around.",
    url: "https://doi.org/10.1016/j.tcs.2009.01.016",
  },
  {
    title: "Garivier & Cappé (2011) — The KL-UCB Algorithm",
    plain: "A sharper, tighter version of the bonus that wastes even fewer tries than plain UCB1.",
    url: "https://arxiv.org/abs/1102.2490",
  },
  {
    title: "Agrawal & Goyal (2012) — Analysis of Thompson Sampling",
    plain: "A different style: instead of adding a bonus, it 'rolls dice' weighted by what it currently believes about each option. Often works as well or better. (The Beta-curves on the analytics page nod to this idea.)",
    url: "https://arxiv.org/abs/1111.1797",
  },
  {
    title: "Li, Chu, Langford & Schapire (2010) — A Contextual-Bandit Approach (LinUCB)",
    plain: "Uses extra clues about the situation (the 'context') to choose smarter — e.g. a different best strategy for different kinds of users. The next step if we ever feed user features into selection.",
    url: "https://arxiv.org/abs/1003.0146",
  },
];

// Newer work — UCB isn't replaced, it's scaled up to modern ML.
const RECENT_REFS = [
  {
    title: "Zhou, Li & Gu (2020) — Neural Contextual Bandits with UCB-based Exploration (NeuralUCB)",
    plain: "Swaps the simple average for a neural network, but keeps the exact same 'add an uncertainty bonus' idea. UCB for the deep-learning era.",
    url: "https://arxiv.org/abs/1911.04462",
  },
  {
    title: "Zhang, Zhou, Li & Gu (2021) — Neural Thompson Sampling",
    plain: "The dice-rolling (Thompson) style, but powered by a neural network instead of simple statistics.",
    url: "https://arxiv.org/abs/2010.00827",
  },
  {
    title: "Foster & Rakhlin (2020) — Beyond UCB: Optimal and Efficient Contextual Bandits with Regression Oracles",
    plain: "Shows you can do contextual bandits efficiently using ANY prediction model, not only UCB-style bounds — a more flexible modern recipe.",
    url: "https://arxiv.org/abs/2002.04926",
  },
  {
    title: "Russo & Van Roy (2018) — Learning to Optimize via Information-Directed Sampling",
    plain: "Picks the option that will TEACH it the most per try, not just the one that looks best right now — a smarter way to balance explore vs exploit.",
    url: "https://arxiv.org/abs/1403.5556",
  },
];

// Advanced & latest — surveys + frontier directions, several directly
// relevant to how THIS app collects feedback.
const ADVANCED_REFS = [
  {
    title: "Slivkins (2019) — Introduction to Multi-Armed Bandits (Foundations & Trends in ML)",
    plain: "A free, modern, comprehensive monograph covering the whole bandit field end to end — the best single deep-dive if you want everything in one document.",
    url: "https://arxiv.org/abs/1904.07272",
  },
  {
    title: "Bengs, Busa-Fekete, El Mesaoudi-Paul & Hüllermeier (2021) — Preference-based Online Learning with Dueling Bandits: A Survey (JMLR)",
    plain: "Most relevant to us: bandits that learn from 'which answer was better' feedback — exactly the kind of signal a thumbs-up/down gives — instead of absolute numeric scores.",
    url: "https://arxiv.org/abs/1807.11398",
  },
  {
    title: "Munos et al. (2023, DeepMind) — Nash Learning from Human Feedback",
    plain: "Frontier work linking preference feedback to aligning large language models (RLHF). The modern descendant of bandit ideas — directly in our problem space, since we learn from human feedback on LLM answers.",
    url: "https://arxiv.org/abs/2312.00886",
  },
  {
    title: "Joulani, György & Szepesvári (2013) — Online Learning under Delayed Feedback (ICML)",
    plain: "Handles rewards that arrive LATE rather than immediately — relevant to us, because a turn's reward often only lands on the user's NEXT message, not right away.",
    url: "https://arxiv.org/abs/1306.0686",
  },
  {
    title: "Bouneffouf & Rish (2019) — A Survey on Practical Applications of Multi-Armed and Contextual Bandits",
    plain: "A tour of where bandits are actually used in the real world — recommendations, ads, clinical trials, finance — useful for seeing the bigger picture beyond the theory.",
    url: "https://arxiv.org/abs/1904.10040",
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
        <h2 className="admin-section-title">Research basis (in plain English)</h2>
        <p className="admin-section-sub">
          Our score <code>ucb = avg + c · (b−a) · √(2 · ln N / count)</code> is
          standard UCB1 with two grounded adjustments: the exploration dial
          <code> c</code> and the reward-range scaling <code>(b−a)</code>. Below,
          each paper is summarised so anyone can follow why the formula looks the
          way it does.
        </p>

        <div className="reward-scale-pointer">
          <strong>Why are the core papers old?</strong> UCB is a mathematically
          <em> settled</em> method — its guarantees were proven in 1963, 1985 and
          2002 and are still correct, so the classic formula never needed
          replacing. Newer research (bottom section) doesn't replace it; it
          <strong> scales it up</strong> to neural networks, context, and
          changing preferences.
        </div>

        <h3 className="admin-subhead">Core — the formula we actually run</h3>
        <ul className="ref-list">
          {CORE_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <div className="ref-note">{r.plain}</div>
            </li>
          ))}
        </ul>

        <h3 className="admin-subhead">Variants — other flavours of the same idea</h3>
        <ul className="ref-list">
          {VARIANT_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <div className="ref-note">{r.plain}</div>
            </li>
          ))}
        </ul>

        <h3 className="admin-subhead">Recent research (2018–2021) — UCB in the ML era</h3>
        <ul className="ref-list">
          {RECENT_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <div className="ref-note">{r.plain}</div>
            </li>
          ))}
        </ul>

        <h3 className="admin-subhead">Advanced &amp; latest — surveys + frontier (some directly relevant to us)</h3>
        <ul className="ref-list">
          {ADVANCED_REFS.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              <div className="ref-note">{r.plain}</div>
            </li>
          ))}
        </ul>

        <div className="reward-scale-pointer">
          <strong>Conclusion.</strong> For standard UCB1 the only real dials are
          <code> c</code> (how adventurous) and <code>(b−a)</code> (reward scale)
          — both exposed above; everything else is live data or the fixed UCB1
          definition, so there's nothing more to tune within UCB1 itself.
          Different textbooks write the constant as 2, √2, or fold it into
          <code> c</code> — same algorithm, different bookkeeping — which is why
          there's no single "correct" c. The classic papers are old because the
          theory is settled, not outdated; recent work (NeuralUCB, Neural
          Thompson, Beyond-UCB, Information-Directed Sampling) keeps the same
          explore-vs-exploit core and adds machine learning on top. The most
          useful upgrade for us specifically would be a
          <strong> discounted / sliding-window UCB</strong> if users' preferences
          start drifting over time.
        </div>
      </div>
    </div>
  );
}
