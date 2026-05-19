import { useEffect, useState } from "react";
import { api } from "../../api.js";

/**
 * InstructionQualityPanel — surfaces (strategy, instruction_version) pairs
 * producing problem signals (format_compliance_fail, content_correction,
 * reask_same_question), ranked by failure rate.
 *
 * This is the "instruction_quality" consumer the signal catalog declared
 * — admins use it to know which instructions need rewriting. Failure rate
 * + dominant signal type tell the admin what KIND of fix to make:
 *   - format_compliance_fail dominates → tighten the format instruction
 *   - content_correction dominates     → review accuracy / RAG retrieval
 *   - reask_same_question dominates    → clarify / restructure
 */
export default function InstructionQualityPanel({ notify }) {
  const [data, setData]   = useState(null);
  const [err, setErr]     = useState(null);
  const [busy, setBusy]   = useState(false);
  const [days, setDays]   = useState(14);
  const [expanded, setEx] = useState(null);   // key of currently-expanded row

  async function load() {
    setBusy(true);
    setErr(null);
    try {
      const d = await api.instructionQuality(days, 5, 5);
      setData(d);
    } catch (e) {
      setErr(e.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  return (
    <div className="iq-panel">
      <div className="iq-head">
        <div>
          <h2 className="admin-section-title">Instruction quality</h2>
          <p className="admin-section-sub">
            Which <code>(strategy, instruction_version)</code> pairs are producing
            problem signals — <code>format_compliance_fail</code>,
            <code> content_correction</code>, <code>reask_same_question</code> —
            in the last {days} days. Sorted by tier (severity) then failure rate.
            <strong> The dominant signal type tells you what kind of fix to make.</strong>
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
        <li><strong>Tier</strong> — severity bucket.
          <em> CRITICAL ≥ 30% failures · HIGH ≥ 15% · MEDIUM ≥ 5% · LOW &lt; 5% · EXPLORING = fewer than 5 turns.</em></li>
        <li><strong>Failure rate</strong> — share of turns with ANY problem signal.
          <em> e.g. 0.169 = 16.9% of served turns produced a complaint or compliance failure.</em></li>
        <li><strong>Dominant signal</strong> — which problem signal is fired most for this pair. Tells you the KIND of fix.
          <em> format_compliance_fail → instruction not specific enough about shape; content_correction → factual issue; reask → clarity/comprehension.</em></li>
        <li><strong>Sample turns</strong> — actual user queries that triggered failures. Click a row to expand and review.
          <em> Use them to understand WHY the instruction failed in context.</em></li>
      </ul>

      {err && (
        <div className="error-banner">
          <strong>Failed</strong> <code>/analytics/instruction-quality</code>
          <div className="error-detail">{err}</div>
        </div>
      )}

      {data && (
        <>
          <div className="iq-summary">
            <span><strong>{data.total_turns}</strong> turns in window</span>
            <span className="dot-sep">·</span>
            <span>
              <strong>{data.total_failures}</strong> with problem signal
              {" "}({(data.overall_rate * 100).toFixed(1)}% overall failure rate)
            </span>
            <span className="dot-sep">·</span>
            <span><strong>{data.pairs.length}</strong> strategy versions</span>
          </div>

          {data.pairs.length === 0 ? (
            <div className="admin-empty">
              No turns recorded in the last {days} days, or no problem signals fired yet.
              Once <code>format_compliance_fail</code> starts firing automatically
              on diverging turns, this dashboard will populate.
            </div>
          ) : (
            <div className="iq-list">
              {data.pairs.map((p, i) => {
                const key = `${p.strategy}__${p.instruction_version}`;
                const isOpen = expanded === key;
                const dominant = dominantSignal(p.failures);
                return (
                  <div
                    key={key}
                    className={`iq-card iq-tier-${p.tier.toLowerCase()} ${isOpen ? "open" : ""}`}
                  >
                    <div
                      className="iq-card-head"
                      onClick={() => setEx(isOpen ? null : key)}
                      role="button"
                      tabIndex={0}
                    >
                      <span className={`tier-chip tier-${p.tier.toLowerCase()}`}>{p.tier}</span>
                      <code className="code-pill">{p.strategy}</code>
                      <code className="version-chip">@{p.instruction_version}</code>
                      <span className="iq-rate">
                        <strong>{(p.failure_rate * 100).toFixed(1)}%</strong> failures
                      </span>
                      <span className="iq-totals">
                        {p.total_failures} of {p.total_turns} turns
                      </span>
                      {dominant && (
                        <span className="iq-dominant" title="The signal type producing most of the failures — fix this first">
                          dominant: <code className="problem-signal">{dominant}</code>
                        </span>
                      )}
                      <span className="iq-expand">{isOpen ? "▾" : "▸"}</span>
                    </div>

                    {isOpen && (
                      <div className="iq-card-body">
                        <div className="iq-failures-row">
                          <FailureChip
                            label="format_compliance_fail"
                            count={p.failures.format_compliance_fail || 0}
                            help="Synthesizer diverged from strategy.format_type. Tighten the instruction's format guidance."
                          />
                          <FailureChip
                            label="content_correction"
                            count={p.failures.content_correction || 0}
                            help="User explicitly corrected a fact. Review accuracy / RAG retrieval for this strategy."
                          />
                          <FailureChip
                            label="reask_same_question"
                            count={p.failures.reask_same_question || 0}
                            help="User re-asked the same thing. The original answer didn't land — clarify or restructure."
                          />
                        </div>

                        {p.samples && p.samples.length > 0 && (
                          <div className="iq-samples">
                            <div className="iq-samples-head">
                              Sample failing turns ({p.samples.length})
                            </div>
                            <table className="iq-samples-tbl">
                              <thead>
                                <tr>
                                  <th style={{ width: "150px" }}>When</th>
                                  <th style={{ width: "120px" }}>Intent · Topic</th>
                                  <th>Query</th>
                                  <th style={{ width: "260px" }}>Signals fired</th>
                                </tr>
                              </thead>
                              <tbody>
                                {p.samples.map((s) => (
                                  <tr key={s.response_id}>
                                    <td className="ts">{(s.ts || "").slice(0, 19).replace("T", " ")}</td>
                                    <td>
                                      <code className="intent-chip">{s.intent || "—"}</code>
                                      {s.topic && <code className="topic-chip">{s.topic}</code>}
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
                          {fixHint(dominant)}
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

// ─── Helpers ──────────────────────────────────────────────────────

function dominantSignal(failures) {
  if (!failures) return null;
  let best = null;
  let bestCount = 0;
  for (const [sig, count] of Object.entries(failures)) {
    if (count > bestCount) {
      best = sig;
      bestCount = count;
    }
  }
  return bestCount > 0 ? best : null;
}

function fixHint(dominantSig) {
  if (dominantSig === "format_compliance_fail") {
    return (
      <>
        <strong>How to fix:</strong> the synthesizer is failing to obey the strategy's
        declared <code>format_type</code>. Open the instruction and make the shape
        directive more concrete — specify section names, bullet counts, length caps.
        Re-publish as a new version.
      </>
    );
  }
  if (dominantSig === "content_correction") {
    return (
      <>
        <strong>How to fix:</strong> users are correcting facts the answer asserted.
        Review the sample queries for the topics most affected. Likely root cause:
        outdated knowledge, missing RAG retrieval, or instruction telling the LLM
        to be confident on topics it shouldn't be.
      </>
    );
  }
  if (dominantSig === "reask_same_question") {
    return (
      <>
        <strong>How to fix:</strong> users are asking the same question again — the
        answer isn't landing. Either content depth is insufficient or the format
        is hard to parse. Look at the sample queries to see if a particular topic
        consistently confuses users.
      </>
    );
  }
  return (
    <>
      <strong>How to fix:</strong> review the sample failing turns to identify
      the pattern. Each problem signal type maps to a different kind of
      instruction fix.
    </>
  );
}

function FailureChip({ label, count, help }) {
  return (
    <span className={`iq-failure-chip ${count > 0 ? "active" : ""}`} title={help}>
      <code className="problem-signal">{label}</code>
      <strong className="iq-failure-count">{count}</strong>
    </span>
  );
}
