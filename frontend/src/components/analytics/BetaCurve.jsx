/**
 * BetaCurve — SVG bell-curve visualization of a Beta(α, β) distribution.
 *
 * We don't use the gamma function; instead we plot the unnormalized density
 *   f(x) ∝ x^(α-1) · (1-x)^(β-1)
 * and rescale to the chart height. That preserves the shape (mode, skew)
 * which is all we need visually.
 */
export default function BetaCurve({
  alpha = 1,
  beta = 1,
  label = "",
  color = "#c87a4c",   // Claude orange — leader curve
  width = 220,
  height = 70,
}) {
  const a = Math.max(1, Number(alpha) || 1);
  const b = Math.max(1, Number(beta) || 1);

  const N = 60;
  const xs = Array.from({ length: N + 1 }, (_, i) => i / N);
  const ys = xs.map((x) => {
    if (x === 0 && a > 1) return 0;
    if (x === 1 && b > 1) return 0;
    if (x === 0 || x === 1) return 1e-9;
    return Math.pow(x, a - 1) * Math.pow(1 - x, b - 1);
  });
  const maxY = Math.max(...ys, 1e-9);

  const pad = 6;
  const w = width - 2 * pad;
  const h = height - 2 * pad;

  const points = xs.map((x, i) => {
    const px = pad + x * w;
    const py = pad + h - (ys[i] / maxY) * h;
    return `${px.toFixed(2)},${py.toFixed(2)}`;
  });

  // Build a closed area path for fill underneath the curve
  const areaPath =
    `M ${pad},${pad + h} ` +
    points.map((p) => `L ${p}`).join(" ") +
    ` L ${pad + w},${pad + h} Z`;

  const linePath = `M ${points.join(" L ")}`;

  // Mean of Beta(a,b) is a/(a+b) — draw a faint vertical tick at the mode
  const mean = a / (a + b);
  const meanX = pad + mean * w;

  return (
    <div className="beta-curve">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <path d={areaPath} fill={color} fillOpacity="0.15" />
        <path d={linePath} fill="none" stroke={color} strokeWidth="2" />
        <line
          x1={meanX} y1={pad} x2={meanX} y2={pad + h}
          stroke={color} strokeOpacity="0.45" strokeWidth="1" strokeDasharray="2 3"
        />
        <line
          x1={pad} y1={pad + h} x2={pad + w} y2={pad + h}
          stroke="#ece9e3" strokeWidth="1"
        />
      </svg>
      {label && (
        <div className="beta-label" style={{ color }}>
          {label}{" "}
          <span
            className="beta-params"
            title={
              "Visualization only — the runtime bandit is UCB, which uses count + " +
              "avg_reward, not α/β. We project (avg_reward + 1) / 2 onto a Beta " +
              "distribution so the curve shape (peak + width) reflects the average + count."
            }
          >
            shape ≈ Beta({a}, {b})
          </span>
        </div>
      )}
    </div>
  );
}
