import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";

const CATEGORIES = [
  { value: "",                 label: "(none — NOT_RECORDED)" },
  { value: "strong_positive",  label: "strong_positive (+1.0)" },
  { value: "weak_positive",    label: "weak_positive (+0.5)" },
  { value: "weak_negative",    label: "weak_negative (-0.5)" },
  { value: "strong_negative",  label: "strong_negative (-1.0)" },
];

const SOURCE_TYPES = [
  { value: "ui",        label: "UI button (user click)" },
  { value: "llm",       label: "LLM-detected (classifier)" },
  { value: "derived",   label: "Derived (automatic — e.g. session, compliance)" },
  { value: "composite", label: "Composite (multi-signal pattern)" },
  { value: "default",   label: "Default (no_signal)" },
];

const FREQ_OPTIONS = ["common", "moderate", "rare"];
const QUALITY_OPTIONS = ["high", "medium", "low"];

const CONSUMER_OPTIONS = [
  "bandit",
  "instruction_quality",
  "analytics",
  "retention",
  "nps",
  "engagement",
];

/**
 * SignalRulesTab — full CRUD for the signal catalog.
 *
 * Supports all 25 signals (15 atomic + 10 composite) plus admin-added rows.
 * Each row carries: source, format/content category, feature_id, frequency,
 * quality, consumers list, and (for composites) trigger pattern + window.
 */
export default function SignalRulesTab({ notify }) {
  const [rows, setRows]     = useState([]);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy]     = useState(false);

  // Form state
  const [signalName, setN]     = useState("");
  const [source, setSrc]       = useState("ui");
  const [fmtCat, setFc]        = useState("");
  const [ctnCat, setCc]        = useState("");
  const [featureId, setFid]    = useState("");
  const [freq, setFreq]        = useState("moderate");
  const [quality, setQuality]  = useState("medium");
  const [consumers, setCons]   = useState([]);
  const [triggerPattern, setTrigger] = useState("");
  const [timeWindow, setTimeWindow]  = useState("");

  // Filter state for the active-rules table
  const [filterSource, setFilterSource] = useState("");

  async function refresh() {
    try { setRows(await api.listSignalRules()); }
    catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  function resetForm() {
    setN(""); setSrc("ui"); setFc(""); setCc("");
    setFid(""); setFreq("moderate"); setQuality("medium");
    setCons([]); setTrigger(""); setTimeWindow("");
    setEditing(false);
  }

  function loadIntoForm(row) {
    setN(row.signal_name || row.entity_id);
    setSrc(row.source || "ui");
    setFc(row.format_category || "");
    setCc(row.content_category || "");
    setFid(row.feature_id != null ? String(row.feature_id) : "");
    setFreq(row.expected_frequency || "moderate");
    setQuality(row.evidence_quality || "medium");
    setCons(Array.isArray(row.consumers) ? row.consumers : []);
    setTrigger(row.trigger_pattern || "");
    setTimeWindow(row.time_window_sec != null ? String(row.time_window_sec) : "");
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!signalName.trim()) return;
    setBusy(true);
    try {
      const payload = {
        signal_name:        signalName.trim(),
        source:             source,
        format_relevant:    Boolean(fmtCat),
        content_relevant:   Boolean(ctnCat),
        format_category:    fmtCat || null,
        content_category:   ctnCat || null,
        feature_id:         featureId ? parseInt(featureId, 10) : null,
        expected_frequency: freq,
        evidence_quality:   quality,
        consumers:          consumers,
      };
      if (source === "composite") {
        payload.trigger_pattern = triggerPattern.trim() || null;
        payload.time_window_sec = timeWindow ? parseInt(timeWindow, 10) : null;
      }
      await api.upsertSignalRule(payload);
      notify(`Signal "${signalName}" ${editing ? "updated" : "saved"}`);
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
      await api.deleteSignalRule(row.signal_name || row.entity_id);
      notify(`Signal "${row.signal_name || row.entity_id}" deleted`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  function toggleConsumer(c) {
    setCons(consumers.includes(c)
      ? consumers.filter((x) => x !== c)
      : [...consumers, c]);
  }

  const filteredRows = useMemo(() => {
    if (!filterSource) return rows;
    return rows.filter((r) => (r.source || "") === filterSource);
  }, [rows, filterSource]);

  // Grouped counts for the source filter
  const sourceCounts = useMemo(() => {
    const map = {};
    for (const r of rows) {
      const s = r.source || "(unset)";
      map[s] = (map[s] || 0) + 1;
    }
    return map;
  }, [rows]);

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing signal: ${signalName}` : "Add or update signal routing rule"}
        </h2>
        <p className="admin-section-sub">
          Each signal has two reward axes — <strong>format</strong> and{" "}
          <strong>content</strong>. Pick a strength category per axis, or leave
          blank for <code>NOT_RECORDED</code> (no bandit update on that axis).
          The system ships 25 signals (15 atomic + 10 composite); you can edit
          any value, add new signals, or delete unused ones.
        </p>
        <ul className="col-legend">
          <li><strong>Signal name</strong> — snake_case identifier matching what the classifier, UI, or composite detector emits.
            <em> e.g. thumbs_up, format_compliance_pass, pattern_regret.</em></li>
          <li><strong>Source</strong> — origin of the signal.
            <em> ui = button click; llm = classifier text detection; derived = automatic (compliance, session); composite = multi-signal pattern.</em></li>
          <li><strong>Format reward</strong> — strength on the format/presentation axis.
            <em> e.g. strong_negative for format_change_request; weak_positive for copy_save.</em></li>
          <li><strong>Content reward</strong> — strength on the content/accuracy axis.
            <em> e.g. strong_negative for content_correction; None for thumbs_up (it's ambiguous, kept analytics-only).</em></li>
          <li><strong>Feature ID</strong> — stable integer for ML feature encoding. Never reuse across signals.
            <em> e.g. 1 (format_change_request), 13 (thumbs_up), 17 (pattern_engaged_positive).</em></li>
          <li><strong>Expected frequency</strong> — sanity bound for monitoring.
            <em> common = most turns; moderate = some turns; rare = should fire infrequently.</em></li>
          <li><strong>Evidence quality</strong> — how trustworthy this signal is for bandit learning (Stage 2 priors).
            <em> high = explicit/objective; medium = behavioral; low = inferred or ambiguous.</em></li>
          <li><strong>Consumers</strong> — downstream systems that read this signal.
            <em> bandit = updates UCB rewards; instruction_quality = flags strategy issues; analytics = dashboards; retention = cohort analysis.</em></li>
          {source === "composite" && (
            <>
              <li><strong>Trigger pattern</strong> — human-readable description of detection rule (free text; detection logic lives in <code>ape/signals/composites.py</code>).
                <em> e.g. "thumbs_up THEN regenerate_click (sequence)".</em></li>
              <li><strong>Time window (seconds)</strong> — max age of pattern. Leave blank for same-response only.
                <em> e.g. 60 for pattern_regret, 120 for pattern_silent_acceptance.</em></li>
            </>
          )}
        </ul>

        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Signal name
              <input
                type="text"
                placeholder="e.g. thumbs_up"
                value={signalName}
                onChange={(e) => setN(e.target.value)}
                disabled={editing}
                required
              />
            </label>
            <label>
              Source
              <select value={source} onChange={(e) => setSrc(e.target.value)}>
                {SOURCE_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
            <label>
              Feature ID
              <input
                type="number"
                min="0"
                placeholder="0-24+"
                value={featureId}
                onChange={(e) => setFid(e.target.value)}
                title="Stable integer for ML encoding. Never reuse."
              />
            </label>
          </div>

          <div className="form-row">
            <label className="grow">
              Format reward category
              <select value={fmtCat} onChange={(e) => setFc(e.target.value)}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </label>
            <label className="grow">
              Content reward category
              <select value={ctnCat} onChange={(e) => setCc(e.target.value)}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </label>
          </div>

          <div className="form-row">
            <label>
              Expected frequency
              <select value={freq} onChange={(e) => setFreq(e.target.value)}>
                {FREQ_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </label>
            <label>
              Evidence quality
              <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                {QUALITY_OPTIONS.map((q) => <option key={q} value={q}>{q}</option>)}
              </select>
            </label>
          </div>

          <div className="form-row">
            <fieldset className="consumers-fieldset">
              <legend>Consumers</legend>
              {CONSUMER_OPTIONS.map((c) => (
                <label key={c} className="consumer-chip">
                  <input
                    type="checkbox"
                    checked={consumers.includes(c)}
                    onChange={() => toggleConsumer(c)}
                  />
                  {c}
                </label>
              ))}
            </fieldset>
          </div>

          {source === "composite" && (
            <>
              <div className="form-row">
                <label className="grow">
                  Trigger pattern (human-readable)
                  <input
                    type="text"
                    placeholder="e.g. thumbs_up THEN regenerate_click (sequence)"
                    value={triggerPattern}
                    onChange={(e) => setTrigger(e.target.value)}
                  />
                </label>
                <label>
                  Time window (sec)
                  <input
                    type="number"
                    min="0"
                    placeholder="blank = same response"
                    value={timeWindow}
                    onChange={(e) => setTimeWindow(e.target.value)}
                  />
                </label>
              </div>
              <p className="composite-warning">
                ⚠ Composite signals also need detection logic in{" "}
                <code>ape/signals/composites.py</code>. The trigger pattern field
                here is descriptive — the actual code-side detector must match.
              </p>
            </>
          )}

          <div className="form-row form-actions">
            <button type="submit" className="btn-primary" disabled={busy || !signalName.trim()}>
              {busy ? "Saving…" : (editing ? "Update signal" : "Save signal")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <div className="signal-list-head">
          <h2 className="admin-section-title">Active signals ({rows.length})</h2>
          <label className="signal-filter">
            Filter by source:
            <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
              <option value="">(all sources)</option>
              {SOURCE_TYPES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.value} ({sourceCounts[s.value] || 0})
                </option>
              ))}
            </select>
          </label>
        </div>

        <AdminTable
          columns={[
            { key: "signal_name", label: "Signal", width: "230px",
              render: (r) => (
                <span className="signal-cell">
                  <code className="code-pill">{r.signal_name || r.entity_id}</code>
                  <span className={`source-badge source-${r.source || "unknown"}`}>
                    {r.source || "—"}
                  </span>
                </span>
              ) },
            { key: "feature_id", label: "FeatID", width: "60px",
              render: (r) => <span className="num">{r.feature_id ?? "—"}</span> },
            { key: "format_category", label: "Format", width: "150px",
              render: (r) => r.format_category
                ? <span className={`reward-badge reward-${r.format_category}`}>{rewardLabel(r.format_category)}</span>
                : <span className="muted">—</span> },
            { key: "content_category", label: "Content", width: "150px",
              render: (r) => r.content_category
                ? <span className={`reward-badge reward-${r.content_category}`}>{rewardLabel(r.content_category)}</span>
                : <span className="muted">—</span> },
            { key: "expected_frequency", label: "Freq", width: "80px",
              render: (r) => <span className="freq-tag">{r.expected_frequency || "—"}</span> },
            { key: "evidence_quality", label: "Quality", width: "80px",
              render: (r) => <span className="quality-tag">{r.evidence_quality || "—"}</span> },
            { key: "consumers", label: "Consumers",
              render: (r) => (
                <span className="consumer-list">
                  {(r.consumers || []).map((c) => (
                    <span key={c} className="consumer-pill">{c}</span>
                  ))}
                </span>
              ) },
            { key: "status", label: "Status", width: "110px",
              render: (r) => (
                <StatusPill
                  entityType="signal_routing"
                  entityId={r.signal_name || r.entity_id}
                  status={r.status}
                  notify={notify}
                  onChanged={refresh}
                />
              ) },
          ]}
          rows={filteredRows.map((r, i) => ({ ...r, _key: i }))}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete signal "${row.signal_name}"? Feature ID ${row.feature_id} will not be reused. Future feedback with this signal will be ignored.`}
          emptyText="No signal rules configured. Run /admin/seed to load defaults."
        />
      </div>
    </div>
  );
}

function rewardLabel(category) {
  return ({
    strong_positive:  "+1.0",
    weak_positive:    "+0.5",
    weak_negative:    "−0.5",
    strong_negative:  "−1.0",
  })[category] || category;
}
