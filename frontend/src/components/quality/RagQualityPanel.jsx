import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * RagQualityPanel — surfaces TOPICS where the knowledge base / RAG is failing.
 *
 * Reuses the same problem signals as InstructionQualityPanel — but groups
 * by topic instead of by (strategy, instruction_version) — so admins can
 * see which topics need RAG enrichment vs which instructions need rewriting.
 *
 * Two questions, two dashboards:
 *   "Which instruction needs rewriting?"   → InstructionQualityPanel
 *   "Which topic's RAG needs enriching?"   → THIS panel
 *
 * Signal weights:
 *   content_correction    × 1.0   (strong — user explicitly corrected a fact)
 *   reask_same_question   × 0.5   (moderate — answer didn't land; mixed cause)
 */
export default function RagQualityPanel({ notify, daysOverride = null }) {
  const [data, setData]   = useState(null);
  const [err, setErr]     = useState(null);
  const [busy, setBusy]   = useState(false);
  const [days, setDays]   = useState(daysOverride ?? 14);
  const [expanded, setEx] = useState(null);

  // If the parent passes a daysOverride (analytics-tab usage), sync our
  // internal state when the parent's window changes.
  useEffect(() => {
    if (daysOverride != null) setDays(daysOverride);
  }, [daysOverride]);

  async function load() {
    setBusy(true);
    setErr(null);
    try {
      const d = await api.ragQuality(days, 5, 5);
      setData(d);
    } catch (e) {
      setErr(e.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  }
  // Refetch on mount AND whenever days changes (either via parent override
  // or local input).
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  return (
    <div className="iq-panel">
      <div className="iq-head">
        <div>
          <h2 className="admin-section-title">RAG / knowledge-base quality by topic</h2>
          <p className="admin-section-sub">
            Which <strong>topics</strong> are producing content failures — same
            signals as instruction quality (<code>content_correction</code>,
            <code> reask_same_question</code>) but grouped by topic instead of
            by strategy. Tells you <strong>which topic needs more / better RAG content</strong>,
            independent of which instruction was active.
          </p>
        </div>
        <div className="iq-controls">
          <label>
            Window (days)
            <input
              type="number"
              min="1"
              max="90"
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value) || 14)}
              style={{ width: "60px" }}
            />
          </label>
          <button className="btn-primary" onClick={load} disabled={busy}>
            {busy ? "Loading…" : "Reload"}
          </button>
        </div>
      </div>

      <ul className="col-legend">
        <li><strong>Weighted failure rate</strong> = (content_corrections × 1.0 + reasks × 0.5) / total_turns.
          <em> Content corrections weigh double because they're explicit factual rejections.</em></li>
        <li><strong>Tier</strong> — CRITICAL ≥ 25% · HIGH ≥ 12% · MEDIUM ≥ 5% · LOW · EXPLORING (&lt;5 turns).</li>
        <li><strong>Sample queries</strong> — the actual user questions that broke. Use them to identify which RAG documents are missing or wrong.</li>
        <li><strong>How to fix</strong> — for CRITICAL/HIGH topics: enrich RAG content, add/update knowledge-base entries, verify source documents are current.</li>
      </ul>

      {err && (
        <div className="error-banner">
          <strong>Failed</strong> <code>/analytics/rag-quality</code>
          <div className="error-detail">{err}</div>
        </div>
      )}

      {data && (
        <>
          <div className="iq-summary">
            <span><strong>{data.total_turns}</strong> turns in window</span>
            <span className="dot-sep">·</span>
            <span>
              <strong>{data.total_failures}</strong> weighted failures
              {" "}({(data.overall_rate * 100).toFixed(1)}% overall rate)
            </span>
            <span className="dot-sep">·</span>
            <span><strong>{data.topics.length}</strong> topics</span>
          </div>

          {data.topics.length === 0 ? (
            <div className="admin-empty">
              No topic-level problem signals in the last {days} days. RAG is healthy
              (or the system hasn't seen enough traffic to surface issues).
            </div>
          ) : (
            <div className="iq-list">
              {data.topics.map((t) => {
                const isOpen = expanded === t.topic;
                return (
                  <div
                    key={t.topic}
                    className={`iq-card iq-tier-${t.tier.toLowerCase()} ${isOpen ? "open" : ""}`}
                  >
                    <div
                      className="iq-card-head"
                      onClick={() => setEx(isOpen ? null : t.topic)}
                      role="button"
                      tabIndex={0}
                    >
                      <span className={`tier-chip tier-${t.tier.toLowerCase()}`}>{t.tier}</span>
                      <code className="topic-chip">{t.topic}</code>
                      <span className="iq-rate">
                        <strong>{(t.failure_rate * 100).toFixed(1)}%</strong> failure rate
                      </span>
                      <span className="iq-totals">
                        {t.weighted_failures} weighted · {t.total_turns} turns
                      </span>
                      <span className="iq-dominant">
                        {t.content_corrections > 0 && (
                          <span title="Factual errors explicitly called out">
                            ✗ <strong>{t.content_corrections}</strong> corrections
                          </span>
                        )}
                        {t.content_corrections > 0 && t.reask_same_questions > 0 && " · "}
                        {t.reask_same_questions > 0 && (
                          <span title="Users re-asked the same thing">
                            ↻ <strong>{t.reask_same_questions}</strong> reasks
                          </span>
                        )}
                      </span>
                      <span className="iq-expand">{isOpen ? "▾" : "▸"}</span>
                    </div>

                    {isOpen && (
                      <div className="iq-card-body">
                        <div className="iq-failures-row">
                          <span className="iq-failure-chip active" title="Strong evidence — user explicitly told us a fact is wrong">
                            <code className="problem-signal">content_correction</code>
                            <strong className="iq-failure-count">{t.content_corrections}</strong>
                          </span>
                          <span className="iq-failure-chip active" title="Moderate evidence — user had to re-ask">
                            <code className="problem-signal">reask_same_question</code>
                            <strong className="iq-failure-count">{t.reask_same_questions}</strong>
                          </span>
                        </div>

                        {t.samples && t.samples.length > 0 && (
                          <div className="iq-samples">
                            <div className="iq-samples-head">
                              Sample failing queries — these are the real questions your RAG didn't handle well
                            </div>
                            <table className="iq-samples-tbl">
                              <thead>
                                <tr>
                                  <th style={{ width: "150px" }}>When</th>
                                  <th style={{ width: "120px" }}>Intent</th>
                                  <th>User query</th>
                                  <th style={{ width: "230px" }}>Signals</th>
                                </tr>
                              </thead>
                              <tbody>
                                {t.samples.map((s) => (
                                  <tr key={s.response_id}>
                                    <td className="ts">{(s.ts || "").slice(0, 19).replace("T", " ")}</td>
                                    <td>
                                      <code className="intent-chip">{s.intent || "—"}</code>
                                    </td>
                                    <td className="iq-query">{s.query || <span className="muted">(query not stored)</span>}</td>
                                    <td>
                                      {(s.signals || []).map((sig) => (
                                        <code key={sig} className="problem-signal">{sig}</code>
                                      ))}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        <div className="iq-action-hint">
                          {hint(t)}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function hint(t) {
  if (t.tier === "CRITICAL") {
    return (
      <>
        <strong>How to fix:</strong> this topic has a critical RAG failure rate. Review the
        sample queries — your knowledge base is likely missing key information or has stale /
        incorrect content for <code>{t.topic}</code>. Priority: add or update RAG documents
        covering the exact facts users are correcting.
      </>
    );
  }
  if (t.tier === "HIGH") {
    return (
      <>
        <strong>How to fix:</strong> elevated failure rate. The RAG documents for <code>{t.topic}</code> may
        need refresh — verify source accuracy and completeness. Sample queries show what users expect.
      </>
    );
  }
  if (t.tier === "MEDIUM") {
    return (
      <>
        <strong>How to fix:</strong> moderate issues. Monitor and consider enriching RAG for this
        topic. If reasks dominate the count, the problem may be presentation clarity (instruction)
        rather than missing content (RAG).
      </>
    );
  }
  if (t.tier === "LOW") {
    return (
      <>
        <strong>Healthy:</strong> this topic's RAG is performing well. No action needed.
      </>
    );
  }
  return (
    <>
      <strong>Not enough data:</strong> fewer than 5 turns on this topic. Wait for more traffic
      before drawing conclusions.
    </>
  );
}
