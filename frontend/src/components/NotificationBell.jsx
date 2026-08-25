/**
 * Adviser notifications — the bell in the top-right of the advisor bar.
 *
 * WHY A PANEL AND NOT A TOAST
 * Alerts say a named client is struggling right now. A toast that fades
 * after four seconds is exactly the wrong shape for that: the adviser may
 * be mid-task, and the whole point is that it waits until someone deals
 * with it. So it accumulates, shows a count, and each item is dismissed
 * deliberately.
 *
 * ACKNOWLEDGEMENT IS EXPLICIT
 * Opening the panel does NOT clear the badge. An adviser glancing at a
 * list has not necessarily contacted anyone, and auto-clearing would
 * quietly lose the one that mattered. "Mark done" is a separate click,
 * per alert.
 */
import { useEffect, useState, useRef } from "react";
import { api } from "../api.js";

const TRIGGER_LABEL = {
  explicit_negative: "Said it wasn't helpful",
  repeated_decline: "Report couldn't answer them",
};

// Slow on purpose. These are "call this client back today" signals, not
// live chat — a 30s poll on an admin screen is noise with no upside.
const POLL_MS = 60000;

function timeAgo(iso) {
  if (!iso) return "";
  const secs = Math.floor((Date.now() - new Date(iso + "Z").getTime()) / 1000);
  if (secs < 60) return "just now";
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [unread, setUnread] = useState(0);
  const [err, setErr] = useState("");
  const boxRef = useRef(null);

  async function load() {
    try {
      const d = await api.listAlerts();
      setAlerts(d.alerts || []);
      setUnread(d.unread || 0);
      setErr("");
    } catch (e) {
      // A failing poll must not throw away what is already on screen —
      // the adviser keeps whatever they had, and sees that it is stale.
      setErr(String(e.message || e));
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, []);

  // Click-outside to close. Bound only while open so the document is not
  // carrying a listener for a panel nobody is looking at.
  useEffect(() => {
    if (!open) return;
    function onDoc(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function ack(id) {
    // Optimistic: the row greys out immediately, because waiting on a
    // round-trip to acknowledge something you just read feels broken.
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === id ? { ...a, acknowledged: true } : a)));
    setUnread((n) => Math.max(0, n - 1));
    try {
      await api.acknowledgeAlert(id);
    } catch {
      load();                       // server disagreed — resync the truth
    }
  }

  return (
    <div className="nb-wrap" ref={boxRef}>
      <button
        className="nb-btn"
        onClick={() => setOpen((v) => !v)}
        aria-label={unread ? `${unread} unread notifications` : "Notifications"}
        aria-expanded={open}
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"
             strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unread > 0 && (
          <span className="nb-badge">{unread > 9 ? "9+" : unread}</span>
        )}
      </button>

      {open && (
        <div className="nb-panel" role="dialog" aria-label="Client notifications">
          <div className="nb-head">
            <strong>Clients who may need you</strong>
            {unread > 0 && <span className="nb-count">{unread} new</span>}
          </div>

          {err && <div className="nb-err">Couldn't refresh — {err}</div>}

          {!alerts.length && !err && (
            <div className="nb-empty">
              Nothing right now. Alerts appear here when a client says
              something wasn't helpful, or the report repeatedly can't
              answer them.
            </div>
          )}

          <div className="nb-list">
            {alerts.map((a) => (
              <div key={a.alert_id}
                   className={"nb-item" + (a.acknowledged ? " done" : "")}>
                <div className="nb-item-top">
                  <span className="nb-client">{a.client_name}</span>
                  <span className="nb-when">{timeAgo(a.created_at)}</span>
                </div>
                <div className="nb-trigger">
                  {TRIGGER_LABEL[a.trigger] || a.trigger}
                </div>
                <div className="nb-detail">{a.detail}</div>
                {!a.acknowledged && (
                  <button className="nb-ack" onClick={() => ack(a.alert_id)}>
                    Mark done
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
