import InfoHint from "./InfoHint.jsx";

/**
 * UserProfileCard — hero panel showing all 12 behavioral facets for one user.
 *
 * Layout:
 *   ╭─────────────────────────────────────────────────────────────────╮
 *   │  COGNITIVE PROFILE · demo_user                                  │
 *   │                                                                 │
 *   │   ┌─ HERO ─────┐    ┌─ HERO ──────┐    ┌─ HERO ──────┐          │
 *   │   │ Offer      │    │ Decision    │    │ Top topic   │          │
 *   │   │ readiness  │    │ stage       │    │             │          │
 *   │   │   0.96     │    │ Action-     │    │ general     │          │
 *   │   │   Ready    │    │ ready       │    │ score 0.87  │          │
 *   │   └────────────┘    └─────────────┘    └─────────────┘          │
 *   │                                                                 │
 *   │  Facet grid: Intent · Engagement · Format · Structured ·         │
 *   │              Clarity · Friction · Positive · Momentum ·          │
 *   │              Learning confidence                                 │
 *   ╰─────────────────────────────────────────────────────────────────╯
 *
 * Each facet badge:
 *   - small uppercase label
 *   - value (the categorical or numeric punchline)
 *   - tiny score bar or footnote
 *
 * All facets are *behavioral*, never psychological. The card explicitly
 * surfaces things like "prefers structured layouts" or "in evaluation stage",
 * never "user is anxious" or "user is risk-averse".
 */
export default function UserProfileCard({ profile, userLabel }) {
  if (!profile) return null;

  const readyTier =
    profile.offer_readiness_score >= 0.7 ? "ready" :
    profile.offer_readiness_score >= 0.5 ? "likely" :
    profile.offer_readiness_score >= 0.3 ? "nurture" : "early";

  return (
    <div className="profile-card">
      <div className="profile-head">
        <div className="profile-title">
          <span className="profile-eyebrow">Cognitive profile</span>
          <h2>{profile.display_name || userLabel || profile.user_id_hash}</h2>
          <code className="profile-hash" title="SHA-256 hash — the only identifier persisted in the analytics layer">
            {profile.user_id_hash}
          </code>
        </div>
        <div className="profile-meta">
          <span className="profile-meta-item">
            <span className="meta-label">Bandit pulls</span>
            <span className="meta-value">{profile.total_bandit_pulls}</span>
          </span>
          <span className="profile-meta-item">
            <span className="meta-label">Tracked topics</span>
            <span className="meta-value">{profile.tracked_topics}</span>
          </span>
          <span className="profile-meta-item">
            <span className="meta-label">Last seen</span>
            <span className="meta-value">{relativeTime(profile.last_activity_ts)}</span>
          </span>
        </div>
      </div>

      {/* Three hero metrics */}
      <div className="profile-hero-row">
        <HeroTile
          label="Offer readiness"
          tier={readyTier}
          score={profile.offer_readiness_score}
          headline={profile.offer_readiness_label}
          sub="0.35×interest + 0.25×momentum + 0.20×stage + 0.20×engagement"
          info={<>
            Stage-gated composite. <code>raw = 0.35·interest + 0.30·recency + 0.20·engagement + 0.15·stage</code>,
            then <code>readiness = raw × decision_stage_score</code>. The multiplicative gate means
            a user in Awareness <em>can't</em> be Ready no matter how engaged.
            <br/><strong>Ready</strong> ≥ 0.70 · <strong>Likely</strong> ≥ 0.50 · <strong>Nurture</strong> ≥ 0.30 · <strong>Too early</strong> &lt; 0.30.
          </>}
        />
        <HeroTile
          label="Decision stage"
          tier={tierForStage(profile.decision_stage)}
          score={profile.decision_stage_score}
          headline={profile.decision_stage || "Unknown"}
          sub={`Recent intent mix — ${formatIntentMix(profile.intent_distribution)}`}
          info={<>
            Inferred from the last 10 intents. Precedence:
            <strong> Support-needed</strong> (≥40% Troubleshooting),
            <strong> Action-ready</strong> (≥40% Decision/Recommendation),
            <strong> Evaluation</strong> (≥40% Comparison/Evaluation),
            <strong> Awareness</strong> (≥50% Definitional),
            else <strong>Exploration</strong>.
          </>}
        />
        <HeroTile
          label="Top topic"
          tier="info"
          score={profile.topic_interest_score}
          headline={profile.top_topic || "—"}
          sub={`interest_score = ${fmt(profile.topic_interest_score)}`}
          info={<>
            The topic with the highest <code>interest_score</code> from
            <code> ape_user_topic_interest</code>. Score blends 40% frequency,
            25% recency, 25% engagement, 10% follow-up depth — all derived
            from the user's last 30 days of activity.
          </>}
        />
      </div>

      {/* Facet grid — the other 9 facets */}
      <div className="profile-facet-grid">
        <FacetTile
          label="Intent pattern"
          value={profile.dominant_intent || "—"}
          footnote={`Dominant of ${Object.keys(profile.intent_distribution || {}).length} intents`}
          info={<>The intent the user fires most often. Drawn from <code>ape_turn_record.intent</code> counts. A user with mostly <em>Decision</em> is action-oriented; mostly <em>Definitional</em> means they're learning basics.</>}
        />
        <FacetTile
          label="Engagement depth"
          value={profile.engagement_depth}
          score={profile.engagement_score}
          footnote={`Max follow-ups (30d): ${profile.max_followups_30d}`}
          info={<>How deep they go on a single topic. <strong>High</strong> = max 30-day count ≥ 8. <strong>Medium</strong> ≥ 3. <strong>Low</strong> &lt; 3. A casual one-off question is Low; 12 turns on retirement is High.</>}
        />
        <FacetTile
          label="Format preference"
          value={pretty(profile.preferred_format) || "—"}
          footnote={`μ=${fmt(profile.preferred_format_avg_reward)} over ${profile.preferred_format_count} pulls`}
          info={<>The strategy that wins for this user — picked by <code>argmax(avg_reward × min(count/5, 1))</code>. The count damping prevents a single high-reward pull from winning.</>}
        />
        <FacetTile
          label="Structured-thinking"
          value={profile.structured_preference}
          score={profile.structured_score}
          footnote={`Structured μ=${fmt(profile.structured_avg_reward)} (n=${profile.structured_pull_count}) vs paragraph μ=${fmt(profile.paragraph_avg_reward)} (n=${profile.paragraph_pull_count})`}
          info={<>Tables/bullets vs prose. We weight reward by pull count for each group; a 0.20 gap flips the label. <strong>Structured</strong> means tables/cards/steps. <strong>Paragraph</strong> means prose/analogy. <strong>Mixed</strong> = within 0.20 of each other.</>}
        />
        <FacetTile
          label="Clarity need"
          value={profile.clarity_need}
          tone={profile.clarity_need === "High" ? "warn" : "ok"}
          footnote={`${profile.clarity_signal_count} clarity signals seen`}
          info={<>How often the user signals confusion. Counts <code>regenerate_click</code>, <code>format_change_request</code>, <code>reask_same_question</code>. <strong>High</strong> ≥ 5 signals — consider simpler defaults for them.</>}
        />
        <FacetTile
          label="Friction signals"
          value={profile.friction_signal_count}
          tone={profile.friction_signal_count > 3 ? "warn" : "ok"}
          footnote="thumbs_down / regenerate / abandon / correction"
          info={<>Hard negative signals: <code>thumbs_down</code>, <code>regenerate_click</code>, <code>session_abandon</code>, <code>content_correction</code>, plus turns with normalized_reward &lt; -0.3. High friction users are candidates for instruction refinement on their dominant topics.</>}
        />
        <FacetTile
          label="Positive engagement"
          value={profile.positive_signal_count}
          tone={profile.positive_signal_count > 0 ? "pos" : "neutral"}
          footnote="thumbs_up / copy / it_worked / deeper_question"
          info={<>Hard positive signals: <code>thumbs_up</code>, <code>copy_save</code>, <code>it_worked_statement</code>, <code>deeper_question</code>, plus turns with normalized_reward ≥ 0.5. High count = the system is working for this user.</>}
        />
        <FacetTile
          label="Recency momentum"
          value={profile.recency_momentum}
          score={profile.recency_score}
          footnote={`${profile.turns_last_3d} turns in last 3d · ${profile.turns_last_30d} in last 30d`}
          info={<>Are they hot right now? Compares per-day rate in the last 3 days vs 30-day baseline. <strong>High</strong> = ≥1.5× — they're accelerating. <strong>Medium</strong> ≥ 0.7×. <strong>Low</strong> means they're going quiet.</>}
        />
        <FacetTile
          label="Learning confidence"
          value={profile.learning_confidence}
          score={profile.learning_confidence_score}
          footnote={`${profile.total_bandit_pulls} total pulls — ${
            profile.learning_confidence === "High"
              ? "personalization is reliable"
              : profile.learning_confidence === "Medium"
              ? "personalization is emerging"
              : "still in cold-start — explore widely"
          }`}
          info={<>How much data backs this user's personalization. <strong>High</strong> = ≥20 total bandit pulls. <strong>Medium</strong> ≥ 8. <strong>Low</strong> = still cold-start — treat preferences as tentative.</>}
        />
      </div>

      <div className="profile-footer">
        Behavioral facets only — no psychological labels, no raw queries.
        All scores derive from <code>ape_turn_record</code>, <code>ape_user_bandit_state</code>,
        and <code>ape_user_topic_interest</code>.
      </div>
    </div>
  );
}

// ---------- Sub-components ----------

function HeroTile({ label, headline, sub, score, tier, info }) {
  return (
    <div className={`hero-tile hero-tile-${tier}`}>
      <div className="hero-label">
        {label}
        {info && <InfoHint width={360}>{info}</InfoHint>}
      </div>
      <div className="hero-headline">{headline}</div>
      {score != null && (
        <div className="hero-score-row">
          <div className="hero-score-bar">
            <div
              className="hero-score-fill"
              style={{ width: `${Math.max(0, Math.min(1, Number(score) || 0)) * 100}%` }}
            />
          </div>
          <span className="hero-score-num">{fmt(score)}</span>
        </div>
      )}
      {sub && <div className="hero-sub">{sub}</div>}
    </div>
  );
}

function FacetTile({ label, value, score, footnote, tone = "neutral", info }) {
  return (
    <div className={`facet-tile tone-${tone}`}>
      <div className="facet-tile-label">
        {label}
        {info && <InfoHint width={320}>{info}</InfoHint>}
      </div>
      <div className="facet-tile-value">{value ?? "—"}</div>
      {score != null && (
        <div className="facet-tile-bar">
          <div
            className="facet-tile-bar-fill"
            style={{ width: `${Math.max(0, Math.min(1, Number(score) || 0)) * 100}%` }}
          />
        </div>
      )}
      {footnote && <div className="facet-tile-footnote">{footnote}</div>}
    </div>
  );
}

// ---------- Helpers ----------

function tierForStage(stage) {
  switch (stage) {
    case "Action-ready":    return "ready";
    case "Evaluation":      return "likely";
    case "Exploration":     return "nurture";
    case "Awareness":       return "early";
    case "Support-needed":  return "warn";
    default:                return "info";
  }
}

function formatIntentMix(dist) {
  if (!dist) return "—";
  const entries = Object.entries(dist).slice(0, 3);
  if (!entries.length) return "—";
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  return entries.map(([k, v]) => `${k} ${Math.round(100 * v / total)}%`).join(" · ");
}

function pretty(s) {
  if (!s) return s;
  return String(s).replace(/_/g, " ");
}

function fmt(v) {
  if (v == null) return "—";
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(2);
}

function relativeTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const diffMs = Date.now() - d.getTime();
  const m = Math.round(diffMs / 60000);
  if (m < 1)    return "just now";
  if (m < 60)   return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24)   return `${h}h ago`;
  const days = Math.round(h / 24);
  return `${days}d ago`;
}
