/**
 * API client — thin wrapper around fetch() for FastAPI endpoints.
 * All paths are relative; Vite proxies them to :7860 in dev,
 * and FastAPI serves them at the same origin in production.
 */

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const opts = { method, headers };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const resp = await fetch(path, opts);
  if (!resp.ok) {
    let detail = await resp.text();
    try { detail = JSON.parse(detail).detail || detail; } catch {}
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

export const api = {
  // Core flow
  health:               ()                                 => request("GET",    "/health"),
  postTurn:             (payload)                          => request("POST",   "/turn", payload),
  postFeedback:         (payload)                          => request("POST",   "/feedback", payload),

  // Conversation history (Mongo-backed)
  loadSessionMessages:  (sessionId, userId, limit = 200)   => request("GET",    `/sessions/${encodeURIComponent(sessionId)}/messages?user_id=${encodeURIComponent(userId)}&limit=${limit}`),
  listUserSessions:     (userId, limit = 20)               => request("GET",    `/users/${encodeURIComponent(userId)}/sessions?limit=${limit}`),
  getLatestSession:     (userId)                           => request("GET",    `/users/${encodeURIComponent(userId)}/latest-session`),
  deleteSession:        (sessionId, userId)                => request("DELETE", `/sessions/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(userId)}`),

  // Config — read
  listIntents:          ()                                 => request("GET",    "/config/intents"),
  listStrategies:       ()                                 => request("GET",    "/config/strategies"),
  listPolicies:         ()                                 => request("GET",    "/config/policies"),
  listSignalRules:      ()                                 => request("GET",    "/config/signal-rules"),
  listRewardScale:      ()                                 => request("GET",    "/config/reward-scale"),
  listInstructions:     (strategyId = "", status = "")     => request("GET",    `/config/instructions${strategyId || status ? `?${[strategyId && `strategy_id=${encodeURIComponent(strategyId)}`, status && `status=${encodeURIComponent(status)}`].filter(Boolean).join("&")}` : ""}`),

  // Config — write
  upsertIntent:         (payload)                          => request("POST",   "/config/intents", payload),
  upsertStrategy:       (payload)                          => request("POST",   "/config/strategies", payload),
  upsertSignalRule:     (payload)                          => request("POST",   "/config/signal-rules", payload),
  upsertRewardValue:    (payload)                          => request("POST",   "/config/reward-scale", payload),
  upsertPolicy:         (payload)                          => request("POST",   "/config/policies", payload),
  publishInstruction:   (payload)                          => request("POST",   "/config/instructions", payload),
  activateInstruction:  (strategyId, version, changedBy="admin_user") =>
                          request("POST", `/config/instructions/activate?strategy_id=${encodeURIComponent(strategyId)}&version=${encodeURIComponent(version)}&changed_by=${encodeURIComponent(changedBy)}`),

  // Config — flip ACTIVE / INACTIVE / DRAFT on any config doc
  setConfigStatus:      (entityType, entityId, status, version) =>
                          request("POST", "/config/status", {
                            entity_type: entityType,
                            entity_id:   entityId,
                            status,
                            ...(version ? { version } : {}),
                          }),

  // Config — delete (every entity type)
  deleteIntent:         (intentId)                         => request("DELETE", `/config/intents/${encodeURIComponent(intentId)}`),
  deleteStrategy:       (strategyId)                       => request("DELETE", `/config/strategies/${encodeURIComponent(strategyId)}`),
  deleteSignalRule:     (signalName)                       => request("DELETE", `/config/signal-rules/${encodeURIComponent(signalName)}`),
  deleteRewardValue:    (category)                         => request("DELETE", `/config/reward-scale/${encodeURIComponent(category)}`),
  deletePolicy:         (intent, topic, strategyId)        =>
                          request("DELETE", `/config/policies?intent=${encodeURIComponent(intent)}&topic=${encodeURIComponent(topic)}&strategy_id=${encodeURIComponent(strategyId)}`),
  deleteInstruction:    (strategyId, version)              =>
                          request("DELETE", `/config/instructions/${encodeURIComponent(strategyId)}/${encodeURIComponent(version)}`),

  // Offer policies — full CRUD
  listOffers:           ()                                 => request("GET",    "/config/offers"),
  upsertOffer:          (payload)                          => request("POST",   "/config/offers", payload),
  deleteOffer:          (topic)                            => request("DELETE", `/config/offers/${encodeURIComponent(topic)}`),

  // Admin / ops
  clearUser:            (userId)                           => request("DELETE", `/admin/clear-user/${encodeURIComponent(userId)}`),
  clearAll:             ()                                 => request("DELETE", "/admin/clear-all"),
  rebuildBandit:        ()                                 => request("POST",   "/admin/rebuild-bandit"),
  dbSnapshot:           (userId, limit = 30)               => request("GET",    `/admin/db-snapshot?user_id=${encodeURIComponent(userId || "")}&limit=${limit}`),
  banditState:          (userId = "", onlyPulled = true)   => request("GET",    `/admin/bandit-state?only_pulled=${onlyPulled}${userId ? `&user_id=${encodeURIComponent(userId)}` : ""}`),
  resetBanditCell:      (userId, domain, intent, topic, strategy = "") =>
                          request("DELETE", `/admin/bandit-state/cell?user_id=${encodeURIComponent(userId)}&domain=${encodeURIComponent(domain)}&intent=${encodeURIComponent(intent)}&topic=${encodeURIComponent(topic)}${strategy ? `&strategy=${encodeURIComponent(strategy)}` : ""}`),
  listAudit:            (date = "", limit = 100)           => request("GET",    `/admin/audit?${date ? `date=${date}&` : ""}limit=${limit}`),
  seed:                 ()                                 => request("POST",   "/admin/seed"),

  // Analytics — business layer
  recomputeAnalytics:   (days = 14)                        => request("POST",   `/analytics/recompute?days=${days}`),
  userInterests:        (userId, limit = 10, refresh = false) =>
                          request("GET", `/analytics/user-interests?user_id=${encodeURIComponent(userId)}&limit=${limit}&refresh=${refresh}`),
  topicUsers:           (topic, limit = 20, minScore = 0.5) =>
                          request("GET", `/analytics/topic-users?topic=${encodeURIComponent(topic)}&limit=${limit}&min_score=${minScore}`),
  trends:               (days = 7, limit = 30, refresh = false) =>
                          request("GET", `/analytics/trends?days=${days}&limit=${limit}&refresh=${refresh}`),
  topicTimeseries:      (topic, days = 30) =>
                          request("GET", `/analytics/topic-timeseries?topic=${encodeURIComponent(topic)}&days=${days}`),
  platformTimeseries:   (days = 30) =>
                          request("GET", `/analytics/platform-timeseries?days=${days}`),
  topicsTimeseries:     (days = 30, topN = 5) =>
                          request("GET", `/analytics/topics-timeseries?days=${days}&top_n=${topN}`),
  userTimeseries:       (userId, days = 30) =>
                          request("GET", `/analytics/user-timeseries?user_id=${encodeURIComponent(userId)}&days=${days}`),
  userOffers:           (userId)                            =>
                          request("GET", `/analytics/offers/${encodeURIComponent(userId)}`),
  // Pass userId="" or null to get the GLOBAL aggregate view across all users.
  cognitiveFacets:      (userId = "", minInteractions = 1, domain = "") =>
                          request("GET", `/analytics/cognitive-facets?min_interactions=${minInteractions}${userId ? `&user_id=${encodeURIComponent(userId)}` : ""}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  activeUsers:          (days = 1, minInterest = 0, limit = 100, domain = "") =>
                          request("GET", `/analytics/active-users?days=${days}&min_interest=${minInterest}&limit=${limit}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  userProfile:          (userId, domain = "") =>
                          request("GET", `/analytics/user-profile?user_id=${encodeURIComponent(userId)}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  unmappedIntents:      (days = 30, limit = 50, domain = "") =>
                          request("GET", `/analytics/unmapped-intents?days=${days}&limit=${limit}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  platformOverview:     (days = 30, topN = 8, domain = "") =>
                          request("GET", `/analytics/platform-overview?days=${days}&top_n=${topN}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  strategyPerformance:  (userId = "", minPulls = 3, domain = "") =>
                          request("GET", `/analytics/strategy-performance?min_pulls=${minPulls}${userId ? `&user_id=${encodeURIComponent(userId)}` : ""}${domain ? `&domain=${encodeURIComponent(domain)}` : ""}`),
  instructionQuality:   (days = 14, minTurns = 5, sampleLimit = 5) =>
                          request("GET", `/analytics/instruction-quality?days=${days}&min_turns=${minTurns}&sample_limit=${sampleLimit}`),
  customerHealth:       (days = 30, cohortWeeks = 4) =>
                          request("GET", `/analytics/customer-health?days=${days}&cohort_weeks=${cohortWeeks}`),
  ragQuality:           (days = 14, minTurns = 5, sampleLimit = 5) =>
                          request("GET", `/analytics/rag-quality?days=${days}&min_turns=${minTurns}&sample_limit=${sampleLimit}`),
};
