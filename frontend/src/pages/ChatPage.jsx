import { useEffect, useState } from "react";
import { usePersistedState } from "../hooks/usePersistedState.js";
import { useApe } from "../hooks/useApe.js";
import { api } from "../api.js";
import Sidebar from "../components/Sidebar.jsx";
import MessageList from "../components/MessageList.jsx";
import Composer from "../components/Composer.jsx";
import StatusDot from "../components/StatusDot.jsx";
import Toast from "../components/Toast.jsx";
import "../styles/chat.css";

export default function ChatPage() {
  const ape = useApe();
  const [showMeta, setShowMeta] = usePersistedState("ape.show_meta", true);
  const [toast, setToast] = useState({ msg: null, kind: "" });

  useEffect(() => { ape.checkHealth(); }, []);

  useEffect(() => {
    if (ape.error) setToast({ msg: ape.error, kind: "error" });
  }, [ape.error]);

  async function handleFeedback(responseId, signal) {
    const result = await ape.sendFeedback(responseId, signal);
    if (!result) {
      setToast({ msg: "Feedback failed", kind: "error" });
      return;
    }
    if (result.status === "applied" || result.status === "applied_no_format_update") {
      const r = result.normalized_reward;
      setToast({
        msg: `${prettySignal(signal)} ${r != null ? `(${r > 0 ? "+" : ""}${r})` : ""}`,
        kind: "ok",
      });
    } else if (result.reason === "already_finalized") {
      setToast({ msg: "Already rated this response", kind: "error" });
    } else {
      setToast({ msg: `Feedback skipped: ${result.reason || result.status}`, kind: "error" });
    }
  }

  async function handleClearChat() {
    if (!window.confirm(`Clear ALL history for "${ape.userId}"? Bandit learning is preserved on the server.`)) return;
    await ape.clearChat();
    setToast({ msg: "History cleared", kind: "ok" });
  }

  async function handleClearDb() {
    if (!window.confirm("Clear ALL database? Wipes everything for every user. This cannot be undone.")) return;
    try {
      await api.clearAll();
      ape.newSession();
      setToast({ msg: "Database cleared", kind: "ok" });
    } catch (err) {
      setToast({ msg: "Clear failed: " + err.message, kind: "error" });
    }
  }

  // Compute the active session's title from its first user message
  const activeSession = ape.sessions.find((s) => s.session_id === ape.sessionId);
  const headerTitle = activeSession
    ? truncate(activeSession.first_user_message || "New chat", 60)
    : "New chat";

  return (
    <div className="app">
      <Sidebar
        userId={ape.userId}
        onUserIdChange={ape.setUserId}
        sessionId={ape.sessionId}
        sessions={ape.sessions}
        onSwitchSession={ape.switchSession}
        onDeleteSession={ape.deleteSession}
        onClearChat={handleClearChat}
        onClearDb={handleClearDb}
        onNewSession={ape.newSession}
      />

      <main className="chat">
        <header className="chat-header">
          <div>
            <h2>{headerTitle}</h2>
            <span className="muted">claude-haiku-4-5 · finance</span>
          </div>
          <StatusDot ok={ape.statusOk} />
        </header>

        <MessageList
          messages={ape.messages}
          showMeta={showMeta}
          onFeedback={handleFeedback}
        />

        <Composer onSend={ape.sendTurn} disabled={ape.sending} sessionId={ape.sessionId} />
      </main>

      <Toast
        message={toast.msg}
        kind={toast.kind}
        onClose={() => setToast({ msg: null, kind: "" })}
      />
    </div>
  );
}

function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n).trimEnd() + "…" : s;
}

function prettySignal(s) {
  return {
    thumbs_up: "Thumbs up",
    thumbs_down: "Thumbs down",
    copy_save: "Copied",
    regenerate_click: "Regenerated",
  }[s] || s;
}
