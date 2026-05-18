/**
 * DateFilter — segmented control for the analytics time window.
 * Today (since 00:00) · 7d · 30d · 90d · All.
 *
 * Emits the `days` value via onChange:
 *   "today" → 0       (server interprets as "since start of today")
 *   "7d"    → 7
 *   "30d"   → 30
 *   "90d"   → 90
 *   "all"   → 3650    (10 years — effectively unbounded)
 */
const OPTIONS = [
  { id: "today", label: "Today", days: 0,    title: "Activity since 00:00 today" },
  { id: "7d",    label: "7d",    days: 7,    title: "Last 7 days" },
  { id: "30d",   label: "30d",   days: 30,   title: "Last 30 days" },
  { id: "90d",   label: "90d",   days: 90,   title: "Last 90 days" },
  { id: "all",   label: "All",   days: 3650, title: "All-time" },
];

export default function DateFilter({ value = "30d", onChange }) {
  return (
    <div className="date-filter" role="tablist" aria-label="Date window">
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          role="tab"
          aria-selected={value === opt.id}
          className={`date-pill ${value === opt.id ? "active" : ""}`}
          title={opt.title}
          onClick={() => onChange?.(opt.id, opt.days)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export const DATE_FILTER_OPTIONS = OPTIONS;

export function daysForFilter(id) {
  return (OPTIONS.find((o) => o.id === id) || OPTIONS[2]).days;
}
