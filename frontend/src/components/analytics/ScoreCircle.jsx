/**
 * ScoreCircle — SVG donut chart showing a 0-100 confidence score.
 * Colors follow the Claude palette and match the .conf-chip tiers:
 *   HIGH      → green   (--pos)
 *   MODERATE  → orange  (--primary)
 *   LOW       → muted gray
 */
export default function ScoreCircle({ value = 0, tier = "LOW", size = 92 }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = (v / 100) * c;

  // Claude-palette tier colors
  const color =
    tier === "HIGH"     ? "#4f8a4d" :   // --pos
    tier === "MODERATE" ? "#c87a4c" :   // --primary
                          "#8c8980";    // --muted

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="score-circle">
      {/* Track ring */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#ece9e3" strokeWidth={stroke}
      />
      {/* Progress ring */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dasharray 0.5s ease" }}
      />
      {/* Center number */}
      <text
        x="50%" y="50%"
        textAnchor="middle" dominantBaseline="central"
        fill="#2d2a26" fontSize={size * 0.32} fontWeight="600"
        fontFamily="Inter, system-ui, sans-serif"
      >
        {Math.round(v)}
      </text>
    </svg>
  );
}
