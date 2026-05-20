import { useEffect, useRef, useState } from "react";

export default function Composer({ onSend, disabled, sessionId }) {
  const [text, setText] = useState("");
  const taRef = useRef(null);

  // Auto-resize the textarea up to a cap (handled by CSS max-height + overflow)
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 220) + "px";
  }, [text]);

  function handleSubmit(e) {
    e?.preventDefault?.();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <div className="composer-wrap">
      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          ref={taRef}
          rows={1}
          placeholder="Message APE..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button
          type="submit"
          className="composer-send"
          disabled={disabled || !text.trim()}
          title="Send message"
          aria-label="Send"
        >
          <SendIcon />
        </button>
      </form>
      <div className="composer-footer">
        <span>APE may produce inaccurate information about people, places, or facts.</span>
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 19V5" />
      <path d="M5 12l7-7 7 7" />
    </svg>
  );
}
