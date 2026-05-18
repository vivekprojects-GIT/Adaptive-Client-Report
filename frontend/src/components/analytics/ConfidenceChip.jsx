/**
 * ConfidenceChip — colored pill showing the confidence tier of a facet.
 *  HIGH      — blue   (≥10 interactions, ≥75 score)
 *  MODERATE  — green  (≥4  interactions, ≥50 score)
 *  LOW       — orange (everything else)
 */
export default function ConfidenceChip({ tier = "LOW", count }) {
  const lower = String(tier).toUpperCase();
  const cls =
    lower === "HIGH"     ? "conf-chip conf-high"     :
    lower === "MODERATE" ? "conf-chip conf-moderate" :
                            "conf-chip conf-low";

  return (
    <span className={cls}>
      <span className="conf-dot" />
      {lower} CONFIDENCE
      {count != null && <span className="conf-count">· {count} interactions</span>}
    </span>
  );
}
