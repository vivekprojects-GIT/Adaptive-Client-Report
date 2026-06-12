import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { usePersistedState } from "./usePersistedState.js";

/**
 * Strip the synthesizer's JSON wrapper from a streaming buffer so we can
 * show clean text while tokens arrive.
 *
 * The synthesizer emits:
 *   {"rendered_format": "...", "response": "...the actual text..."}
 *
 * During streaming the JSON may be incomplete. We use these heuristics:
 *   1. If the buffer is well-formed JSON with a `response` field → return it
 *   2. If we can see `"response":` followed by an opening quote, extract
 *      from there to the buffer end and unescape it
 *   3. If the buffer doesn't look like JSON yet (e.g. starts with ```), strip
 *      code-fence prefix
 *   4. Otherwise return the raw buffer (worst case: user sees a flash of
 *      `{"rendered_format": ...` for a few hundred ms — `done` cleans it up)
 */
function extractDisplayText(buf) {
  if (!buf) return "";
  let s = buf.trimStart();
  // Strip code fences
  if (s.startsWith("```")) {
    s = s.replace(/^```[a-zA-Z]*\n?/, "");
    if (s.endsWith("```")) s = s.slice(0, -3);
  }
  // Fast path: complete JSON
  try {
    const parsed = JSON.parse(s);
    if (parsed && typeof parsed.response === "string") return parsed.response;
  } catch { /* not yet complete — fall through */ }

  // Find `"response":` and pull everything after the opening quote
  const m = s.match(/"response"\s*:\s*"/);
  if (m) {
    const start = m.index + m[0].length;
    let out = "";
    let i = start;
    while (i < s.length) {
      const ch = s[i];
      if (ch === "\\" && i + 1 < s.length) {
        const next = s[i + 1];
        if (next === "n") out += "\n";
        else if (next === "t") out += "\t";
        else if (next === '"') out += '"';
        else if (next === "\\") out += "\\";
        else out += next;
        i += 2;
      } else if (ch === '"') {
        // Reached the closing quote — done
        return out;
      } else {
        out += ch;
        i += 1;
      }
    }
    return out;   // still streaming, no closing quote yet
  }

  // No "response" field visible yet — show the raw text (will get replaced)
  return s;
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
            streamBuf += payload.text;
            updateBubble(extractDisplayText(streamBuf), false);
          } else if (payload.event === "done") {
            finalResult = payload;
            updateBubble(payload.answer || extractDisplayText(streamBuf), true);
          } else if (payload.event === "error") {
            throw new Error(payload.message || "stream error");
          }
        }
      }

      if (!finalResult) throw new Error("stream ended without 'done' event");

      if (!mountedRef.current) return;        // navigated away — don't touch state
      setPendingMessages([]);
      const rows = await api.loadSessionMessages(finalResult.session_id, userId);
      if (!mountedRef.current) return;
      setMessages(rows || []);
      refreshSessions();
    } catch (err) {
      // AbortError is expected when the user navigates away mid-stream.
      if (err.name === "AbortError" || !mountedRef.current) return;
      console.error("[APE] turn failed", err);
      setError(err.message);
      setPendingMessages([]);
    } finally {
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
  // Fire regenerate_click on the response being regenerated, then re-issue
  // the user's most recent query so the bandit picks a fresh strategy.
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
    // Fire the negative signal on the old response
    await sendFeedback(responseId, "regenerate_click");
    // Re-issue the same query (gets a new bandit selection)
    if (userQuery) {
      await sendTurn(userQuery);
    }
  }, [messages, sendFeedback, sendTurn]);

  // ---- Session abandon (best-effort beacon on tab close) ------------------
  // Fires session_abandon for the most recent PENDING response when the
  // user closes the tab / navigates away. Uses navigator.sendBeacon so the
  // request survives unload. Best-effort only — not all browsers fire
  // beforeunload reliably (especially mobile).
  useEffect(() => {
    function onUnload() {
      // Find the most recent assistant message with a response_id and no
      // applied signal yet — that's the row that might still be PENDING.
      const lastAssistant = [...messages].reverse().find(
        (m) => m.role === "assistant" && m.response_id && !m.applied_signal
      );
      if (!lastAssistant || !userId) return;
      const payload = JSON.stringify({
        user_id:     userId,
        response_id: lastAssistant.response_id,
        signal:      "session_abandon",
      });
      try {
        navigator.sendBeacon?.(
          "/feedback",
          new Blob([payload], { type: "application/json" })
        );
      } catch { /* nothing we can do — page is unloading */ }
    }
    window.addEventListener("beforeunload", onUnload);
    return () => window.removeEventListener("beforeunload", onUnload);
  }, [messages, userId]);

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
