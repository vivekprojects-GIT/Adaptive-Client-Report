import { useState, useRef, useEffect } from "react";

/**
 * InfoHint — small ⓘ icon next to a label. Hover (or click) opens a tooltip
 * with a longer explanation. Keeps the page label terse while still giving
 * the admin a way to learn what a number means.
 *
 * Usage:
 *   <h3>Offer readiness <InfoHint>...long text...</InfoHint></h3>
 *
 * Props:
 *   children    — tooltip content (string or JSX)
 *   align       — "left" (default) | "right" — which edge the bubble anchors to
 *   width       — tooltip width in px (default 280)
 */
export default function InfoHint({ children, align = "left", width = 280 }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  return (
    <span
      className="info-hint"
      ref={wrapRef}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="info-hint-icon"
        aria-label="What does this mean?"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        i
      </button>
      {open && (
        <span
          className={`info-hint-bubble align-${align}`}
          style={{ width: `${width}px` }}
          role="tooltip"
        >
          {children}
        </span>
      )}
    </span>
  );
}
