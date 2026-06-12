import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Sidebar({
  userId,
  onUserIdChange,
  sessionId,
  sessions,
  onSwitchSession,
  onDeleteSession,
  onClearChat,
  onClearDb,
  onNewSession,
}) {
  const groups = groupSessionsByRecency(sessions);
  const initial = (userId || "U").slice(0, 1).toUpperCase();

  // Draft-edit the user id locally; commit on Enter or blur. Committing on
  // every keystroke made the field impossible to edit (an empty field
  // snapped back to demo_user mid-typing and each keystroke switched users).
  const [draft, setDraft] = useState(userId);
  useEffect(() => { setDraft(userId); }, [userId]);

  function commitUserId() {
    const v = (draft || "").trim();
    if (v && v !== userId) onUserIdChange(v);
    else setDraft(userId);   // empty or unchanged — revert the draft
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-row">
          <div className="brand-text">
            <h1>APE</h1>
            <span className="brand-sub">Adaptive Prompt Engine</span>
          </div>
        </div>
        <button className="btn-new-chat" onClick={onNewSession}>
          <NewChatIcon />
          <span>New chat</span>
        </button>
      </div>

      <div className="session-section">
        {sessions.length === 0 && (
          <div className="session-empty">
            No conversations yet. Send a message to start.
          </div>
        )}
        {groups.map(({ label, items }) => items.length === 0 ? null : (
          <div key={label}>
            <div className="session-group-title">{label}</div>
            <ul className="session-list">
              {items.map((s) => (
                <li
                  key={s.session_id}
                  className={`session-row ${s.session_id === sessionId ? "active" : ""}`}
                >
                  <button
                    className="session-link"
                    onClick={() => onSwitchSession(s.session_id)}
                    title={s.first_user_message || "(no preview)"}
                  >
                    {truncate(s.first_user_message || "(empty chat)", 40)}
                  </button>
                  <button
                    className="session-del"
                    onClick={() => {
                      if (window.confirm("Delete this chat?")) onDeleteSession(s.session_id);
                    }}
                    title="Delete chat"
                  >x</button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="identity-row">
          <div className="identity-avatar">{initial}</div>
          <input
            className="identity-input"
            type="text"
            value={draft}
            placeholder="user_id"
            title="Type a user id and press Enter to switch"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") e.target.blur(); }}
            onBlur={commitUserId}
          />
        </div>
        <nav className="sidebar-actions">
          <Link to="/analytics">Analytics</Link>
          <Link to="/admin">Admin / Config</Link>
          <button onClick={onClearChat} className="danger">Clear my history</button>
          <button onClick={onClearDb} className="danger">Clear ALL database</button>
        </nav>
      </div>
    </aside>
  );
}

// ---------- Helpers ----------

function NewChatIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n).trimEnd() + "..." : s;
}

function groupSessionsByRecency(sessions) {
  const today = startOfDay(new Date());
  const yesterday = new Date(today.getTime() - 86400000);
  const sevenDaysAgo = new Date(today.getTime() - 7 * 86400000);
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 86400000);

  const groups = {
    today:    { label: "Today",         items: [] },
    yesterday:{ label: "Yesterday",     items: [] },
    week:     { label: "Previous 7 days", items: [] },
    month:    { label: "Previous 30 days", items: [] },
    older:    { label: "Older",         items: [] },
  };

  for (const s of sessions) {
    const t = parseTime(s.last_active_at);
    if (!t) { groups.older.items.push(s); continue; }
    if (t >= today)         groups.today.items.push(s);
    else if (t >= yesterday) groups.yesterday.items.push(s);
    else if (t >= sevenDaysAgo) groups.week.items.push(s);
    else if (t >= thirtyDaysAgo) groups.month.items.push(s);
    else                     groups.older.items.push(s);
  }
  return [groups.today, groups.yesterday, groups.week, groups.month, groups.older];
}

function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}
function parseTime(s) {
  try { return new Date(s); } catch { return null; }
}
