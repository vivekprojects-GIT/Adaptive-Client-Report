import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

export default function MessageList({ messages, showMeta, onPrompt, onFeedback, onRegenerate, rated }) {
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
          <div className="empty-chat-mark" aria-hidden="true">A</div>
          <div className="empty-chat-title">Ask APE about a money decision</div>
          <div className="empty-chat-sub">
            Start with one of these, or write your own question.
          </div>
          <div className="prompt-grid">
            {PROMPTS.map((prompt) => (
              <button
                key={prompt}
                className="prompt-card"
                type="button"
                onClick={() => onPrompt?.(prompt)}
              >
                <span>{prompt}</span>
                <PromptArrow />
              </button>
            ))}
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
              onRegenerate={onRegenerate}
              ratedSignal={rated?.[m.response_id]}
            />
          ))}
        </div>
      )}
    </div>
  );
}

const PROMPTS = [
  "Compare Roth IRA vs Traditional IRA",
  "Make a debt payoff plan in numbered steps",
  "Explain expense ratios with a simple example",
  "Help me decide between saving and investing",
];

function PromptArrow() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M7 4.5 12.5 10 7 15.5" />
    </svg>
  );
}
