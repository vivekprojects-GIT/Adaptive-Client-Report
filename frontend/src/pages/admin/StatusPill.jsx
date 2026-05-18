import { useState } from "react";
import { api } from "../../api.js";

/**
 * StatusPill — clickable dropdown showing ACTIVE / PAUSED on any config row.
 *
 * Click → opens a tiny menu with the two options. Picking the other one POSTs
 * /config/status and calls onChanged so the parent tab can refresh.
 *
 * The runtime path (orchestrator, recommender, classifier lookups) filters
 * by `status=ACTIVE`, so flipping to PAUSED removes the row from the runtime
 * immediately. It stays visible in the admin table so it can be re-activated.
 *
 * Props:
 *   entityType   — "intent" / "strategy" / "instruction" / "policy" /
 *                  "signal_routing" / "reward_scale" / "offer_policy"
 *   entityId     — row.entity_id (or intent_id / strategy_id / etc)
 *   version      — required for instructions; omit for everything else
 *   status       — current value from the row
 *   onChanged    — callback the parent uses to refresh its list
 *   notify       — toast helper from the parent
 */
export default function StatusPill({ entityType, entityId, version, status, onChanged, notify }) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  const current = (status || "ACTIVE").toUpperCase();
  // "INACTIVE" is the canonical paused state; we label it "PAUSED" in the UI
  // because that's the verb the admin thinks in.
  const isActive = current === "ACTIVE";
  const label    = isActive ? "ACTIVE" : (current === "DRAFT" ? "DRAFT" : "PAUSED");
  const nextStatus = isActive ? "INACTIVE" : "ACTIVE";
  const nextLabel  = isActive ? "Pause" : "Activate";

  async function flip() {
    if (busy) return;
    setBusy(true);
    setOpen(false);
    try {
      await api.setConfigStatus(entityType, entityId, nextStatus, version);
      notify?.(
        nextStatus === "ACTIVE"
          ? `Activated ${entityId}${version ? `@${version}` : ""}`
          : `Paused ${entityId}${version ? `@${version}` : ""} — runtime will skip it`
      );
      onChanged?.();
    } catch (err) {
      notify?.("Status change failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="status-pill-wrap">
      <button
        className={`status-pill status-pill-${current.toLowerCase()}`}
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        title={isActive
          ? "ACTIVE — runtime reads this row. Click to pause."
          : "PAUSED — runtime skips this row. Click to re-activate."}
      >
        <span className="status-pill-dot" />
        {busy ? "…" : label}
        <span className="status-pill-caret">▾</span>
      </button>
      {open && !busy && (
        <span className="status-pill-menu">
          <button
            className="status-pill-menu-item"
            onClick={flip}
          >
            {nextLabel}
          </button>
          <button
            className="status-pill-menu-item status-pill-menu-cancel"
            onClick={() => setOpen(false)}
          >
            Cancel
          </button>
        </span>
      )}
    </span>
  );
}
