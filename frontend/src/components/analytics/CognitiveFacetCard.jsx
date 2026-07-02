import { useState } from "react";
import ScoreCircle from "./ScoreCircle.jsx";
import BetaCurve from "./BetaCurve.jsx";
import ConfidenceChip from "./ConfidenceChip.jsx";

/**
 * CognitiveFacetCard — one (intent, topic) cell, fully expanded.
 *
 * Layout (matches the reference dashboard):
 *   ┌──────────────────────────────────────────────────────────────┐
 *   │  ⊙ 88     Rebalancing Decisions         ● Scenario Narrative │
 *   │  score    [intent] · [topic]              μ = 0.85           │
 *   │           HIGH CONFIDENCE · 14 interactions                  │
 *   │                                          ● Elimination Matrix│
 *   │                                            μ = 0.42          │
 *   │ ────────────────────────────────────────────────────────────  │
 *   │     [Beta curve LEAD]              [Beta curve RUNNER]        │
 *   │                                                              │
 *   │  ✦ COGNITIVE INSIGHT                                         │
 *   │  Strong preference for scenario narrative — clearly outper…  │
 *   │                                                              │
 *   │  ▾ All strategies tried (optional, collapsed)                │
 *   └──────────────────────────────────────────────────────────────┘
 */
export default function CognitiveFacetCard({ facet, onInspectUser }) {
  const [showAll, setShowAll] = useState(false);
  const [showContributors, setShowContributors] = useState(false);

  const lead = facet.leading_strategy;
  const runner = facet.runner_up_strategy;

  // Claude palette: leader uses the brand orange, runner-up a muted gray-brown
  const leadColor   = "#c87a4c";   // --primary
  const runnerColor = "#8c8980";   // --muted

  const hasExtras = (facet.all_strategies?.length || 0) > (runner ? 2 : 1);
  const hasContributors = facet.scope === "global"
    && Array.isArray(facet.contributors)
    && facet.contributors.length > 0;

  return (
    <div className="facet-card">
      {/* Header row — score, name, leaders */}
      <div className="facet-row">
        <ScoreCircle value={facet.confidence_score} tier={facet.confidence_tier} />

        <div className="facet-main">
          <div className="facet-title">
            <span className="facet-title-text">{facet.facet_name}</span>
            {/* "N users" pill is GLOBAL-ONLY — never renders in single-user mode.
                Click to expand the contributor list inside the card. */}
            {facet.scope === "global" && facet.unique_users != null && (
              <button
                type="button"
                className={`users-pill users-pill-button ${showContributors ? "open" : ""}`}
                onClick={() => setShowContributors((v) => !v)}
                disabled={!hasContributors}
                title={hasContributors
                  ? "Click to see who contributed to this cell"
                  : "Number of distinct users who contributed to this cell"}
              >
                {facet.unique_users} user{facet.unique_users === 1 ? "" : "s"}
                {hasContributors && (
                  <span className="users-pill-caret">{showContributors ? "▴" : "▾"}</span>
                )}
              </button>
            )}
          </div>
          <div className="facet-sub">
            <code className="intent-pill">{facet.intent}</code>
            <span className="dot-sep">·</span>
            <code className="topic-pill">{facet.topic}</code>
          </div>
          <ConfidenceChip tier={facet.confidence_tier} count={facet.interaction_count} />
        </div>

        <div className="facet-leaders">
          <div className="leader-row">
            <span className="leader-dot" style={{ background: leadColor }} />
            <span className="leader-name">{prettyName(lead?.name)}</span>
            <span className="leader-mu">μ = {fmt(lead?.avg_reward)}</span>
          </div>
          {runner && (
            <div className="leader-row runner">
              <span className="leader-dot" style={{ background: runnerColor }} />
              <span className="leader-name">{prettyName(runner.name)}</span>
              <span className="leader-mu">μ = {fmt(runner.avg_reward)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Inline detail — always visible */}
      <div className="facet-detail">
        <div className="curves-row">
          {lead && (
            <BetaCurve
              alpha={lead.alpha}
              beta={lead.beta}
              label={prettyName(lead.name)}
              color={leadColor}
            />
          )}
          {runner ? (
            <BetaCurve
              alpha={runner.alpha}
              beta={runner.beta}
              label={prettyName(runner.name)}
              color={runnerColor}
            />
          ) : (
            <div className="beta-curve beta-empty">
              <div className="beta-empty-text">
                Only one strategy tried —<br />
                no runner-up to compare yet
              </div>
            </div>
          )}
        </div>

        {/* Contributor list — visible only in global mode after click. */}
        {showContributors && hasContributors && (
          <div className="contributors">
            <div className="contributors-head">
              Contributors to this cell ({facet.contributors.length})
            </div>
            <table className="contributors-tbl">
              <thead>
                <tr>
                  <th>User</th>
                  <th className="num">Pulls</th>
                  <th>Best strategy</th>
                  <th className="num">μ-reward</th>
                  <th>Last active</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {facet.contributors.map((c) => (
                  <tr key={c.user_id_hash}>
                    <td>
                      <span className="contrib-name">{c.display_name}</span>
                      <code className="contrib-hash" title={c.user_id_hash}>
                        {shortHash(c.user_id_hash)}
                      </code>
                    </td>
                    <td className="num">{c.pulls_in_cell}</td>
                    <td>{prettyName(c.best_strategy)}</td>
                    <td className="num">{c.best_strategy_avg_reward.toFixed(2)}</td>
                    <td className="contrib-last">{relativeTime(c.last_active)}</td>
                    <td>
                      <button
                        className="contrib-inspect"
                        onClick={() => onInspectUser?.(c.user_id_hash)}
                        title="Switch the page to this user's view"
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="cog-insight">
          <div className="cog-insight-head">
            <span className="cog-icon">✦</span> Cognitive Insight
          </div>
          <div className="cog-insight-body">{facet.insight_text}</div>
        </div>

        {hasExtras && (
          <div className="all-strategies">
            <button
              className="all-strategies-toggle"
              onClick={() => setShowAll((s) => !s)}
            >
              {showAll ? "▾" : "▸"} All strategies tried ({facet.all_strategies.length})
            </button>
            {showAll && (
              <>
                <table className="strategy-mini-tbl">
                  <thead>
                    <tr>
                      <th>Strategy</th>
                      <th className="num">Pulls</th>
                      <th className="num">μ reward</th>
                      <th className="num" title="Selection score = avg_reward + exploration bonus. This is pick priority, not reward.">Selection score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {facet.all_strategies.map((s) => (
                      <tr key={s.name}>
                        <td>{prettyName(s.name)}</td>
                        <td className="num">{s.count}</td>
                        <td className="num">{fmt(s.avg_reward)}</td>
                        <td className="num">{fmt(s.cached_ucb)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="ucb-formula-note">
                  Runtime selection uses <code>selection_score = avg_reward + c * width * sqrt(2 * ln N / count)</code>,
                  computed live (no cache) from the current params. This is pick priority, not reward; the rightmost column
                  drives the next pick. The Beta curves above are a visualization; they aren't read by the selection code.
                </div>
              </>
            )}
          </div>
        )}

        {facet.last_activity_ts && (
          <div className="facet-footer">
            Last activity: {formatTs(facet.last_activity_ts)}
          </div>
        )}
      </div>
    </div>
  );
}

function prettyName(s) {
  if (!s) return "—";
  return String(s).replace(/_/g, " ");
}

function fmt(v) {
  if (v == null) return "—";
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(2);
}

function formatTs(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function shortHash(h) {
  if (!h) return "—";
  return h.length > 12 ? `${h.slice(0, 12)}…` : h;
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
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString();
}
