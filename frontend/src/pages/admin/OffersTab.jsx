import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

/**
 * OffersTab — full CRUD for outreach actions.
 *
 * "Outreach" in this product means any next-best-action surfaced to the
 * business based on a user's interest signals — could be a consultation,
 * a follow-up call, an educational email, etc. The underlying DB
 * entity_type is still `offer_policy` (legacy name) but the UI labels say
 * "outreach" everywhere.
 *
 * Each outreach is keyed by topic (entity_id). The form supports:
 *   - topic                       text  (entity_id, locked when editing)
 *   - outreach_type               text  (stored as offer_type in JSON)
 *   - description                 text
 *   - min_interest_score          0..1 eligibility gate
 *   - weight_frequency / recency / engagement / followup
 *                                 optional per-outreach scoring weights
 *
 * The four weights override the global defaults (40/25/25/10). They can be
 * entered as fractions OR as raw importance — the recommender normalizes
 * before applying. Blank fields fall back to the global default.
 */

// Global defaults from ape/analytics/compute.py — shown as placeholder
// text so the admin sees what they're overriding.
const DEFAULT_WEIGHTS = {
  frequency:  0.40,
  recency:    0.25,
  engagement: 0.25,
  followup:   0.10,
};

const WEIGHT_KEYS = ["frequency", "recency", "engagement", "followup"];
const WEIGHT_LABEL = {
  frequency:  "Frequency",
  recency:    "Recency",
  engagement: "Engagement",
  followup:   "Followup depth",
};
const WEIGHT_HINT = {
  frequency:  "How often this is their top topic",
  recency:    "How recently they touched it",
  engagement: "Avg reward on the topic",
  followup:   "Recent-week vs 30-day ratio",
};

export default function OffersTab({ notify }) {
  const [rows, setRows]     = useState([]);
  const [topic, setTopic]   = useState("");
  const [offerType, setOT]  = useState("");
  const [desc, setDesc]     = useState("");
  const [minScore, setMin]  = useState("0.7");
  const [domain, setDom]    = useState("finance");
  const [weights, setWeights] = useState({ frequency: "", recency: "", engagement: "", followup: "" });
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]     = useState(false);

  async function refresh() {
    try { setRows(await api.listOffers()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }

  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setTopic(""); setOT(""); setDesc("");
    setMin("0.7"); setDom("finance");
    setWeights({ frequency: "", recency: "", engagement: "", followup: "" });
    setEditing(false);
  }

  function loadIntoForm(row) {
    setTopic(row.entity_id || row.topic || "");
    setOT(row.offer_type || "");
    setDesc(row.description || "");
    setMin(String(row.min_interest_score ?? 0.7));
    setDom(row.domain || "finance");
    setWeights({
      frequency:  row.weight_frequency  != null ? String(row.weight_frequency)  : "",
      recency:    row.weight_recency    != null ? String(row.weight_recency)    : "",
      engagement: row.weight_engagement != null ? String(row.weight_engagement) : "",
      followup:   row.weight_followup   != null ? String(row.weight_followup)   : "",
    });
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Live normalization preview — show the admin what the effective weights
  // will be after the recommender normalizes whatever they entered.
  const normalized = useMemo(() => {
    const raw = {};
    let anyEntered = false;
    for (const k of WEIGHT_KEYS) {
      const v = weights[k];
      if (v !== "" && v !== null && !Number.isNaN(parseFloat(v))) {
        raw[k] = Math.max(0, parseFloat(v));
        anyEntered = true;
      } else {
        raw[k] = DEFAULT_WEIGHTS[k];   // blank → default
      }
    }
    const total = WEIGHT_KEYS.reduce((a, k) => a + raw[k], 0);
    if (total <= 0) return null;
    const out = {};
    for (const k of WEIGHT_KEYS) out[k] = raw[k] / total;
    return { ...out, total, anyEntered };
  }, [weights]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!topic.trim() || !offerType.trim()) return;
    setBusy(true);
    try {
      const payload = {
        topic:                    topic.trim(),
        offer_type:               offerType.trim(),
        description:              desc.trim(),
        min_interest_score:       parseFloat(minScore) || 0.7,
        domain:                   domain.trim() || "finance",
      };
      // Only send weights that the admin actually entered — blanks stay blank
      // (which the backend treats as "use global default")
      for (const k of WEIGHT_KEYS) {
        const v = weights[k];
        if (v !== "" && !Number.isNaN(parseFloat(v))) {
          payload[`weight_${k}`] = parseFloat(v);
        }
      }
      await api.upsertOffer(payload);
      notify(`Outreach for "${topic}" ${editing ? "updated" : "created"}`);
      resetForm();
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(row) {
    try {
      await api.deleteOffer(row.entity_id || row.topic);
      notify(`Outreach for "${row.entity_id}" deleted`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing outreach: ${topic}` : "Add or update outreach action"}
        </h2>
        <p className="admin-section-sub">
          An outreach action fires when the user's <code>interest_score</code> on the topic
          is ≥ <code>min_interest_score</code>. The score is a weighted blend of
          frequency, recency, engagement, and followup depth — adjust the weights
          per-action if this outreach should care more about, say, recent activity
          than total volume. Leave weights blank to use the global defaults
          (40/25/25/10).
        </p>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Topic
              <input
                type="text"
                placeholder="e.g. retirement_accounts"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={editing}
                required
              />
            </label>
            <label className="grow">
              Outreach type
              <input
                type="text"
                placeholder="e.g. retirement_planning_consultation, follow_up_email"
                value={offerType}
                onChange={(e) => setOT(e.target.value)}
                required
              />
            </label>
            <label>
              Domain
              <input value={domain} onChange={(e) => setDom(e.target.value)} />
            </label>
          </div>
          <div className="form-row">
            <label className="grow">
              Description
              <input
                type="text"
                placeholder="Schedule a 30-min planning call"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
              />
            </label>
            <label>
              Min interest score
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={minScore}
                onChange={(e) => setMin(e.target.value)}
              />
            </label>
          </div>

          {/* ----- Weights section ----- */}
          <div className="weights-section">
            <div className="weights-head">
              <strong>Scoring weights</strong>
              <span className="weights-sub">
                Blank = use global default. Enter fractions (0.4) or relative importance (4) —
                we normalize on save.
              </span>
            </div>
            <div className="form-row weights-row">
              {WEIGHT_KEYS.map((k) => (
                <label key={k}>
                  {WEIGHT_LABEL[k]}
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    placeholder={String(DEFAULT_WEIGHTS[k])}
                    value={weights[k]}
                    onChange={(e) => setWeights({ ...weights, [k]: e.target.value })}
                    title={WEIGHT_HINT[k]}
                  />
                  <span className="weight-hint">{WEIGHT_HINT[k]}</span>
                </label>
              ))}
            </div>
            {normalized && (
              <div className="weights-preview">
                <span className="weights-preview-label">Effective:</span>
                {WEIGHT_KEYS.map((k) => (
                  <span key={k} className="weights-preview-chip">
                    {WEIGHT_LABEL[k]} <strong>{Math.round(normalized[k] * 100)}%</strong>
                  </span>
                ))}
                {!normalized.anyEntered && (
                  <span className="weights-preview-default">(global default)</span>
                )}
              </div>
            )}
          </div>

          <div className="form-row form-actions">
            <button type="submit" className="btn-primary" disabled={busy || !topic.trim() || !offerType.trim()}>
              {busy ? "Saving…" : (editing ? "Update outreach" : "Create outreach")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>
                Cancel edit
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Active outreach actions ({rows.length})</h2>
        <AdminTable
          columns={[
            { key: "entity_id",    label: "Topic",     width: "180px",
              render: (r) => <span className="topic-chip">{r.entity_id}</span> },
            { key: "offer_type",   label: "Outreach type",
              render: (r) => <strong>{r.offer_type}</strong> },
            { key: "min_interest_score", label: "Min score", width: "90px",
              render: (r) => <span className="num">{Number(r.min_interest_score).toFixed(2)}</span> },
            { key: "weights", label: "Weights (f/r/e/u)", width: "180px",
              render: (r) => <WeightsCell row={r} /> },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill
                  entityType="offer_policy"
                  entityId={r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
          ]}
          rows={rows.map((r, i) => ({ ...r, _key: i }))}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete outreach action for topic "${row.entity_id}"?`}
          emptyText="No outreach actions yet. Add one above to recommend follow-ups to interested users."
        />
      </div>
    </div>
  );
}

/** Compact display: F/R/E/U weights as percentages, or "default" if all blank. */
function WeightsCell({ row }) {
  const have = ["weight_frequency", "weight_recency", "weight_engagement", "weight_followup"]
    .some((k) => row[k] != null);
  if (!have) {
    return <span className="muted">global default</span>;
  }
  const raw = {
    f: row.weight_frequency  ?? DEFAULT_WEIGHTS.frequency,
    r: row.weight_recency    ?? DEFAULT_WEIGHTS.recency,
    e: row.weight_engagement ?? DEFAULT_WEIGHTS.engagement,
    u: row.weight_followup   ?? DEFAULT_WEIGHTS.followup,
  };
  const total = raw.f + raw.r + raw.e + raw.u || 1;
  return (
    <code className="weights-cell">
      {Math.round(100 * raw.f / total)}/{Math.round(100 * raw.r / total)}/{Math.round(100 * raw.e / total)}/{Math.round(100 * raw.u / total)}
    </code>
  );
}
