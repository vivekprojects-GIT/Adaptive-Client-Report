/**
 * CorrelationHeatmap — pairwise Pearson correlation matrix between signals.
 *
 * Reads:
 *   data = {
 *     signals:     ["thumbs_up", "thumbs_down", ...],
 *     matrix:      [[1.0, -0.4, ...], ...],      // NxN, symmetric, diag = 1
 *     frequencies: {"thumbs_up": 0.32, ...},     // marginal share per signal
 *     n_users:     23,
 *     n_turns:     412,
 *     small_sample_warning: true|false,
 *   }
 *
 * Visual:
 *   Red cell   = positive correlation  (users firing X also fire Y)
 *   Blue cell  = negative correlation  (firing X means NOT firing Y)
 *   White cell = ≈ 0 correlation        (independent at user-population level)
 *
 * Diagonal is always 1.0 (perfect self-correlation) and is dimmed
 * because it carries no information.
 *
 * Designed as a hand-rolled SVG (consistent with MiniLineChart). No
 * dependency on d3/plotly/recharts — keeps the bundle small.
 */
import { useState } from "react";
import InfoHint from "./InfoHint.jsx";

const CELL_SIZE = 38;     // square px per cell
const LABEL_W   = 150;    // left/top label rail width
const PAD       = 12;     // outer padding

export default function CorrelationHeatmap({ data }) {
  const [hover, setHover] = useState(null);   // {i, j} of hovered cell

  if (!data || !data.signals || data.signals.length === 0) {
    return (
      <div className="corr-empty">
        No signal correlation data yet — needs at least one applied-reward turn.
      </div>
    );
  }

  const { signals, matrix, frequencies, n_users, n_turns, small_sample_warning } = data;
  const n = signals.length;

  // Geometry
  const gridW = n * CELL_SIZE;
  const gridH = n * CELL_SIZE;
  const totalW = LABEL_W + gridW + PAD * 2;
  const totalH = LABEL_W + gridH + PAD * 2;

  // x/y for the top-left of cell (i, j) — i = row, j = column
  const cellX = (j) => PAD + LABEL_W + j * CELL_SIZE;
  const cellY = (i) => PAD + LABEL_W + i * CELL_SIZE;

  return (
    <div className="corr-heatmap">
      <div className="corr-head">
        <div className="corr-summary">
          <strong>{n_users}</strong> user{n_users === 1 ? "" : "s"} ·
          {" "}<strong>{n_turns}</strong> applied-reward turn{n_turns === 1 ? "" : "s"} ·
          {" "}<strong>{n}</strong> signal type{n === 1 ? "" : "s"}
          {small_sample_warning && (
            <span className="corr-warning" title="Pearson correlation on fewer than 10 users is noisy. Treat values as directional, not statistical.">
              ⚠ small sample
            </span>
          )}
        </div>
      </div>

      <div className="corr-svg-wrap">
        <svg
          width={totalW}
          height={totalH}
          viewBox={`0 0 ${totalW} ${totalH}`}
          onMouseLeave={() => setHover(null)}
        >
          {/* Column labels (rotated 45°) */}
          {signals.map((s, j) => (
            <text
              key={`col-${j}`}
              x={cellX(j) + CELL_SIZE / 2}
              y={PAD + LABEL_W - 6}
              transform={`rotate(-45 ${cellX(j) + CELL_SIZE / 2} ${PAD + LABEL_W - 6})`}
              fontSize="11"
              fill="var(--text)"
              textAnchor="start"
            >
              {prettyShort(s)}
            </text>
          ))}

          {/* Row labels */}
          {signals.map((s, i) => (
            <text
              key={`row-${i}`}
              x={PAD + LABEL_W - 8}
              y={cellY(i) + CELL_SIZE / 2 + 4}
              fontSize="11"
              fill="var(--text)"
              textAnchor="end"
            >
              {prettyShort(s)}
            </text>
          ))}

          {/* Cells */}
          {matrix.map((row, i) =>
            row.map((v, j) => {
              const isDiag = i === j;
              const isHover = hover && hover.i === i && hover.j === j;
              return (
                <g key={`c-${i}-${j}`}>
                  <rect
                    x={cellX(j)}
                    y={cellY(i)}
                    width={CELL_SIZE - 1}
                    height={CELL_SIZE - 1}
                    fill={isDiag ? "var(--bg)" : corrColor(v)}
                    stroke={isHover ? "var(--primary)" : "var(--border)"}
                    strokeWidth={isHover ? 2 : 0.5}
                    onMouseEnter={() => setHover({ i, j })}
                    style={{ cursor: "pointer" }}
                  />
                  <text
                    x={cellX(j) + CELL_SIZE / 2}
                    y={cellY(i) + CELL_SIZE / 2 + 4}
                    fontSize="10.5"
                    fontWeight={Math.abs(v) > 0.5 ? 700 : 500}
                    fill={isDiag ? "var(--muted)" : textColor(v)}
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    {isDiag ? "—" : v.toFixed(2)}
                  </text>
                </g>
              );
            })
          )}
        </svg>

        {/* Hover detail panel */}
        {hover && (
          <div className="corr-detail">
            <div className="corr-detail-row">
              <code>{signals[hover.i]}</code>  ×  <code>{signals[hover.j]}</code>
            </div>
            <div className="corr-detail-row">
              ρ = <strong>{matrix[hover.i][hover.j].toFixed(3)}</strong>{" "}
              <span className="corr-detail-interp">{interpret(matrix[hover.i][hover.j])}</span>
            </div>
            <div className="corr-detail-row corr-detail-freq">
              {signals[hover.i]} fires on {(frequencies[signals[hover.i]] * 100).toFixed(1)}% of turns
            </div>
            {hover.i !== hover.j && (
              <div className="corr-detail-row corr-detail-freq">
                {signals[hover.j]} fires on {(frequencies[signals[hover.j]] * 100).toFixed(1)}% of turns
              </div>
            )}
          </div>
        )}
      </div>

      {/* Color legend */}
      <div className="corr-legend">
        <span className="corr-legend-label">Correlation:</span>
        <div className="corr-legend-bar">
          {[-1, -0.6, -0.3, 0, 0.3, 0.6, 1].map((v) => (
            <div
              key={v}
              className="corr-legend-cell"
              style={{ background: corrColor(v) }}
              title={`ρ = ${v}`}
            >
              {v.toFixed(1)}
            </div>
          ))}
        </div>
        <span className="corr-legend-help">
          <InfoHint width={340}>
            Each cell is the Pearson correlation between the per-user proportion
            of two signal types. <strong>Red</strong> = users who fire one tend
            to fire the other ("engaged-positive" cluster).{" "}
            <strong>Blue</strong> = users who fire one tend NOT to fire the other
            ("opposing populations"). <strong>White (~0)</strong> = independent
            at the user-population level. Values below |0.3| are weak signal;
            above |0.5| are interesting; near |1.0| are nearly redundant.
          </InfoHint>
        </span>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────

// Diverging red-white-blue scale clamped to [-1, 1].
function corrColor(v) {
  const clamped = Math.max(-1, Math.min(1, v));
  if (clamped >= 0) {
    // 0 → white, +1 → deep red
    const intensity = clamped;
    const r = 255;
    const g = Math.round(255 - intensity * 175);
    const b = Math.round(255 - intensity * 175);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // 0 → white, -1 → deep blue
    const intensity = -clamped;
    const r = Math.round(255 - intensity * 175);
    const g = Math.round(255 - intensity * 130);
    const b = 255;
    return `rgb(${r}, ${g}, ${b})`;
  }
}

// Contrasting text color so cells stay legible at high saturation.
function textColor(v) {
  return Math.abs(v) > 0.55 ? "#fff" : "var(--text)";
}

// Compact label — keeps the row/column rail narrow.
function prettyShort(s) {
  return s
    .replace("format_change_request", "fmt_change_req")
    .replace("content_correction",    "content_corr")
    .replace("reask_same_question",   "reask_same")
    .replace("it_worked_statement",   "it_worked")
    .replace("deeper_question",       "deeper_q")
    .replace("session_abandon",       "abandon")
    .replace("regenerate_click",      "regenerate");
}

// Plain-English interpretation
function interpret(v) {
  const a = Math.abs(v);
  if (a < 0.1)  return "(independent)";
  if (a < 0.3)  return v > 0 ? "(weak positive)" : "(weak negative)";
  if (a < 0.5)  return v > 0 ? "(moderate positive)" : "(moderate negative)";
  if (a < 0.7)  return v > 0 ? "(strong positive)" : "(strong negative)";
  return v > 0 ? "(near-redundant)" : "(near-opposing)";
}
