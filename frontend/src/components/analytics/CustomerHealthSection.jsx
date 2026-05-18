import { useEffect, useState } from "react";
import { api } from "../../api.js";
import InfoHint from "./InfoHint.jsx";
import MiniLineChart from "./MiniLineChart.jsx";

/**
 * CustomerHealthSection — the three remaining signal consumers in one block.
 *
 *   retention    — D1 / D7 / D30 cohort return rates
 *   satisfaction — NPS-style score from thumbs_up/thumbs_down (per-week trend)
 *   engagement   — behavioral segments (deep_divers, explorers, etc.)
 *
 * All three are GLOBAL (don't depend on the inspected user) and CUMULATIVE
 * in nature — they describe long-running product health metrics. The date
 * window selector applies via the `days` parameter.
 */
export default function CustomerHealthSection({ windowLabel = "", days = 30 }) {
  const [data, setData] = useState(null);
  const [err, setErr]   = useState(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setErr(null);
    try {
      const d = await api.customerHealth(days, 4);
      setData(d);
    } catch (e) {
      setErr(e.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  }
  // Refetch on mount AND whenever the parent's window changes.
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  if (err) {
    return (
      <section className="section">
        <div className="error-banner">
          <strong>Failed</strong> <code>/analytics/customer-health</code>
          <div className="error-detail">{err}</div>
        </div>
      </section>
    );
  }
  if (!data) {
    return (
      <section className="section">
        <div className="empty-state">Loading customer health…</div>
      </section>
    );
  }

  return (
    <section className="section section-health">
      <div className="section-head">
        <div>
          <h2>
            Customer health
            <span className="window-tag">{windowLabel}</span>
          </h2>
          <p className="section-sub">
            Retention cohorts, NPS-style satisfaction score, and behavioral
            engagement segments — the three signal consumers that turn{" "}
            <code>thumbs_up</code>, <code>thumbs_down</code>,{" "}
            <code>deeper_question</code>, and session-continuity signals into
            product-health rollups.
          </p>
        </div>
        <div>
          <button className="btn-secondary" onClick={load} disabled={busy}>
            {busy ? "Loading…" : "Reload"}
          </button>
        </div>
      </div>

      <div className="health-grid">
        <RetentionCard retention={data.retention} />
        <SatisfactionCard satisfaction={data.satisfaction} />
        <EngagementCard engagement={data.engagement} />
      </div>
    </section>
  );
}

// ─── Retention card ───────────────────────────────────────────────────────

function RetentionCard({ retention }) {
  const cohorts = retention?.cohorts || [];
  const d1   = retention?.overall_d1_retention  ?? 0;
  const d7   = retention?.overall_d7_retention  ?? 0;
  const d30  = retention?.overall_d30_retention ?? 0;

  return (
    <div className="health-card">
      <div className="health-card-head">
        <h3>Retention</h3>
        <InfoHint width={340}>
          Cohort return-rate analysis. Users are grouped by the week they were
          first seen; <strong>D1 / D7 / D30 retention</strong> = % of that cohort
          that had at least one more turn within 1 / 7 / 30 days of their
          first visit. Only mature cohorts (old enough to measure) contribute
          to the overall average.
        </InfoHint>
      </div>

      <div className="health-numbers">
        <RetentionPill label="D1" rate={d1} />
        <RetentionPill label="D7" rate={d7} />
        <RetentionPill label="D30" rate={d30} />
      </div>

      {cohorts.length === 0 ? (
        <div className="health-empty">No cohorts yet.</div>
      ) : (
        <table className="health-cohort-tbl">
          <thead>
            <tr>
              <th>Cohort (week)</th>
              <th className="num">Size</th>
              <th className="num">D1</th>
              <th className="num">D7</th>
              <th className="num">D30</th>
            </tr>
          </thead>
          <tbody>
            {cohorts.map((c) => (
              <tr key={c.week_start}>
                <td className="ts">{c.week_start}</td>
                <td className="num">{c.size}</td>
                <td className="num">{c.mature_d1  ? pct(c.rate_d1)  : "—"}</td>
                <td className="num">{c.mature_d7  ? pct(c.rate_d7)  : "—"}</td>
                <td className="num">{c.mature_d30 ? pct(c.rate_d30) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function RetentionPill({ label, rate }) {
  const tier = rate >= 0.5 ? "good" : rate >= 0.25 ? "mid" : "low";
  return (
    <div className={`retention-pill retention-${tier}`}>
      <div className="retention-pill-rate">{pct(rate)}</div>
      <div className="retention-pill-label">{label}</div>
    </div>
  );
}

// ─── Satisfaction card ────────────────────────────────────────────────────

function SatisfactionCard({ satisfaction }) {
  const s = satisfaction || {};
  const nps = s.nps_score ?? 0;
  const verdict = s.verdict || "mixed";

  return (
    <div className="health-card">
      <div className="health-card-head">
        <h3>Satisfaction (NPS-style)</h3>
        <InfoHint width={340}>
          Score = <code>(positive% − negative%) × 100</code> from
          <code> thumbs_up</code> / <code>thumbs_down</code> signals.
          Range <code>[−100, +100]</code>.{" "}
          <strong>Very satisfied ≥ 50 · Mixed 0-50 · Concerning &lt; 0.</strong>
          {" "}Note: thumbs_up/down are <em>not</em> used to update the bandit
          (they're ambiguous about cause) — but they ARE the cleanest signal
          for overall satisfaction.
        </InfoHint>
      </div>

      <div className="nps-display">
        <div className={`nps-score nps-${verdict}`}>
          {nps > 0 ? "+" : ""}{nps}
        </div>
        <div className="nps-verdict">{prettyVerdict(verdict)}</div>
      </div>

      <div className="nps-breakdown">
        <span className="thumbs-stat thumbs-up">
          Positive: <strong>{s.thumbs_up ?? 0}</strong> <span className="muted">({pct(s.positive_rate ?? 0)})</span>
        </span>
        <span className="thumbs-stat thumbs-down">
          Negative: <strong>{s.thumbs_down ?? 0}</strong> <span className="muted">({pct(s.negative_rate ?? 0)})</span>
        </span>
        <span className="thumbs-total muted">
          {s.total_rated ?? 0} rated turns
        </span>
      </div>

      {(s.weekly_trend || []).length > 1 && (
        <div className="nps-trend">
          <div className="nps-trend-head">Weekly positive rate</div>
          <MiniLineChart
            data={s.weekly_trend.map((w) => ({
              date: w.week_start,
              value: Math.round(w.rate * 100),
            }))}
            width={300}
            height={70}
            color="#5fa86b"
            yLabel="positive %"
            formatValue={(v) => `${v}%`}
          />
        </div>
      )}
    </div>
  );
}

// ─── Engagement card ──────────────────────────────────────────────────────

function EngagementCard({ engagement }) {
  const e = engagement || {};
  const segments = e.segments || [];
  const total = e.total_users || 0;
  const max = Math.max(...segments.map((s) => s.count), 1);

  return (
    <div className="health-card">
      <div className="health-card-head">
        <h3>Engagement segments</h3>
        <InfoHint width={380}>
          Behavioral segmentation. Each active user falls into exactly one segment
          based on their in-window pattern:
          <br/><br/>
          <strong>Deep divers</strong>: &gt;5 deeper_questions on ≤3 topics — they want depth on a few subjects.
          <br/>
          <strong>Explorers</strong>: &gt;3 topics covered — broad curiosity.
          <br/>
          <strong>Power users</strong>: &gt;20 turns AND &gt;2 sessions — habitual.
          <br/>
          <strong>One-and-done</strong>: ≤2 turns lifetime — never came back after first try.
          <br/>
          <strong>Casual</strong>: everyone else — moderate usage.
        </InfoHint>
      </div>

      <div className="engagement-total">
        <strong>{total}</strong> active user{total === 1 ? "" : "s"} in window
      </div>

      {segments.length === 0 || total === 0 ? (
        <div className="health-empty">No engagement data yet.</div>
      ) : (
        <ul className="engagement-list">
          {segments.map((s) => (
            <li key={s.segment} className={s.count > 0 ? "" : "dim"}>
              <span className="seg-label">{prettySegment(s.segment)}</span>
              <span className="seg-bar-wrap">
                <span
                  className={`seg-bar seg-${s.segment}`}
                  style={{ width: `${(s.count / max) * 100}%` }}
                />
              </span>
              <span className="seg-count">{s.count}</span>
              <span className="seg-pct muted">{pct(s.pct)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function pct(v) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${Math.round(Number(v) * 100)}%`;
}

function prettyVerdict(v) {
  return ({
    very_satisfied: "Very satisfied",
    mixed:          "Mixed",
    concerning:     "Concerning",
  })[v] || v;
}

function prettySegment(s) {
  return ({
    deep_divers:   "Deep divers",
    explorers:     "Explorers",
    power_users:   "Power users",
    one_and_done:  "One-and-done",
    casual:        "Casual",
  })[s] || s.replace(/_/g, " ");
}
