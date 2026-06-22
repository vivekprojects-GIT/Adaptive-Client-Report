/**
 * ResearchTab — the project's research home.
 *
 *   1. The final goal (a per-user preference "brain" via RLHF-style feedback)
 *   2. A flow diagram / roadmap: Now → Goal, with the DATA to collect and the
 *      FORMULA to use at each stage.
 *   3. A validated library of papers (foundations → frontier), each in plain
 *      English. All links HTTP-checked to resolve.
 *
 * Lives here (not in the UCB Formula tab) so the UCB tab stays a focused tuner.
 */

// ── Evolution roadmap: Now → Goal ────────────────────────────────────────────
const ROADMAP = [
  {
    stage: "Stage 0",
    here: true,
    title: "Per-user UCB over response formats",
    summary: "Where we are today. A bandit learns which response shape each user prefers, per intent.",
    data: "Thumbs + LLM-detected signals → format reward (explicit ±2 / inferred ±1), keyed by (user, intent).",
    formula: "ucb = avg + c · (b−a) · √(2 · ln N / count)",
    papers: "Auer 2002 · Sutton & Barto · Hoeffding · Lai & Robbins",
  },
  {
    stage: "Stage 1",
    title: "Preference / dueling bandits",
    summary: "Switch from absolute scores to 'which answer was better' — exactly what a thumb really means. More data-efficient.",
    data: "Pairwise comparisons (A vs B): regenerate = old-vs-new, or show two formats and let the user pick. Store (winner, loser) per (user, intent).",
    formula: "Relative UCB: pick argmax over win-prob estimates  P(i ≻ j) = σ(s_i − s_j),  with a UCB bonus on the preference matrix.",
    papers: "Yue et al. 2012 · Bengs et al. 2021 (survey)",
  },
  {
    stage: "Stage 2",
    title: "Contextual bandit (personalization)",
    summary: "Generalize across users and situations using features, so new users aren't cold-started from scratch.",
    data: "A context vector x per turn: user-profile facets, conversation-history embedding, intent, time/device — plus the reward. Store (x, action, reward).",
    formula: "LinUCB:  a* = argmaxₐ ( xₐᵀ θ̂ₐ + α · √(xₐᵀ Aₐ⁻¹ xₐ) ).  Scale up → NeuralUCB (a network replaces the linear map).",
    papers: "Li et al. 2010 (LinUCB) · Zhou et al. 2020 (NeuralUCB) · Foster & Rakhlin 2020",
  },
  {
    stage: "Stage 3",
    title: "Per-user reward model (the RLHF reward model)",
    summary: "Learn a model of HOW this person judges answers — not just format, but content, tone, reasoning. This is the data bottleneck.",
    data: "A large pool of preference comparisons — pooled across all users, then fine-tuned per user. Volume is the hard part (sparse per-user feedback).",
    formula: "Bradley–Terry:  P(A ≻ B) = σ( r_θ(A) − r_θ(B) ).  Train r_θ by maximizing log-likelihood (cross-entropy) over the comparisons.",
    papers: "Christiano et al. 2017 · Stiennon et al. 2020",
  },
  {
    stage: "Stage 4",
    goal: true,
    title: "Generation steering — the indirect 'brain'",
    summary: "Use the learned reward model to shape the LLM's actual generation per user. The system now responds the way that individual would prefer.",
    data: "The reward model r_θ + prompts; ongoing feedback keeps it fresh online.",
    formula: "RLHF / PPO:  max_π  E[ r_θ(x,y) ] − β · KL(π ‖ π_ref).   OR DPO (no separate reward model):  optimize the policy directly from preferences.",
    papers: "Ouyang et al. 2022 (InstructGPT) · Rafailov et al. 2023 (DPO) · Munos et al. 2023 (Nash-HF)",
  },
];

// ── Paper library (all links HTTP-validated) ─────────────────────────────────
const GROUPS = [
  {
    group: "Foundations — the formula we run today",
    items: [
      { t: "Lai & Robbins (1985) — Asymptotically efficient adaptive allocation rules",
        p: "Proved the theoretical best-possible: you can't avoid testing losers more than a tiny (logarithmic) amount. UCB hits that limit.",
        u: "https://doi.org/10.1016/0196-8858(85)90002-8" },
      { t: "Hoeffding (1963) — Probability Inequalities for Sums of Bounded Random Variables",
        p: "The math rule for 'how far an average can be from the truth' — why the exploration bonus is scaled to the reward range (our ×4).",
        u: "https://doi.org/10.1080/01621459.1963.10500830" },
      { t: "Auer, Cesa-Bianchi & Fischer (2002) — Finite-time Analysis of the Multiarmed Bandit Problem",
        p: "Defines UCB1 — score = average + 'how unsure am I' bonus. The exact algorithm we run.",
        u: "https://link.springer.com/article/10.1023/A:1013689704352" },
      { t: "Sutton & Barto (2018) — Reinforcement Learning: An Introduction, §2.7",
        p: "Writes UCB with the single tunable dial c — the knob in the UCB Formula tab.",
        u: "http://incompleteideas.net/book/the-book-2nd.html" },
      { t: "Slivkins (2019) — Introduction to Multi-Armed Bandits",
        p: "Free, comprehensive modern monograph — the best single end-to-end reference.",
        u: "https://arxiv.org/abs/1904.07272" },
      { t: "Lattimore & Szepesvári (2020) — Bandit Algorithms (Cambridge)",
        p: "The rigorous modern textbook; derives UCB, range scaling, and every variant. Free PDF.",
        u: "https://tor-lattimore.com/downloads/book/book.pdf" },
    ],
  },
  {
    group: "UCB variants — other flavours of the same idea",
    items: [
      { t: "Garivier & Moulines (2011) — UCB Policies for Non-Stationary Bandit Problems",
        p: "A version that slowly FORGETS old feedback — good when preferences drift over time.",
        u: "https://arxiv.org/abs/0805.3415" },
      { t: "Audibert, Munos & Szepesvári (2009) — Exploration with variance estimates (UCB-V)",
        p: "Explores noisy/unpredictable options more, steady ones less.",
        u: "https://doi.org/10.1016/j.tcs.2009.01.016" },
      { t: "Garivier & Cappé (2011) — The KL-UCB Algorithm",
        p: "A sharper bonus that wastes even fewer tries than plain UCB1.",
        u: "https://arxiv.org/abs/1102.2490" },
    ],
  },
  {
    group: "Bayesian & information-based alternatives",
    items: [
      { t: "Thompson (1933) — On the Likelihood that One Unknown Probability Exceeds Another",
        p: "The original idea behind Thompson Sampling: 'roll dice' weighted by current belief instead of adding a bonus.",
        u: "https://doi.org/10.1093/biomet/25.3-4.285" },
      { t: "Agrawal & Goyal (2012) — Analysis of Thompson Sampling",
        p: "Modern proof that the dice-rolling approach matches UCB's guarantees. (The Beta-curves on the analytics page nod to this.)",
        u: "https://arxiv.org/abs/1111.1797" },
      { t: "Russo & Van Roy (2018) — Learning to Optimize via Information-Directed Sampling",
        p: "Picks the option that TEACHES the most per try, not just the one that looks best now.",
        u: "https://arxiv.org/abs/1403.5556" },
    ],
  },
  {
    group: "Contextual bandits — the personalization step (Stage 2)",
    items: [
      { t: "Li, Chu, Langford & Schapire (2010) — A Contextual-Bandit Approach (LinUCB)",
        p: "Uses clues about the situation (context) to choose smarter — a different best choice for different users.",
        u: "https://arxiv.org/abs/1003.0146" },
      { t: "Zhou, Li & Gu (2020) — Neural Contextual Bandits with UCB Exploration (NeuralUCB)",
        p: "Replaces the simple average with a neural network, keeping the same uncertainty-bonus idea.",
        u: "https://arxiv.org/abs/1911.04462" },
      { t: "Zhang, Zhou, Li & Gu (2021) — Neural Thompson Sampling",
        p: "The dice-rolling style powered by a neural network.",
        u: "https://arxiv.org/abs/2010.00827" },
      { t: "Foster & Rakhlin (2020) — Beyond UCB: Contextual Bandits with Regression Oracles",
        p: "Do contextual bandits efficiently with ANY prediction model, not only UCB-style bounds.",
        u: "https://arxiv.org/abs/2002.04926" },
    ],
  },
  {
    group: "Preference / dueling bandits — matches our thumbs (Stage 1)",
    items: [
      { t: "Yue, Broder, Kleinberg & Joachims (2012) — The K-armed Dueling Bandits Problem",
        p: "Learns purely from 'A was better than B' comparisons — exactly the kind of signal a thumb gives.",
        u: "https://doi.org/10.1016/j.jcss.2011.12.028" },
      { t: "Bengs, Busa-Fekete, El Mesaoudi-Paul & Hüllermeier (2021) — Dueling Bandits: A Survey",
        p: "The full modern map of preference-based online learning. Most directly relevant to our feedback model.",
        u: "https://arxiv.org/abs/1807.11398" },
    ],
  },
  {
    group: "Delayed feedback — matches our reward timing",
    items: [
      { t: "Joulani, György & Szepesvári (2013) — Online Learning under Delayed Feedback",
        p: "Handles rewards that arrive LATE — like ours, where a turn's reward often lands only on the user's next message.",
        u: "https://arxiv.org/abs/1306.0686" },
    ],
  },
  {
    group: "RLHF — the final goal (Stages 3–4)",
    items: [
      { t: "Christiano et al. (2017) — Deep Reinforcement Learning from Human Preferences",
        p: "The paper that started modern RLHF: train a reward model from human preference comparisons, then optimize against it.",
        u: "https://arxiv.org/abs/1706.03741" },
      { t: "Stiennon et al. (2020) — Learning to Summarize from Human Feedback",
        p: "Showed RLHF dramatically improves real LLM outputs — the bridge from theory to language models.",
        u: "https://arxiv.org/abs/2009.01325" },
      { t: "Ouyang et al. (2022) — Training Language Models to Follow Instructions with Human Feedback (InstructGPT)",
        p: "The recipe behind ChatGPT-style alignment: SFT → reward model → PPO. The blueprint for Stage 4.",
        u: "https://arxiv.org/abs/2203.02155" },
      { t: "Rafailov et al. (2023) — Direct Preference Optimization (DPO)",
        p: "Skips the separate reward model + RL — optimizes the policy straight from preferences. Simpler, very relevant for us.",
        u: "https://arxiv.org/abs/2305.18290" },
      { t: "Munos et al. (2023, DeepMind) — Nash Learning from Human Feedback",
        p: "Frontier work framing preference learning as a game — the cutting edge of aligning models to human feedback.",
        u: "https://arxiv.org/abs/2312.00886" },
    ],
  },
  {
    group: "Where bandits are used in the real world",
    items: [
      { t: "Bouneffouf & Rish (2019) — Survey on Practical Applications of Multi-Armed & Contextual Bandits",
        p: "A tour of bandits in recommendations, ads, clinical trials, finance — the bigger picture.",
        u: "https://arxiv.org/abs/1904.10040" },
    ],
  },
];

export default function ResearchTab() {
  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">Research & roadmap</h2>
        <p className="admin-section-sub">
          <strong>Final goal:</strong> a system that indirectly acts like an
          individual's "brain" — learning a person's preferences and judgment
          from their feedback (RLHF-style) and using it to shape every response.
          Today's bandit is the first, interpretable step toward that. Below is
          the path from here to there — the <strong>data</strong> to collect and
          the <strong>formula</strong> to use at each stage — followed by the
          validated paper library.
        </p>
      </div>

      {/* ── Flow diagram / roadmap ─────────────────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">The path: Now → Goal</h2>
        <div className="roadmap">
          {ROADMAP.map((s, i) => (
            <div key={s.stage} className="roadmap-item">
              <div className={`roadmap-card${s.here ? " is-here" : ""}${s.goal ? " is-goal" : ""}`}>
                <div className="roadmap-head">
                  <span className="roadmap-stage">{s.stage}</span>
                  {s.here && <span className="roadmap-badge here">▶ you are here</span>}
                  {s.goal && <span className="roadmap-badge goal">🎯 the goal</span>}
                </div>
                <div className="roadmap-title">{s.title}</div>
                <div className="roadmap-summary">{s.summary}</div>
                <div className="roadmap-row"><span className="roadmap-k">Data to collect</span><span>{s.data}</span></div>
                <div className="roadmap-row"><span className="roadmap-k">Formula</span><code>{s.formula}</code></div>
                <div className="roadmap-row"><span className="roadmap-k">Papers</span><span className="ref-note">{s.papers}</span></div>
              </div>
              {i < ROADMAP.length - 1 && <div className="roadmap-arrow" aria-hidden="true">↓</div>}
            </div>
          ))}
        </div>
        <div className="reward-scale-pointer">
          <strong>The real bottleneck is data, not algorithms.</strong> RLHF works
          because of huge volumes of preference labels; a single user gives only a
          handful of signals per session. So the hard problem for our goal is
          extracting maximum signal from sparse, delayed, preference-style feedback
          — which is exactly why the dueling-bandit and delayed-feedback papers
          below are the most relevant frontier for us.
        </div>
      </div>

      {/* ── Paper library ──────────────────────────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Paper library (links validated)</h2>
        {GROUPS.map((g) => (
          <div key={g.group}>
            <h3 className="admin-subhead">{g.group}</h3>
            <ul className="ref-list">
              {g.items.map((r) => (
                <li key={r.u}>
                  <a href={r.u} target="_blank" rel="noopener noreferrer">{r.t}</a>
                  <div className="ref-note">{r.p}</div>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div className="reward-scale-pointer">
          <strong>Conclusion.</strong> UCB (Stage 0) is a settled, proven method —
          the classic papers are old because the theory is done, not outdated. The
          route to the goal keeps the same explore-vs-exploit core and adds, in
          order: <strong>preference feedback</strong> (dueling bandits, Stage 1),
          <strong> context</strong> (LinUCB/NeuralUCB, Stage 2), a
          <strong> learned per-user reward model</strong> (Bradley–Terry, Stage 3),
          and finally <strong>generation steering</strong> (RLHF/PPO or DPO,
          Stage 4) — the point at which the system genuinely shapes responses to an
          individual's judgment. Each step is well-trodden research, all cited and
          link-checked above.
        </div>
      </div>
    </div>
  );
}
