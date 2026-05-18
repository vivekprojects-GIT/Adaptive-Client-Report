import { useEffect } from "react";

export default function Toast({ message, kind = "", onClose, durationMs = 2400 }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, durationMs);
    return () => clearTimeout(t);
  }, [message, onClose, durationMs]);

  if (!message) return null;
  return (
    <div className={`toast ${kind}`}>
      {message}
    </div>
  );
}
