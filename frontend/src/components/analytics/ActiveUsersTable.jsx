/**
 * ActiveUsersTable — admin-facing customer outreach view.
 *
 * Each row is a user active in the selected window:
 *   user_id_hash · top_topic · interest_score · last_activity · contact-ready badge
 *
 * Clicking "Inspect" sets the user as the inspected user on the page, jumping
 * to their cognitive-facet cards above.
 */
export default function ActiveUsersTable({ rows, onInspect, windowLabel = "", activeHash = "" }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="empty-state">
        No users active in window <strong>{windowLabel || "—"}</strong>.
      </div>
    );
  }

  return (
    <table className="tbl active-users-tbl">
      <thead>
        <tr>
          <th>User</th>
          <th>Top topic</th>
          <th className="num">Interest</th>
          <th className="num">Turns</th>
          <th className="num">Topics</th>
          <th className="num">Pos / total rewards</th>
          <th>Last seen</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((u) => {
          const isActive = activeHash === u.user_id_hash;
          const rowClass = [
            u.contact_ready ? "ready" : "",
            isActive ? "row-active" : "",
          ].filter(Boolean).join(" ");
          return (
          <tr key={u.user_id_hash} className={rowClass}>
            <td>
              <div className="user-name">{u.display_name || shortHash(u.user_id_hash)}</div>
              <code className="user-hash" title="Persisted as a SHA-256 hash; this is the only identifier stored in the analytics layer.">
                {shortHash(u.user_id_hash)}
              </code>
              {u.intents?.length > 0 && (
                <div className="intent-mini">
                  {u.intents.slice(0, 3).map((i) => (
                    <span key={i} className="intent-mini-pill">{i}</span>
                  ))}
                </div>
              )}
            </td>
            <td>
              <span className="topic-chip">{u.top_topic || "—"}</span>
              {u.topics?.length > 1 && (
                <span className="topic-more">+{u.topics.length - 1} more</span>
              )}
            </td>
            <td className={`num ${interestClass(u.top_interest_score)}`}>
              <strong>{fmt(u.top_interest_score)}</strong>
            </td>
            <td className="num">{u.turn_count}</td>
            <td className="num">{u.topic_count}</td>
            <td className="num">
              {u.positive_rewards}
              <span className="reward-divider"> / </span>
              {u.applied_rewards}
            </td>
            <td className="last-seen">{relativeTime(u.last_activity_ts)}</td>
            <td>
              {u.do_not_contact ? (
                <span className="status-blocked" title="do_not_contact flag is set in the directory">
                  ⊘ Do not contact
                </span>
              ) : !u.compliance_eligible ? (
                <span className="status-blocked" title="compliance_eligible=false in the directory">
                  ⊘ Compliance block
                </span>
              ) : u.contact_ready ? (
                <span className="contact-ready-yes" title={u.recommendation_reason}>
                  ● Contact ready
                </span>
              ) : (
                <span className="contact-ready-no" title={u.recommendation_reason}>
                  ○ Below threshold
                </span>
              )}
              {u.recommendation_reason && (
                <div className="recommendation-reason">{u.recommendation_reason}</div>
              )}
            </td>
            <td>
              <button
                className={`btn-secondary btn-tiny ${isActive ? "btn-active" : ""}`}
                onClick={() => onInspect?.(u.user_id_hash)}
                title="Load this user's cognitive facets, interests, and offers"
                disabled={isActive}
              >
                {isActive ? "● Inspecting" : "Inspect →"}
              </button>
            </td>
          </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function shortHash(h) {
  if (!h) return "—";
  return h.length > 10 ? `${h.slice(0, 10)}…` : h;
}

function interestClass(v) {
  const x = Number(v) || 0;
  if (x >= 0.7) return "pos";
  if (x <= 0.3) return "zero";
  return "";
}

function fmt(v) {
  if (v == null) return "—";
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(2);
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
