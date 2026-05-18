/**
 * MiniLineChart — small SVG line/area chart for analytics trend tiles.
 *
 * Designed to fit inline next to a number tile or above a list. NOT a
 * general-purpose chart library — supports just the shapes we need:
 *
 *   • Single series   →  pass `data` as [{date, value}]
 *   • Multi-series    →  pass `series` as [{name, color?, points: [{date, value}]}]
 *
 * Renders an SVG with:
 *   - x-axis: evenly spaced date ticks (first, middle, last labeled)
 *   - y-axis: derived from data range with a 0 floor; no left ticks (keeps it small)
 *   - Hover tooltip shows the date and per-series values
 *   - Optional fill under the line for the single-series variant (looks like a
 *     "spark area" rather than a line)
 *
 * Why hand-rolled SVG and not Recharts?
 *   The bundle is already 285 kB and we render maybe 4 of these. Recharts
 *   would add ~120 kB gzipped for a fancier version of the same thing.
 *
 * Props:
 *   data         single-series: [{date: "2026-05-12", value: 4}]
 *   series       multi-series:  [{name, color?, points: [{date, value}]}]
 *   width        default 320
 *   height       default 80
 *   color        single-series color (default brand orange)
 *   fillUnder    single-series only — fill area below line (default true)
 *   yLabel       optional y-axis text label (rendered as title attribute)
 *   formatValue  optional (v) => string for tooltip values
 */
import { useMemo, useState } from "react";

const DEFAULT_COLORS = [
  "#d76a35",  // brand orange
  "#3b82c4",  // blue
  "#5fa86b",  // green
  "#b87cb8",  // purple
  "#d4a017",  // gold
];

export default function MiniLineChart({
  data        = null,
  series      = null,
  width       = 320,
  height      = 80,
  color       = "#d76a35",
  fillUnder   = true,
  yLabel      = "",
  formatValue = (v) => String(v),
  showLegend  = false,
}) {
  // ── Normalize to internal multi-series shape ──────────────────────────
  const normSeries = useMemo(() => {
    if (series && series.length) {
      return series.map((s, i) => ({
        name:   s.name,
        color:  s.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length],
        points: s.points || [],
      }));
    }
    if (data && data.length) {
      return [{ name: yLabel || "value", color, points: data.map((d) => ({ date: d.date, value: d.value ?? d.count ?? 0 })) }];
    }
    return [];
  }, [data, series, color, yLabel]);

  // ── Date axis (union of all dates) ────────────────────────────────────
  const allDates = useMemo(() => {
    const s = new Set();
    for (const ser of normSeries) {
      for (const p of ser.points) s.add(p.date);
    }
    return Array.from(s).sort();
  }, [normSeries]);

  // ── Y range ───────────────────────────────────────────────────────────
  const yMax = useMemo(() => {
    let m = 0;
    for (const ser of normSeries) {
      for (const p of ser.points) {
        const v = Number(p.value ?? p.count ?? 0);
        if (v > m) m = v;
      }
    }
    return m || 1;
  }, [normSeries]);

  // ── Hover state ───────────────────────────────────────────────────────
  const [hoverIdx, setHoverIdx] = useState(null);

  if (allDates.length === 0) {
    return (
      <div className="mini-chart-empty" style={{ width, height }}>
        no data yet
      </div>
    );
  }

  // ── Geometry ──────────────────────────────────────────────────────────
  const padL = 8;
  const padR = 8;
  const padT = 6;
  const padB = 18;
  const innerW = width  - padL - padR;
  const innerH = height - padT - padB;
  // x positions per date index (evenly spaced)
  const n = allDates.length;
  const xAt = (i) => padL + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v) => padT + innerH - (v / yMax) * innerH;

  // For each series → SVG path
  const lookup = (ser) => {
    const m = new Map();
    for (const p of ser.points) m.set(p.date, Number(p.value ?? p.count ?? 0));
    return m;
  };
  const seriesPaths = normSeries.map((ser) => {
    const m = lookup(ser);
    let d = "";
    let started = false;
    allDates.forEach((date, i) => {
      const v = m.get(date);
      if (v == null) return;
      const x = xAt(i);
      const y = yAt(v);
      d += (started ? " L " : "M ") + x.toFixed(1) + " " + y.toFixed(1);
      started = true;
    });
    // Closed area path (only used for single-series fill)
    let area = "";
    if (started && fillUnder && normSeries.length === 1) {
      const firstIdx = allDates.findIndex((dt) => m.has(dt));
      const lastIdx  = allDates.length - 1 - [...allDates].reverse().findIndex((dt) => m.has(dt));
      area = `M ${xAt(firstIdx).toFixed(1)} ${yAt(0).toFixed(1)} ` +
             d.replace(/^M /, "L ") +
             ` L ${xAt(lastIdx).toFixed(1)} ${yAt(0).toFixed(1)} Z`;
    }
    return { ser, path: d, area };
  });

  // Date tick labels (first, middle, last)
  const tickIdxs = n <= 1 ? [0] :
                   n <= 3 ? allDates.map((_, i) => i) :
                          [0, Math.floor((n - 1) / 2), n - 1];

  // Tooltip content for hovered index
  const tip = hoverIdx == null ? null : (() => {
    const date = allDates[hoverIdx];
    const rows = normSeries.map((ser) => {
      const v = lookup(ser).get(date);
      return v == null ? null : { name: ser.name, color: ser.color, value: v };
    }).filter(Boolean);
    return { date, rows };
  })();

  return (
    <div className="mini-chart" title={yLabel || ""}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={yLabel || "trend chart"}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Faint y-baseline */}
        <line
          x1={padL} y1={padT + innerH}
          x2={padL + innerW} y2={padT + innerH}
          stroke="var(--border)" strokeWidth="1"
        />

        {/* Area fill (single series, optional) */}
        {seriesPaths.map(({ ser, area }, i) =>
          area ? (
            <path
              key={`area-${i}`}
              d={area}
              fill={ser.color}
              fillOpacity="0.12"
            />
          ) : null
        )}

        {/* Lines */}
        {seriesPaths.map(({ ser, path }, i) => (
          <path
            key={`line-${i}`}
            d={path}
            fill="none"
            stroke={ser.color}
            strokeWidth="1.6"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* Hover dot (per series at hovered index) */}
        {hoverIdx != null && normSeries.map((ser, i) => {
          const v = lookup(ser).get(allDates[hoverIdx]);
          if (v == null) return null;
          return (
            <circle
              key={`dot-${i}`}
              cx={xAt(hoverIdx)}
              cy={yAt(v)}
              r="3"
              fill={ser.color}
              stroke="var(--surface)"
              strokeWidth="1.5"
            />
          );
        })}

        {/* Hover vertical guide */}
        {hoverIdx != null && (
          <line
            x1={xAt(hoverIdx)} y1={padT}
            x2={xAt(hoverIdx)} y2={padT + innerH}
            stroke="var(--muted)" strokeWidth="0.7" strokeDasharray="2 2"
            opacity="0.5"
          />
        )}

        {/* Invisible mouse-area rects per data point */}
        {allDates.map((_, i) => {
          const left  = i === 0 ? 0 : (xAt(i - 1) + xAt(i)) / 2;
          const right = i === n - 1 ? width : (xAt(i) + xAt(i + 1)) / 2;
          return (
            <rect
              key={`hit-${i}`}
              x={left}
              y={0}
              width={Math.max(right - left, 1)}
              height={height}
              fill="transparent"
              onMouseEnter={() => setHoverIdx(i)}
            />
          );
        })}

        {/* x-axis ticks */}
        {tickIdxs.map((i) => (
          <text
            key={`tick-${i}`}
            x={xAt(i)}
            y={height - 4}
            textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}
            fontSize="10"
            fill="var(--muted)"
          >
            {fmtTick(allDates[i])}
          </text>
        ))}
      </svg>

      {/* Tooltip */}
      {tip && (
        <div className="mini-chart-tip">
          <div className="mini-chart-tip-date">{tip.date}</div>
          {tip.rows.map((r) => (
            <div key={r.name} className="mini-chart-tip-row">
              <span className="mini-chart-tip-swatch" style={{ background: r.color }} />
              <span className="mini-chart-tip-name">{r.name}</span>
              <span className="mini-chart-tip-val">{formatValue(r.value)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      {showLegend && normSeries.length > 1 && (
        <div className="mini-chart-legend">
          {normSeries.map((ser) => (
            <span key={ser.name} className="mini-chart-legend-item">
              <span className="mini-chart-legend-swatch" style={{ background: ser.color }} />
              {ser.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function fmtTick(isoDate) {
  // "2026-05-12" → "May 12"
  if (!isoDate || isoDate.length < 10) return isoDate || "";
  const [, m, d] = isoDate.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(m, 10) - 1]} ${parseInt(d, 10)}`;
}
