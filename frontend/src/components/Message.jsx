import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { splitStreaming } from "../utils/streamRender.js";

// Full CommonMark + GFM (tables, strikethrough, task lists, autolinks) via
// react-markdown — replaces the old hand-rolled regex renderer, so any
// standard markdown the model emits renders correctly without per-syntax
// patches. Links open in a new tab.
const MD_PLUGINS = [remarkGfm];
const MD_COMPONENTS = {
  a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" />,
};

function Markdown({ children }) {
  return (
    <ReactMarkdown remarkPlugins={MD_PLUGINS} components={MD_COMPONENTS}>
      {children}
    </ReactMarkdown>
  );
}

/**
 * One message — Claude Desktop style.
 *
 *   user message:        right-aligned, subtle warm-gray bubble
 *   assistant message:   full-width prose, no bubble (just clean markdown)
 *
 * Assistant messages carry response_id + rendered_format. The feedback row
 * (👍/👎) appears only on the most recent assistant message and routes to
 * Path B with that exact response_id.
 */
export default function Message({ message, isLastAssistant, showMeta, onFeedback, onRegenerate, ratedSignal }) {
  const isUser = message.role === "user";
  const isPlaceholder = !!message._placeholder;
  const thumbsLocked = !!ratedSignal;

  // User messages: plain text in the bubble (React escapes automatically).
  // Assistant messages: full markdown via react-markdown.
  //
  // While streaming we render LINE BY LINE: every complete line is safe to
  // markdown-render, while the partially-typed last line is held back and
  // sanitized (see splitStreaming). That keeps raw syntax off the screen
  // without freezing a whole table as plain text until it finishes.
  return (
    <div className={`msg ${isUser ? "user" : "assistant"}`}>
      <div className="msg-content">
        {isUser
          ? message.content
          : isPlaceholder
            ? <StreamingContent content={message.content} />
            : <Markdown>{message.content}</Markdown>}
      </div>

      {!isUser && showMeta && message.meta && (
        <div className="meta-strip">{renderMetaChips(message)}</div>
      )}

      {!isUser && isLastAssistant && !isPlaceholder && message.response_id && (
        <div className="feedback-row">
          <button
            className={`fb-btn${ratedSignal === "thumbs_up" ? " active" : ""}`}
            onClick={() => onFeedback(message.response_id, "thumbs_up")}
            disabled={thumbsLocked}
            title={thumbsLocked ? "Already rated" : "Good response"}
            aria-label="Thumbs up"
            aria-pressed={ratedSignal === "thumbs_up"}
          >
            <ThumbUpIcon />
          </button>
          <button
            className={`fb-btn${ratedSignal === "thumbs_down" ? " active" : ""}`}
            onClick={() => onFeedback(message.response_id, "thumbs_down")}
            disabled={thumbsLocked}
            title={thumbsLocked ? "Already rated" : "Bad response"}
            aria-label="Thumbs down"
            aria-pressed={ratedSignal === "thumbs_down"}
          >
            <ThumbDownIcon />
          </button>
          <button
            className="fb-btn"
            onClick={() => navigator.clipboard?.writeText(message.content || "")}
            title="Copy response"
            aria-label="Copy"
          >
            <CopyIcon />
          </button>
          <button
            className="fb-btn"
            onClick={() => onRegenerate?.(message.response_id)}
            title="Regenerate this response"
            aria-label="Regenerate"
          >
            <RegenIcon />
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * The in-flight assistant bubble. splitStreaming decides which prefix of the
 * buffer is safe to parse (buffering half-open tables/fences) and sanitizes
 * the still-typing line; this component just renders those two pieces.
 */
function StreamingContent({ content }) {
  const { thinking, committed, tail } = splitStreaming(content);
  if (thinking) {
    return (
      <div className="placeholder-text">
        <span className="spinner" />Thinking…
      </div>
    );
  }
  return (
    <>
      {committed ? <Markdown>{committed}</Markdown> : null}
      {tail ? <div className="stream-tail">{tail}</div> : null}
    </>
  );
}

// ---------- Chip rendering ----------

function renderMetaChips(msg) {
  const meta = msg.meta || {};
  const chips = [];
  // Topic is disabled in the bandit key (collapsed to "_all") — don't show it.
  if (meta.topic && meta.topic !== "_all") chips.push(chip("topic: " + meta.topic));
  if (meta.intent)            chips.push(chip("intent: "   + meta.intent));
  if (meta.selected_strategy) chips.push(chip("strategy: " + meta.selected_strategy));
  if (msg.rendered_format)    chips.push(chip("rendered: " + msg.rendered_format));
  // Selection score of the chosen strategy — computed LIVE server-side from
  // the current cell state (matches the Bandit State tab), not a cached
  // snapshot. Round-robin cold-start picks have no meaningful score.
  // `meta.ucb_at_selection` is the historical fallback for older messages.
  const selMethod = msg.selection_method || meta.selection_method;
  const liveScore = msg.live_selection_score != null
    ? msg.live_selection_score
    : meta.ucb_at_selection;
  if (selMethod === "round_robin") {
    chips.push(chip("pick: round-robin"));
  } else if (liveScore != null) {
    chips.push(chip(`selection score: ${Number(liveScore).toFixed(2)}`));
  }
  // Applied reward verdict — joined from ape_turn_record by the messages
  // API. Shows BOTH reward axes of the two-axis model:
  //   format  — what the bandit consumed (explicit ±2 / inferred ±1)
  //   content — recorded evidence about the answer's substance
  if (msg.reward_status === "APPLIED") {
    const hasFormat  = msg.normalized_reward != null;
    const hasContent = msg.content_reward != null;
    if (msg.applied_signal && msg.applied_signal !== "no_signal") {
      chips.push(chip(`signal: ${msg.applied_signal}`));
    }
    if (hasContent) {
      const c = Number(msg.content_reward);
      chips.push(chip(
        `content: ${c > 0 ? "+" : ""}${c} (${tierLabel(msg.content_category)})`,
        c > 0 ? "pos" : "neg",
      ));
    }
    if (hasFormat) {
      const f = Number(msg.normalized_reward);
      chips.push(chip(
        `format: ${f > 0 ? "+" : ""}${f} (${tierLabel(msg.reward_category)})`,
        f > 0 ? "pos" : "neg",
      ));
    }
    if (!hasFormat && !hasContent && msg.applied_signal && msg.applied_signal !== "no_signal") {
      chips.push(chip("no reward (axis not recorded)"));
    }
  } else if (msg.reward_status === "PENDING" && msg.response_id) {
    chips.push(chip("reward: pending"));
  }
  return <>{chips}</>;
}

function chip(text, klass = "") {
  return <span key={text} className={`chip ${klass}`}>{text}</span>;
}

// "explicit_positive" -> "explicit", "inferred_negative" -> "inferred"
function tierLabel(category) {
  if (!category) return "?";
  return String(category).split("_")[0];
}

// ---------- Icons ----------

function ThumbUpIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H7a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L15 2"/>
    </svg>
  );
}
function ThumbDownIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 14V2M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H17a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L9 22"/>
    </svg>
  );
}
function CopyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
    </svg>
  );
}
function RegenIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 3-6.7"/>
      <path d="M3 4v5h5"/>
    </svg>
  );
}
