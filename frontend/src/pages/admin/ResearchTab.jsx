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

// ── Method selection guide: when to use what ─────────────────────────────────
const METHODS = [
  {
    method: "Greedy / ε-greedy",
    problem: "Explore vs exploit with no context and minimal machinery.",
    when: "Tiny action sets; a quick baseline.",
    fit: "skip", fitLabel: "not for us",
    fitText: "Too crude — exploration is random, with no awareness of uncertainty.",
    papers: "Sutton & Barto §2",
  },
  {
    method: "UCB1 (+ variants)",
    problem: "Explore/exploit on a small fixed set with provable guarantees and full transparency.",
    when: "Few arms, scalar reward, you want deterministic & auditable picks.",
    fit: "now", fitLabel: "using now (Stage 0)",
    fitText: "Interpretable — we can SHOW why each arm was picked — and strong with round-robin cold-start. The right starting point.",
    papers: "Auer 2002",
  },
  {
    method: "Thompson Sampling (Bayesian)",
    problem: "Same explore/exploit, but sample from a belief distribution instead of adding a bonus.",
    when: "You want better empirical performance, natural uncertainty, easy priors, and graceful handling of delayed/batched feedback.",
    fit: "next", fitLabel: "strong alternative",
    fitText: "Often beats UCB in practice and copes better with sparse/delayed feedback (which we have). Trade-off: less transparent than UCB.",
    papers: "Thompson 1933 · Agrawal & Goyal 2012 · Russo 2018 (tutorial)",
  },
  {
    method: "Contextual bandits (LinUCB / NeuralUCB)",
    problem: "The best action DEPENDS on the situation — who the user is, the context.",
    when: "You have features and different users/contexts want different things.",
    fit: "stage2", fitLabel: "Stage 2",
    fitText: "Needed for real personalization beyond per-(user, intent) cells.",
    papers: "Li 2010 · Zhou 2020",
  },
  {
    method: "Contextual Thompson Sampling",
    problem: "Contextual + Bayesian — personalization with belief sampling.",
    when: "Personalization AND you want TS's empirical edge / uncertainty handling.",
    fit: "stage2best", fitLabel: "Stage 2 — best fit",
    fitText: "Likely our best Stage-2 choice — contextual TS tends to outperform LinUCB in practice.",
    papers: "Agrawal & Goyal 2013",
  },
  {
    method: "Dueling / Preference bandits",
    problem: "You only observe 'A was better than B' — never absolute scores.",
    when: "Feedback is comparative: thumbs, A/B, regenerate.",
    fit: "matches", fitLabel: "matches our feedback (Stage 1)",
    fitText: "Matches our signal EXACTLY. The natural first upgrade from scalar rewards.",
    papers: "Yue 2012 · Bengs 2021",
  },
  {
    method: "RL / RLHF (reward model + policy)",
    problem: "Shape a complex, structured policy (e.g. text generation) from human preference feedback.",
    when: "Action space is huge/structured (language); you want to steer generation itself, not pick from a menu.",
    fit: "goal", fitLabel: "the goal (Stages 3–4)",
    fitText: "Learn a reward model of the person, then steer the LLM's actual output. This is the indirect 'brain'.",
    papers: "Christiano 2017 · Ouyang 2022 · Rafailov 2023",
  },
];

// ── Decision flow — pick the method without confusion ────────────────────────
const DECISION = [
  { q: "Is feedback comparative ('A better than B') or an absolute score?",
    a: "Comparative → Dueling / Preference bandits. Absolute → continue below." },
  { q: "Does the best choice depend on context (who / what / when)?",
    a: "Yes → Contextual methods. No → plain (non-contextual) bandit." },
  { q: "Do you want transparency & provable bounds, or best empirical performance?",
    a: "Transparency → UCB family. Performance / priors / delayed feedback → Thompson family." },
  { q: "Is the action space huge & structured — generating text, not picking from a menu?",
    a: "Yes → RL / RLHF (reward model + policy, or DPO). No → a bandit is enough." },
];

// ── Industry context — how it's really done, and why per-user is hard ────────
const INDUSTRY = [
  {
    k: "Bandits are everywhere",
    v: "Contextual bandits / Thompson Sampling run recommendations & ads at Google, Meta, Netflix, Spotify, LinkedIn. This is mature, deployed tech — not unexplored.",
  },
  {
    k: "RLHF is preference learning",
    v: "The exact family here. It aligns every modern chat LLM (InstructGPT, DPO, Nash-HF). Heavily researched — just aimed at AGGREGATE human preference, not each end-user.",
  },
  {
    k: "Per-user data is too sparse",
    v: "A rich preference model needs thousands of labels; one user gives a handful. Big labs use POOLED models (learn across millions, condition on user features) — not per-user online learning.",
  },
  {
    k: "They chose memory over weights",
    v: "Per-user fine-tuning is costly and hard to serve, so the per-user 'brain' that actually shipped is in-context MEMORY + retrieval (ChatGPT / Gemini memory). Cheaper mechanism, same goal.",
  },
  {
    k: "Bandit menu vs generation space",
    v: "Bandits pick from a menu; LLM output is an infinite space. Cleanly combining them at scale is genuinely open — the niche this project pokes at.",
  },
  {
    k: "Sycophancy & feedback loops",
    v: "Optimizing hard to one person's thumbs creates models that just tell you what you want (sycophancy) and filter bubbles. Labs are deliberately cautious (Sharma et al. 2023).",
  },
];

// ── Who uses what in industry (public papers / eng blogs / talks) ────────────
const INDUSTRY_USAGE = [
  { co: "Yahoo", method: "Contextual bandit (LinUCB)", use: "News article selection — the seminal Li et al. 2010 paper was Yahoo's front page." },
  { co: "Netflix", method: "Contextual bandits", use: "Artwork / thumbnail personalization, row & title ranking." },
  { co: "Spotify", method: "Contextual bandits (BaRT)", use: "Home-screen recommendations, playlist / podcast ranking." },
  { co: "Microsoft", method: "Contextual bandits as a service", use: "Azure Personalizer / the Decision Service (built on Vowpal Wabbit)." },
  { co: "Google / YouTube", method: "Deep RL (off-policy REINFORCE) + bandits", use: "Video recommendations ('Top-K off-policy correction'); bandits in ads." },
  { co: "Meta", method: "Applied RL (Horizon / ReAgent) + bandits", use: "Notifications, feed & recommendation ranking." },
  { co: "LinkedIn · Amazon · Booking · DoorDash · Uber", method: "Contextual bandits", use: "Feed/notification timing, layout, recommendations." },
  { co: "OpenAI · Anthropic · Google DeepMind", method: "RLHF (+ DPO, Constitutional AI)", use: "Aligning LLMs to AGGREGATE human preference (ChatGPT, Claude, Gemini)." },
  { co: "OpenAI / Google (consumer LLMs)", method: "Agentic memory (context, not weights)", use: "Per-USER adaptation — ChatGPT / Gemini 'Memory' features." },
];

// ── Agentic path — ship-now alternative to the learned-reward-model track ─────
const AGENTIC_LANE = [
  {
    component: "1 · Profile / memory agent",
    role: "Maintains a per-user 'mental model' in readable text/JSON — preferences, style, do's & don'ts, recurring topics.",
    wiring: "New ape_user_profile doc in Mongo, seeded from the cognitive-facet analytics you already compute (structured_preference, clarity_need, preferred_format).",
  },
  {
    component: "2 · Reflection agent",
    role: "Every N turns, reads (history + thumbs + signals) and rewrites the profile: e.g. '3 down-votes on long answers → prefers concise'.",
    wiring: "A triggered orchestrator step; feed the existing per-user facet summary in as structured input to the reflection prompt so it doesn't start cold.",
  },
  {
    component: "3 · Orchestrator integration",
    role: "Injects the profile into the synthesizer prompt; the UCB bandit still picks the format as a fast statistical prior.",
    wiring: "Add the profile block in build_synthesizer_system_prompt() — same spot the strategy instruction goes. Bandit selection is unchanged; profile + bandit are complementary.",
  },
  {
    component: "4 · Critic agent",
    role: "Before sending, checks the draft for correctness & sycophancy vs the profile ('are we just agreeing?').",
    wiring: "A post-synthesis LLM check in handle_turn; log its verdict alongside the existing signals so it shows in analytics.",
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
      { t: "Russo, Van Roy, Kazerouni, Osband & Wen (2018) — A Tutorial on Thompson Sampling",
        p: "The friendly, comprehensive guide to Thompson Sampling (incl. contextual). Best starting point if we adopt TS.",
        u: "https://arxiv.org/abs/1707.02038" },
      { t: "Chapelle & Li (2011) — An Empirical Evaluation of Thompson Sampling",
        p: "Showed Thompson Sampling often beats UCB in practice — the paper that revived TS for real systems.",
        u: "https://papers.nips.cc/paper_files/paper/2011/hash/e53a0a2978c28872a4505bdb51db06dc-Abstract.html" },
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
      { t: "Agrawal & Goyal (2013) — Thompson Sampling for Contextual Bandits with Linear Payoffs",
        p: "Contextual personalization done the Bayesian (Thompson) way — likely our best Stage-2 choice.",
        u: "https://arxiv.org/abs/1209.3352" },
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
    group: "Agentic path — memory, reflection & critic (ship-now track)",
    items: [
      { t: "Park et al. (2023) — Generative Agents: Interactive Simulacra of Human Behavior",
        p: "The canonical memory + reflection agent: stores observations and periodically reflects them into higher-level beliefs. The blueprint for our profile/reflection agents.",
        u: "https://arxiv.org/abs/2304.03442" },
      { t: "Shinn et al. (2023) — Reflexion: Language Agents with Verbal Reinforcement Learning",
        p: "Learns from feedback by writing reflections in language instead of updating weights — exactly the 'model the user in language' idea.",
        u: "https://arxiv.org/abs/2303.11366" },
      { t: "Packer et al. (2023) — MemGPT: Towards LLMs as Operating Systems",
        p: "Manages long-term memory beyond the context window — relevant for an evolving per-user profile.",
        u: "https://arxiv.org/abs/2310.08560" },
      { t: "Yao et al. (2022) — ReAct: Synergizing Reasoning and Acting in Language Models",
        p: "The reason-then-act loop underneath most LLM agents — the orchestration pattern for the critic/router.",
        u: "https://arxiv.org/abs/2210.03629" },
    ],
  },
  {
    group: "LLM personalization & alignment frontier",
    items: [
      { t: "Jang et al. (2023) — Personalized Soups: Personalized LLM Alignment via Post-hoc Parameter Merging",
        p: "Per-user alignment by merging preference-tuned models — a concrete attempt at the per-person 'brain'.",
        u: "https://arxiv.org/abs/2310.11564" },
      { t: "Rame et al. (2023) — Rewarded Soups: Pareto-optimal Alignment by Interpolating Weights",
        p: "Blends multiple reward objectives instead of one — handles the fact that people weigh things differently.",
        u: "https://arxiv.org/abs/2306.04488" },
      { t: "Ong et al. (2024) — RouteLLM: Learning to Route LLMs with Preference Data",
        p: "Uses preference data to ROUTE between models/strategies — a bandit-flavoured, production-grade use of feedback.",
        u: "https://arxiv.org/abs/2406.18665" },
      { t: "Sharma et al. (2023, Anthropic) — Towards Understanding Sycophancy in Language Models",
        p: "Why optimizing to user approval is dangerous (models that just agree) — the risk our critic agent guards against.",
        u: "https://arxiv.org/abs/2310.13548" },
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

      {/* ── Recommendation: best approach for us ───────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Recommendation — the best approach for us</h2>
        <div className="unique-banner">
          <div className="unique-tag">✓ Verdict</div>
          <p>
            For our situation — <strong>sparse, comparative (thumbs), delayed
            feedback</strong>; a small menu of strategies; a POC aiming at a
            per-user "brain" — the best approach is the <strong>hybrid</strong>:
            the <strong>UCB bandit + an agentic memory/reflection layer + a
            critic</strong>, with the agent as the centerpiece. It is the only
            option that is both <strong>shippable now</strong> (no training, no
            data threshold) <em>and</em> <strong>on the path to the goal</strong>.
          </p>
        </div>

        <h3 className="admin-subhead">Why it beats each alternative (for us)</h3>
        <ul className="ref-list">
          <li><strong>🥇 UCB + agent memory + critic (the fusion)</strong>
            <div className="ref-note">Bandit answers "which format works" (provable, interpretable); the agent reasons a rich preference profile from just a few signals (what LLMs do well and bandits/RLHF can't on sparse data); the critic stops sycophancy. The only path that ships now AND becomes a "brain".</div></li>
          <li><strong>Pure UCB / Thompson</strong>
            <div className="ref-note">Too narrow — learns format stats only; can't capture style, values, or reasoning preferences. Never becomes a brain.</div></li>
          <li><strong>Contextual Thompson</strong>
            <div className="ref-note">Better stats and the right Stage-2 upgrade, but still only stats — no language-level user model.</div></li>
          <li><strong>Per-user RLHF / reward model</strong>
            <div className="ref-note">Most powerful, but premature — data-hungry and expensive; we lack the per-user volume. It's the destination, not the first move.</div></li>
          <li><strong>Pure agent / memory (no bandit)</strong>
            <div className="ref-note">Loses the grounded, provable reward signal; can drift and hallucinate preferences. The bandit keeps it honest.</div></li>
        </ul>

        <div className="reward-scale-pointer">
          <strong>First move:</strong> add the <strong>profile + reflection agent</strong>,
          seeded from the cognitive-facet analytics we already compute
          (<code>compute_user_cognitive_profile</code>), and inject that profile into
          the synthesizer prompt — keeping the UCB bandit as-is for format selection.
          That turns existing stats into a readable per-user "brain" in days, not a
          research project. <strong>Graduate later:</strong> contextual Thompson
          (Stage 2) once we have enough users to learn across them; a learned reward
          model + DPO (Stages 3–4) only once feedback volume justifies the cost.
        </div>
      </div>

      {/* ── Method selection guide ─────────────────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Which method, when? (we are NOT UCB-only)</h2>
        <p className="admin-section-sub">
          UCB is just our starting point — chosen because it's simple,
          interpretable, and provably good for a cold start. But the right tool
          depends on the sub-problem. Here's the full menu, what each one solves,
          when to reach for it, and how it fits our path to the goal.
        </p>
        <div className="method-grid">
          {METHODS.map((m) => (
            <div key={m.method} className={`method-card fit-${m.fit}`}>
              <div className="method-head">
                <span className="method-name">{m.method}</span>
                <span className={`method-badge fit-${m.fit}`}>{m.fitLabel}</span>
              </div>
              <div className="method-row"><span className="method-k">Problem</span><span>{m.problem}</span></div>
              <div className="method-row"><span className="method-k">Use when</span><span>{m.when}</span></div>
              <div className="method-row"><span className="method-k">Fit for us</span><span>{m.fitText}</span></div>
              <div className="method-row"><span className="method-k">Papers</span><span className="ref-note">{m.papers}</span></div>
            </div>
          ))}
        </div>

        <h3 className="admin-subhead">Decision flow — answer these in order</h3>
        <ol className="decision-flow">
          {DECISION.map((d, i) => (
            <li key={i}>
              <span className="decision-q">{d.q}</span>
              <span className="decision-a">{d.a}</span>
            </li>
          ))}
        </ol>

        <div className="reward-scale-pointer">
          <strong>What we use, and why — no confusion.</strong> Our feedback is
          <em> comparative</em> (thumbs) and <em>delayed</em> (lands next turn),
          and our action set is a <em>small menu</em> of strategies — so a bandit,
          not full RL, is correct for now. We run <strong>UCB</strong> first
          because it's transparent and easy to trust in a demo. The clean
          progression: <strong>UCB → Preference/Dueling (Stage 1) → Contextual
          Thompson Sampling (Stage 2) → per-user reward model (Stage 3) → RLHF/DPO
          generation steering (Stage 4)</strong>. We switch from UCB to the
          Thompson / contextual / RLHF family exactly when the data justifies it —
          not all at once.
        </div>
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

      {/* ── Agentic path (ship-now alternative) ────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Agentic path — a ship-now alternative to the reward-model track</h2>

        <div className="unique-banner">
          <div className="unique-tag">★ Our unique approach</div>
          <p>
            Most systems pick <em>one</em> tool: a <strong>bandit</strong> (statistics only),
            an <strong>agent/memory</strong> (language only), or <strong>RLHF</strong> (weights only).
            We <strong>fuse three</strong> into one loop:
          </p>
          <div className="unique-fuse">
            <span className="unique-chip">UCB bandit<small>fast, provable, interpretable prior on <em>which format</em> works</small></span>
            <span className="unique-plus">+</span>
            <span className="unique-chip">Agent memory + reflection<small>rich language model of <em>who</em> the user is &amp; <em>why</em> they prefer things — generalises from sparse feedback</small></span>
            <span className="unique-plus">+</span>
            <span className="unique-chip">Critic agent<small>guards against sycophancy &amp; feedback loops</small></span>
          </div>
          <p className="unique-why">
            The <strong>bandit grounds the agent</strong> in real reward statistics; the
            <strong> agent gives the bandit context</strong> it can't represent (style, values,
            history); the <strong>critic keeps it honest</strong>. None of the three alone is a
            per-user "brain" — the <strong>fusion</strong> is the bet. It's interpretable and
            ship-now (no training), unlike per-user RLHF.
          </p>
        </div>

        <p className="admin-section-sub">
          Stages 3–4 (learn a reward model, then RLHF) are data-hungry and slow.
          A parallel, cheaper track gets a working preference "brain" <em>now</em>:
          instead of learning weights, an <strong>agent maintains the user model
          in language</strong> and the LLM reasons it from sparse feedback. This is
          the same approach big labs shipped for per-user adaptation (memory).
        </p>
        <div className="method-grid">
          {AGENTIC_LANE.map((a) => (
            <div key={a.component} className="method-card fit-now">
              <div className="method-head">
                <span className="method-name">{a.component}</span>
              </div>
              <div className="method-row"><span className="method-k">Role</span><span>{a.role}</span></div>
              <div className="method-row"><span className="method-k">Wires into</span><span>{a.wiring}</span></div>
            </div>
          ))}
        </div>
        <div className="roadmap-arrow" aria-hidden="true" style={{ textAlign: "center" }}>↓</div>
        <div className="reward-scale-pointer">
          <strong>Agentic track vs reward-model track.</strong> The agentic path
          (memory + reflection + critic) is <strong>interpretable, cheap, and
          shippable today</strong> — the profile is readable text, nothing is
          trained — but it has <strong>no convergence guarantees</strong> and can
          drift or hallucinate preferences (hence the critic). The learned-reward
          track (Stages 3–4) is <strong>principled but data-hungry and
          expensive</strong>. Recommended: <strong>run the agentic track now</strong>
          alongside the UCB bandit (bandit = fast format prior; profile = rich
          preferences; critic = safety), and graduate to a learned reward model
          only when accumulated feedback justifies it. See the "Agentic path"
          papers below (Generative Agents, Reflexion, MemGPT, ReAct).
        </div>
      </div>

      {/* ── Industry context ───────────────────────────────────────────── */}
      <div className="admin-section">
        <h2 className="admin-section-title">Industry context — how it's really done (and why per-user is hard)</h2>
        <p className="admin-section-sub">
          The components are all industrial-grade; what's uncommon is our exact
          combination — a lightweight, interpretable, per-user learner steering an
          LLM. These are the real reasons big labs solve personalization differently.
        </p>
        <ul className="ref-list">
          {INDUSTRY.map((x) => (
            <li key={x.k}>
              <strong>{x.k}.</strong> <span className="ref-note">{x.v}</span>
            </li>
          ))}
        </ul>

        <h3 className="admin-subhead">Who uses what (public papers / eng blogs / talks)</h3>
        <table className="usage-table">
          <thead>
            <tr><th>Company</th><th>Method family</th><th>Personalization use case</th></tr>
          </thead>
          <tbody>
            {INDUSTRY_USAGE.map((r) => (
              <tr key={r.co}>
                <td><strong>{r.co}</strong></td>
                <td>{r.method}</td>
                <td className="ref-note">{r.use}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="ref-note" style={{ marginTop: "6px" }}>
          The pattern: recommendations/ads → contextual bandits &amp; RL; LLM
          alignment → RLHF/DPO (aimed at everyone, not per-user); per-user LLM
          adaptation → memory/context, not bandits. Nobody does per-user
          bandit→LLM the way we frame it — the big players split it; our niche is
          fusing them. (Public descriptions only — production internals aren't
          fully disclosed and change over time.)
        </p>
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
