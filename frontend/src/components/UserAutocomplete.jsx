import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";

/**
 * UserAutocomplete — reusable user-search input with live suggestions.
 *
 * Loads the active-users roster once on mount and filters as the admin types.
 * On pick, fires `onApply(user_id_hash)` — the hash is guaranteed to exist
 * in the bandit/turn tables, so downstream filters can't miss the user just
 * because the admin typed a display name like "Alex Chen".
 *
 * Props:
 *   value         (string)   — current selected user_id_hash / raw user_id
 *   onApply       (string)→  — called when admin picks a suggestion or hits Enter
 *   placeholder   (string)
 *   allowEmpty    (bool)     — show a "(all users)" empty-state option
 *   suggestions   (array?)   — pre-loaded user list; if omitted, fetches itself
 *   className     (string?)  — additional class on the wrapper
 *
 * Matches:
 *   - case-insensitive substring on display_name
 *   - prefix match on user_id_hash
 *   - exact match on raw user_id (if you happen to type one)
 */
export default function UserAutocomplete({
  value = "",
  onApply,
  placeholder = "Search by name or hash",
  allowEmpty = false,
  suggestions: providedSuggestions = null,
  className = "",
}) {
  const [draft, setDraft]   = useState(value || "");
  const [open, setOpen]     = useState(false);
  const [highlight, setHi]  = useState(0);
  const [loaded, setLoaded] = useState(providedSuggestions || []);
  const wrapRef = useRef(null);

  useEffect(() => { setDraft(value || ""); }, [value]);

  // Load active users once if caller didn't provide them.
  // Use a wide window so even dormant users show up in the suggestions.
  useEffect(() => {
    if (providedSuggestions !== null) {
      setLoaded(providedSuggestions);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const r = await api.activeUsers(3650, 0, 500);  // ~10 years window
        if (!cancelled) setLoaded(Array.isArray(r) ? r : []);
      } catch { /* dropdown just shows no suggestions */ }
    })();
    return () => { cancelled = true; };
  }, [providedSuggestions]);

  // Click-outside closes dropdown
  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const matches = useMemo(() => {
    const q = draft.trim().toLowerCase();
    if (!q) return loaded.slice(0, 8);   // empty query: show top 8
    const out = [];
    const seen = new Set();
    for (const u of loaded) {
      const name = (u.display_name || "").toLowerCase();
      const hash = (u.user_id_hash || "").toLowerCase();
      if (name.includes(q) || hash.includes(q)) {
        const key = u.user_id_hash || u.display_name;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(u);
        if (out.length >= 8) break;
      }
    }
    return out;
  }, [draft, loaded]);

  useEffect(() => { setHi(0); }, [matches.length]);

  function pick(user) {
    setDraft(user.user_id_hash);
    onApply?.(user.user_id_hash);
    setOpen(false);
  }

  function commit() {
    if (open && matches[highlight]) {
      pick(matches[highlight]);
    } else {
      // Free text — let the backend's _resolve_user_hash handle it
      onApply?.(draft.trim());
      setOpen(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHi((h) => (h + 1) % Math.max(matches.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHi((h) => (h - 1 + Math.max(matches.length, 1)) % Math.max(matches.length, 1));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <span className={`user-autocomplete ${className}`} ref={wrapRef}>
      <input
        type="text"
        value={draft}
        onChange={(e) => { setDraft(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
      />
      {draft && (
        <button
          type="button"
          className="ua-clear"
          onClick={() => { setDraft(""); onApply?.(""); setOpen(false); }}
          title="Clear"
        >
          ×
        </button>
      )}
      {open && (
        <ul className="ua-dropdown" role="listbox">
          {allowEmpty && (
            <li
              role="option"
              aria-selected={false}
              className="ua-option ua-option-empty"
              onMouseDown={(e) => { e.preventDefault(); pick({ user_id_hash: "", display_name: "all users" }); }}
            >
              <span className="opt-name">— all users —</span>
              <span className="opt-topic">no filter</span>
            </li>
          )}
          {matches.length === 0 && (
            <li className="ua-option ua-empty">No matches</li>
          )}
          {matches.map((u, i) => (
            <li
              key={u.user_id_hash}
              role="option"
              aria-selected={i === highlight}
              className={`ua-option ${i === highlight ? "active" : ""}`}
              onMouseEnter={() => setHi(i)}
              onMouseDown={(e) => { e.preventDefault(); pick(u); }}
            >
              <span className="opt-name">{u.display_name || shortHash(u.user_id_hash)}</span>
              <code className="opt-hash">{shortHash(u.user_id_hash)}</code>
              {u.top_topic && <span className="opt-topic">top: {u.top_topic}</span>}
              {u.contact_ready && <span className="opt-ready" title="Contact-ready">●</span>}
            </li>
          ))}
        </ul>
      )}
    </span>
  );
}

function shortHash(h) {
  if (!h) return "";
  return h.length > 14 ? `${h.slice(0, 14)}…` : h;
}
