import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { usePersistedState } from "./usePersistedState.js";

/**
 * Display text for the streaming buffer.
 *
 * The synthesizer now emits PLAIN MARKDOWN (no JSON envelope), so each chunk is
 * directly renderable and we can markdown-render progressively as it arrives —
 * exactly how a chat assistant streams. No parsing/unescaping needed.
 *
 * The only handling left is a legacy guard: if an older model still emits the
 * `{"rendered_format": ..., "response": "..."}` wrapper, scrape the `response`
 * field so the user never sees raw JSON. Normal markdown passes through
 * untouched.
 */
function extractDisplayText(buf) {
  if (!buf) return "";
  const s = buf.trimStart();

  // Plain markdown (the normal path) — show it as-is.
  if (!s.startsWith("{")) return buf;

  // --- legacy JSON-envelope fallback ---
  try {
    const parsed = JSON.parse(s);
    if (parsed && typeof parsed.response === "string") return parsed.response;
  } catch { /* incomplete JSON — fall through to partial scrape */ }

  const m = s.match(/"response"\s*:\s*"/);
  if (m) {
    let out = "";
    for (let i = m.index + m[0].length; i < s.length; i++) {
      const ch = s[i];
      if (ch === "\\" && i + 1 < s.length) {
        const next = s[i + 1];
        out += next === "n" ? "\n" : next === "t" ? "\t" : next;
        i += 1;
      } else if (ch === '"') {
        return out;
      } else {
        out += ch;
      }
    }
    return out;
  }
  return buf;
}

/**
 * Central APE chat state.
 *
 * Conversation history is server-authoritative — stored in MongoDB
 * (ape_messages collection). The client reads via /sessions/{id}/messages
 * and writes via /turn. localStorage holds only the active user_id and the
 * current session_id (so a page refresh resumes the same conversation).
 *
 * Returns:
 *   userId, setUserId
 *   sessionId, setSessionId, newSession
 *   sessions          — list of past sessions for the current user
 *   messages          — current session's messages, sorted by ts
 *   sending
 *   statusOk
 *   sendTurn(query)
 *   sendFeedback(responseId, signal)
 *   clearChat()       — wipes server data for this user
 *   deleteSession(id) — wipes one session
 *   refreshHistory()
 *   refreshSessions()
 */
export function useApe() {
  const [userId, setUserId]       = usePersistedState("ape.user_id", "demo_user");
  const [sessionId, setSessionId] = usePersistedState("ape.session_id", null);
  const [sessions, setSessions]   = useState([]);
  const [messages, setMessages]   = useState([]);
  const [pendingMessages, setPendingMessages] = useState([]); // optimistic
  const [sending, setSending]     = useState(false);
  const [statusOk, setStatusOk]   = useState(null);
  const [error, setError]         = useState(null);

  // Lifecycle guards — prevent setState after unmount and abort any
  // in-flight SSE stream when the component goes away (e.g. user navigates
  // from /chat to /analytics mid-stream).
  const mountedRef = useRef(true);
  const abortRef   = useRef(null);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  // ---- Health check ------------------------------------------------------
  const checkHealth = useCallback(async () => {
    try {
      await api.health();
      setStatusOk(true);
    } catch {
      setStatusOk(false);
    }
  }, []);

  // ---- Server-driven history ---------------------------------------------
  const refreshHistory = useCallback(async () => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    try {
      const rows = await api.loadSessionMessages(sessionId, userId);
      setMessages(rows || []);
    } catch (err) {
      console.warn("[APE] loadSessionMessages failed", err);
    }
  }, [sessionId, userId]);

  const refreshSessions = useCallback(async () => {
    try {
      const rows = await api.listUserSessions(userId);
      setSessions(rows || []);
    } catch (err) {
      console.warn("[APE] listUserSessions failed", err);
    }
  }, [userId]);

  // On user change, resume their latest session (or start fresh)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (!sessionId) {
          const { session_id } = await api.getLatestSession(userId);
          if (!cancelled && session_id) setSessionId(session_id);
        }
        if (!cancelled) {
          await refreshSessions();
          await refreshHistory();
        }
      } catch (err) {
        console.warn("[APE] initial load failed", err);
      }
    })();
    return () => { cancelled = true; };
    // Re-run when user_id changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // Refresh history whenever sessionId changes
  useEffect(() => { refreshHistory(); }, [sessionId, refreshHistory]);

  // ---- Send a turn (streaming via SSE) -----------------------------------
  // Streams synthesizer tokens as they arrive. Updates the placeholder
  // assistant bubble in place; on `done` we drop the placeholder and
  // refresh the canonical history from Mongo.
  const sendTurn = useCallback(async (query) => {
    if (!query || !query.trim() || sending) return;
    const trimmed = query.trim();
    setSending(true);
    setError(null);

    const optUserId = "opt_user_" + Date.now();
    const optAsstId = "opt_asst_" + Date.now();

    setPendingMessages([
      { message_id: optUserId, role: "user",      content: trimmed, ts: new Date().toISOString() },
      { message_id: optAsstId, role: "assistant", content: "",      ts: new Date(Date.now() + 1).toISOString(),
        _streaming: true, _placeholder: true },
    ]);

    // ----------------------------------------------------------------
    // streamBuf  = the raw LLM text (may contain JSON wrapper)
    // shown      = the cleaned, display-friendly text we render
    // We try to extract the "response": "..." field from the JSON wrapper
    // on the fly; if the JSON isn't well-formed yet, we just show the raw
    // text (the wrapper noise disappears once `done` arrives).
    // ----------------------------------------------------------------
    let streamBuf = "";
    let finalResult = null;

    // --- render batching -------------------------------------------------
    // Deltas arrive faster than the browser can paint, so we don't re-render
    // per chunk. Instead we coalesce onto the next animation frame: many
    // deltas landing inside one ~16ms frame collapse into a single repaint.
    // (Message.jsx then renders only the COMPLETED markdown blocks, keeping
    // the trailing partial block as plain text, so nothing snaps mid-build.)
    let rafId = null;
    const scheduleRender = () => {
      if (rafId !== null) return;                       // already queued
      rafId = requestAnimationFrame(() => {
        rafId = null;
        updateBubble(extractDisplayText(streamBuf), false);
      });
    };
    const cancelRender = () => {
      if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    };

    const updateBubble = (text, isFinal) => {
      setPendingMessages([
        { message_id: optUserId, role: "user", content: trimmed,
          ts: new Date().toISOString() },
        { message_id: optAsstId, role: "assistant", content: text,
          ts: new Date(Date.now() + 1).toISOString(),
          _streaming: !isFinal, _placeholder: !isFinal },
      ]);
    };

    // Fresh AbortController per turn; abort the previous one if somehow
    // still open, then store this one so unmount can cancel the stream.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch("/turn/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:           userId,
          session_id:        sessionId || undefined,
          query:             trimmed,
          generate_response: true,
        }),
        signal: controller.signal,
      });
      if (!resp.ok || !resp.body) {
        throw new Error(`stream failed: ${resp.status} ${resp.statusText}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done || !mountedRef.current) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE events: separated by blank line ("\n\n")
        const events = buffer.split("\n\n");
        buffer = events.pop();   // keep the trailing incomplete event

        for (const raw of events) {
          const line = raw.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          const payload = JSON.parse(line.slice(6));
          if (payload.event === "metadata") {
            // Adopt session_id immediately so reload works mid-stream
            if (payload.session_id && payload.session_id !== sessionId) {
              setSessionId(payload.session_id);
            }
          } else if (payload.event === "delta") {
            streamBuf += payload.text;      // always accumulate
            scheduleRender();               // repaint at most once per frame
          } else if (payload.event === "done") {
            finalResult = payload;
            cancelRender();                 // drop any queued partial repaint
            updateBubble(payload.answer || extractDisplayText(streamBuf), true);
          } else if (payload.event === "error") {
            throw new Error(payload.message || "stream error");
          }
        }
      }

      if (!finalResult) throw new Error("stream ended without 'done' event");

      if (!mountedRef.current) return;        // navigated away — don't touch state
      // Keep the optimistic bubbles on screen while the canonical history is
      // fetched, then swap atomically. Clearing them BEFORE the fetch made the
      // just-streamed answer vanish for the whole Mongo round-trip (the UI
      // flashed back to the stale conversation) and reappear when rows landed.
      const rows = await api.loadSessionMessages(finalResult.session_id, userId);
      if (!mountedRef.current) return;
      setMessages(rows || []);
      setPendingMessages([]);
      refreshSessions();
    } catch (err) {
      // AbortError is expected when the user navigates away mid-stream.
      if (err.name === "AbortError" || !mountedRef.current) return;
      console.error("[APE] turn failed", err);
      setError(err.message);
      setPendingMessages([]);
    } finally {
      // Drop any frame still queued so it can't repaint after teardown.
      cancelRender();
      if (mountedRef.current) setSending(false);
      // This turn's controller is done; clear it so unmount doesn't abort a
      // controller that's no longer active.
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [sending, userId, sessionId, refreshSessions]);

  // ---- Feedback (Path B) -------------------------------------------------
  const sendFeedback = useCallback(async (responseId, signal) => {
    if (!responseId) {
      console.warn("[APE] sendFeedback called without response_id");
      return null;
    }
    try {
      const result = await api.postFeedback({
        user_id:     userId,
        response_id: responseId,
        signal,
      });
      // Refresh history so the assistant message picks up its applied verdict
      await refreshHistory();
      return result;
    } catch (err) {
      console.error("[APE] feedback failed", err);
      setError(err.message);
      return null;
    }
  }, [userId, refreshHistory]);

  // ---- Regenerate ---------------------------------------------------------
  // Re-issue the user's most recent query so the bandit picks a fresh
  // strategy. (vg signal catalog: regenerate is not a signal — only thumbs
  // and LLM-detected text move rewards.)
  const regenerate = useCallback(async (responseId) => {
    if (!responseId) return null;
    // Find the user message immediately before this assistant response
    const idx = messages.findIndex((m) => m.response_id === responseId);
    let userQuery = null;
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        userQuery = messages[i].content;
        break;
      }
    }
    // Re-issue the same query (gets a new bandit selection)
    if (userQuery) {
      await sendTurn(userQuery);
    }
  }, [messages, sendTurn]);

  // ---- User switching ------------------------------------------------------
  // Changing the user must also drop the old user's sessionId — otherwise the
  // chat keeps pointing at a session the new user can't read (and the
  // latest-session auto-resume for the new user never fires).
  const switchUser = useCallback((id) => {
    const trimmed = (id || "").trim();
    if (!trimmed || trimmed === userId) return;
    setUserId(trimmed);
    setSessionId(null);
    setMessages([]);
    setSessions([]);
  }, [userId, setUserId, setSessionId]);

  // ---- Session controls --------------------------------------------------
  const newSession = useCallback(() => {
    // Drop sessionId; next sendTurn() will trigger the server to mint a new one
    setSessionId(null);
    setMessages([]);
  }, []);

  const switchSession = useCallback((targetSessionId) => {
    setSessionId(targetSessionId);
  }, []);

  const deleteSession = useCallback(async (targetSessionId) => {
    try {
      await api.deleteSession(targetSessionId, userId);
      if (targetSessionId === sessionId) {
        setSessionId(null);
        setMessages([]);
      }
      await refreshSessions();
    } catch (err) {
      console.warn("[APE] deleteSession failed", err);
    }
  }, [userId, sessionId, refreshSessions]);

  const clearChat = useCallback(async () => {
    try {
      await api.clearUser(userId);
    } catch (err) {
      console.warn("[APE] clearUser failed (continuing)", err);
    }
    setSessionId(null);
    setMessages([]);
    setSessions([]);
  }, [userId]);

  return {
    userId, setUserId, switchUser,
    sessionId, switchSession, newSession, deleteSession,
    sessions,
    messages:  pendingMessages.length ? [...messages, ...pendingMessages] : messages,
    sending,
    statusOk,
    error,
    sendTurn,
    sendFeedback,
    regenerate,
    clearChat,
    refreshHistory,
    refreshSessions,
    checkHealth,
  };
}
