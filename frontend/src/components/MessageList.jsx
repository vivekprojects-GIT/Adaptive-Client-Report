import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

export default function MessageList({ messages, showMeta, onFeedback }) {
  const wrapRef = useRef(null);

  // Auto-scroll to the bottom on new messages
  useEffect(() => {
    if (!wrapRef.current) return;
    wrapRef.current.scrollTop = wrapRef.current.scrollHeight;
  }, [messages]);

  const lastAsstIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && !messages[i]._placeholder) return i;
    }
    return -1;
  })();

  return (
    <div className="messages" ref={wrapRef}>
      {messages.length === 0 ? (
        <div className="empty-chat">
          <div className="empty-chat-title">How can I help you today?</div>
          <div>
            Ask a finance question to get started. Click 👍/👎 on any answer —
            the bandit learns which response formats work best for you.
          </div>
        </div>
      ) : (
        <div className="messages-inner">
          {messages.map((m, i) => (
            <Message
              key={m.message_id || i}
              message={m}
              isLastAssistant={i === lastAsstIdx}
              showMeta={showMeta}
              onFeedback={onFeedback}
            />
          ))}
        </div>
      )}
    </div>
  );
}
