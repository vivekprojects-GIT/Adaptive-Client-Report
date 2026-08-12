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

  // Config — read
  listReportTypes:      ()                                 => request("GET",    "/config/report-types"),
  listClients:          (q)                                => request("GET",    "/clients" + (q ? "?q=" + encodeURIComponent(q) : "")),
  importClients:        (payload)                          => request("POST",   "/clients/import", payload),
  d1Decision:           (clientId, reportType)             => request("GET",    "/ape/d1-decision?client_id=" + encodeURIComponent(clientId) + "&report_type=" + encodeURIComponent(reportType)),
  generateOneReport:    (payload)                          => request("POST",   "/reports/generate-one", payload),
  reportClientLink:     (reportId)                         => request("GET",    `/reports/${encodeURIComponent(reportId)}/link`),
  clientInsight:        (clientId)                         => request("GET",    `/clients/${encodeURIComponent(clientId)}/insight`),
  setSkillNote:         (clientId, note)                   => request("POST",   `/clients/${encodeURIComponent(clientId)}/skill-note`, { note }),
  d1State:              ()                                 => request("GET",    "/ape/d1-state"),
  d2State:              ()                                 => request("GET",    "/ape/d2-state"),
  sendReport:           (reportId)                         => request("POST",   "/reports/" + encodeURIComponent(reportId) + "/send", {}),
  listGeneratedReports: ()                                 => request("GET",    "/reports/generated"),
  generateReports:      (payload)                          => request("POST",   "/reports/generate", payload),
  listTemplates:        (rt)                               => request("GET",    "/config/templates" + (rt ? `?report_type=${encodeURIComponent(rt)}` : "")),

  // Config — write
  upsertReportType:     (payload)                          => request("POST",   "/config/report-types", payload),
  upsertTemplate:       (payload)                          => request("POST",   "/config/templates", payload),
  previewTemplate:      (payload)                          => request("POST",   "/config/templates/preview", payload),
  deleteTemplate:       (templateId)                       => request("DELETE", `/config/templates/${encodeURIComponent(templateId)}`),
  getSelectionConfig:   ()                                 => request("GET",    "/config/selection"),
  updateSelectionConfig: (payload)                         => request("POST",   "/config/selection", payload),

  // Config — flip ACTIVE / INACTIVE / DRAFT on any config doc
  setConfigStatus:      (entityType, entityId, status, version) =>
                          request("POST", "/config/status", {
                            entity_type: entityType,
                            entity_id:   entityId,
                            status,
                            ...(version ? { version } : {}),
                          }),

  // Config — delete (every entity type)

  // Admin / ops
  listAudit:            (date = "", limit = 100)           => request("GET",    `/admin/audit?${date ? `date=${date}&` : ""}limit=${limit}`),
};
