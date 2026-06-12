/**
 * PlatformOverviewCard — macro view across ALL users in the window.
 *
 * Layout:
 *   ┌─ PLATFORM OVERVIEW · last 30 days ──────────────────────────┐
 *   │  [7 users] [261 turns] [21 topics] [16 strategies]          │
 *   │                                                             │
 *   │  ┌──── Top topics ────┐  ┌──── Top strategies ──────┐       │
 *   │  │ roth_ira  ████ 3   │  │ decision_card  0.83 ▓▓▓ │       │
 *   │  │ compound  ███  2   │  │ comparison_t.  0.73 ▓▓  │       │
 *   │  └────────────────────┘  └─────────────────────────┘       │
 *   │                                                             │
 *   │  ┌─ Decision-stage funnel ─┐  ┌─ Readiness ─┐               │
 *   │  │ Action-ready  ▓▓   2    │  │ Ready    2   │               │
 *   │  │ Evaluation    ▓    1    │  │ Likely   1   │               │
 *   │  │ Exploration   ▓▓   2    │  │ Nurture  2   │               │
 *   │  │ Awareness     ▓▓   2    │  │ Too early 2  │               │
 *   │  └─────────────────────────┘  └──────────────┘               │
 *   │                                                             │
 *   │  Intent mix: Comparison 27% · Decision 21% · …              │
 *   └─────────────────────────────────────────────────────────────┘
 *
 * No per-user identifiers — only aggregates. Pairs with the single-user
 * Inspect view below.
 */
import InfoHint from "./InfoHint.jsx";
import MiniLineChart from "./MiniLineChart.jsx";

export default function PlatformOverviewCard({
  data,
  windowLabel = "",
  platformDailySeries = null,   // [{date, total_turns, unique_users}]
  topicsDailySeries   = null,   // [{topic, series: [{date, count}]}]
}) {
  if (!data) return null;

  const maxTopicUsers = Math.max(...(data.by_topic || []).map((t) => t.total_users), 1);
  const maxStratPulls = Math.max(...(data.by_strategy || []).map((s) => s.total_pulls), 1);
  const maxStageCount = Math.max(...(data.stage_funnel || []).map((s) => s.count), 1);
  const maxReadyCount = Math.max(...(data.readiness_funnel || []).map((r) => r.count), 1);

  return (
    <div className="platform-card">
      <div className="platform-head">
        <div>
          <span className="profile-eyebrow">Platform overview</span>
          <h2>
            All users <span className="window-tag">{windowLabel}</span>
          </h2>
        </div>
        <div className="platform-numbers">
          <PlatformNumber value={data.total_active_users} label="Active users" />
          <PlatformNumber value={data.total_turns} label="Turns" />
          <PlatformNumber value={data.total_topics} label="Topics" />
          <PlatformNumber value={data.total_strategies} label="Strategies pulled" />
        </div>
      </div>

      {/* Activity trend chart — daily turns across the window */}
      {platformDailySeries && platformDailySeries.length > 0 && (
        <div className="trend-tile">
          <div className="trend-tile-head">
            <span>
              Activity trend
              <InfoHint width={300}>
                Total <strong>turns per day</strong> across all users in this window.
                Hover any point to see the exact count. Rising = engagement growing;
                falling = users dropping off. This is the simplest gut-check for product health.
              </InfoHint>
            </span>
            <span className="trend-tile-totals">
              {sum(platformDailySeries.map((d) => d.total_turns))} turns total
            </span>
          </div>
          <MiniLineChart
            data={platformDailySeries.map((d) => ({ date: d.date, value: d.total_turns }))}
            width={640}
            height={88}
            color="#d76a35"
            yLabel="turns/day"
            formatValue={(v) => `${v} turn${v === 1 ? "" : "s"}`}
          />
        </div>
      )}

      {/* Two-column: top topics + top strategies */}
      <div className="platform-cols-2">
        <div className="platform-block">
          <div className="platform-block-head">
            Top topics by user reach
            <InfoHint width={320}>
              Ranked by <strong>unique users</strong> then sum of interest_score.
              The bar shows user reach; the sub-text shows avg interest and turn volume.
              "1 user" cells are weaker evidence than "3 users" cells with the same score.
            </InfoHint>
          </div>
          <ol className="platform-ranklist">
            {(data.by_topic || []).map((t) => (
              <li key={t.topic}>
                <div className="rank-row">
                  <span className="rank-name">
                    <span className="topic-chip">{t.topic}</span>
                  </span>
                  <span className="rank-bar-wrap">
                    <span
                      className="rank-bar"
                      style={{ width: `${(t.total_users / maxTopicUsers) * 100}%` }}
                    />
                  </span>
                  <span className="rank-num">{t.total_users}<span className="rank-num-unit"> users</span></span>
                </div>
                <div className="rank-sub">
                  avg interest {fmt(t.avg_interest_score)} · {t.turns_in_window} turns · μ-reward {fmt(t.avg_reward)}
                </div>
              </li>
            ))}
            {(data.by_topic || []).length === 0 && (
              <li className="rank-empty">No topic data in window.</li>
            )}
          </ol>
          {/* Per-topic trend chart — one line per top-N topic */}
          {topicsDailySeries && topicsDailySeries.length > 0 && (
            <div className="trend-tile">
              <div className="trend-tile-head">
                <span>
                  Topic trends
                  <InfoHint width={320}>
                    Daily turns for the top {topicsDailySeries.length} topics over this window.
                    Hover to compare same-day counts. Use this to spot topics
                    <strong> heating up</strong> (rising line) vs <strong>cooling off</strong>
                    (falling line) — instruction or outreach focus often follows.
                  </InfoHint>
                </span>
              </div>
              <MiniLineChart
                series={topicsDailySeries.map((t) => ({
                  name:   t.topic,
                  points: (t.series || []).map((p) => ({ date: p.date, value: p.count })),
                }))}
                width={640}
                height={120}
                showLegend
                formatValue={(v) => `${v} turn${v === 1 ? "" : "s"}`}
              />
            </div>
          )}
        </div>

        <div className="platform-block">
          <div className="platform-block-head">
            Top strategies (popularity × reward)
            <InfoHint width={340}>
              Strategies ranked by <code>avg_reward × log(pulls + 1)</code> — rewards
              that have been validated by volume. The big number is μ-reward
              (average normalized_reward in [-1, +1]); a strategy with μ=0.83 over
              40 pulls is more trustworthy than one with μ=0.95 over 2.
            </InfoHint>
          </div>
          <ol className="platform-ranklist">
            {(data.by_strategy || []).map((s) => (
              <li key={s.strategy}>
                <div className="rank-row">
                  <span className="rank-name">{prettyName(s.strategy)}</span>
                  <span className="rank-bar-wrap">
                    <span
                      className="rank-bar rank-bar-strategy"
                      style={{ width: `${(s.total_pulls / maxStratPulls) * 100}%` }}
                    />
                  </span>
                  <span className="rank-num">
                    {fmt(s.avg_reward)}<span className="rank-num-unit"> μ</span>
                  </span>
                </div>
                <div className="rank-sub">
                  {s.total_pulls} pulls · {s.unique_users} users · {s.unique_cells} cells
                </div>
              </li>
            ))}
            {(data.by_strategy || []).length === 0 && (
              <li className="rank-empty">No strategies pulled yet.</li>
            )}
          </ol>
        </div>
      </div>

      {/* Stage + readiness funnels */}
      <div className="platform-cols-2">
        <div className="platform-block">
          <div className="platform-block-head">
            Decision-stage funnel
            <InfoHint width={340}>
              Where users are in their buying journey, inferred from each user's recent intents.
              <strong> Awareness</strong> (Definitional-heavy) → <strong>Exploration</strong> (mixed)
              → <strong>Evaluation</strong> (Comparison-heavy) → <strong>Action-ready</strong> (Decision-heavy).
              <strong> Support-needed</strong> users are stuck and may need human help.
            </InfoHint>
          </div>
          <ul className="platform-funnel">
            {STAGE_ORDER.map((stage) => {
              const row = (data.stage_funnel || []).find((r) => r.stage === stage);
              const count = row?.count || 0;
              return (
                <li key={stage} className={count ? "" : "dim"}>
                  <span className="funnel-label">{stage}</span>
                  <span className="funnel-bar-wrap">
                    <span
                      className={`funnel-bar funnel-${stage.toLowerCase().replace(/\W+/g, "-")}`}
                      style={{ width: `${(count / maxStageCount) * 100}%` }}
                    />
                  </span>
                  <span className="funnel-count">{count}</span>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="platform-block">
          <div className="platform-block-head">
            Outreach-readiness distribution
            <InfoHint width={340}>
              How many users land in each readiness tier.
              <strong> Ready</strong> ≥ 0.70 — surface for outreach.
              <strong> Likely</strong> ≥ 0.50 — strong candidates, nurture lightly.
              <strong> Nurture</strong> ≥ 0.30 — keep engaged but don't push.
              <strong> Too early</strong> &lt; 0.30 — leave them alone.
              The stage gate means an "Awareness" user can't be Ready regardless of engagement.
            </InfoHint>
          </div>
          <ul className="platform-funnel">
            {READINESS_ORDER.map((tier) => {
              const row = (data.readiness_funnel || []).find((r) => r.tier === tier);
              const count = row?.count || 0;
              return (
                <li key={tier} className={count ? "" : "dim"}>
                  <span className="funnel-label">{tier}</span>
                  <span className="funnel-bar-wrap">
                    <span
                      className={`funnel-bar funnel-tier-${tier.toLowerCase().replace(/\W+/g, "-")}`}
                      style={{ width: `${(count / maxReadyCount) * 100}%` }}
                    />
                  </span>
                  <span className="funnel-count">{count}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      {/* Intent + signal mix */}
      <div className="platform-cols-2">
        <div className="platform-block">
          <div className="platform-block-head">
            Intent mix
            <InfoHint width={300}>
              Percentage of all turns in this window by intent. A balanced spread is healthy;
              a heavy <em>Definitional</em> skew means the user base is still learning. A heavy
              <em> Comparison/Decision</em> skew means they're at the action end.
            </InfoHint>
          </div>
          <div className="pct-row">
            {(data.intent_mix || []).map((i) => (
              <span key={i.intent} className="pct-pill">
                <span className="pct-name">{i.intent}</span>
                <span className="pct-num">{i.pct}%</span>
              </span>
            ))}
            {(data.intent_mix || []).length === 0 && <span className="muted">No intents recorded.</span>}
          </div>
        </div>

        <div className="platform-block">
          <div className="platform-block-head">
            Signal mix (across all firings)
            <InfoHint width={380}>
              How often each signal fired across all rewarded turns. The
              catalog is the 9-signal set from the reward doc: thumbs (UI)
              plus six LLM-detected text signals.
              <br/><br/>
              Green = positive (<code>thumbs_up</code>,
              <code> format_praise_explicit</code>, <code>it_worked_statement</code>,
              <code> deeper_question</code>).
              Red = negative (<code>thumbs_down</code>,
              <code> format_change_request</code>, <code>content_correction</code>,
              <code> reask_same_question</code>).
              A healthy mix is mostly green with rare explicit complaints.
            </InfoHint>
          </div>
          <div className="pct-row">
            {(data.signal_mix || []).map((s) => (
              <span
                key={s.signal}
                className={`pct-pill signal-${signalToneClass(s.signal)}`}
                title={`${s.count} firings`}
              >
                <span className="pct-name">{s.signal.replace(/_/g, " ")}</span>
                <span className="pct-num">{s.pct}%</span>
              </span>
            ))}
            {(data.signal_mix || []).length === 0 && <span className="muted">No signals recorded.</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Helpers ----------

const STAGE_ORDER     = ["Awareness", "Exploration", "Evaluation", "Action-ready", "Support-needed", "Unknown"];
const READINESS_ORDER = ["Ready", "Likely", "Nurture", "Too early"];

function signalToneClass(name) {
  if (!name) return "neutral";
  // Legacy composite patterns may exist in old data — keep them distinct
  if (name.startsWith("pattern_")) return "composite";
  // Positive — current catalog first, legacy names kept for old records
  if (/^(thumbs_up|format_praise_explicit|it_worked_statement|deeper_question|copy_save|format_keep_request|format_compliance_pass|session_continue)$/.test(name)) {
    return "pos";
  }
  // Negative — current catalog first, legacy names kept for old records
  if (/^(thumbs_down|format_change_request|content_correction|reask_same_question|regenerate_click|session_abandon|format_compliance_fail)$/.test(name)) {
    return "neg";
  }
  return "neutral";
}

function PlatformNumber({ value, label }) {
  return (
    <div className="platform-num">
      <div className="platform-num-value">{value ?? "—"}</div>
      <div className="platform-num-label">{label}</div>
    </div>
  );
}

function fmt(v) {
  if (v == null) return "—";
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(2);
}

function prettyName(s) {
  if (!s) return "—";
  return String(s).replace(/_/g, " ");
}

function sum(arr) {
  let s = 0;
  for (const x of arr) s += Number(x) || 0;
  return s;
}
