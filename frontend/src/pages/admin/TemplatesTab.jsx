import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";
import TemplateCanvas from "./TemplateCanvas.jsx";

// The shared presentation vocabulary. A template's style vector and a
// client's learned preference profile are expressed in these same terms —
// that shared vocabulary is what lets a chat signal ("show me a table")
// reach a template the client has never received.
const DIMENSIONS = [
  "concise", "detail", "visual", "table", "comparison",
  "numeric_precision", "narrative", "step_by_step", "technical_depth",
];

const emptyStyle = () => Object.fromEntries(DIMENSIONS.map((d) => [d, 0.5]));

export default function TemplatesTab({ notify }) {
  const [rows, setRows]         = useState([]);
  const [types, setTypes]       = useState([]);
  const [filter, setFilter]     = useState("quarterly_portfolio_review");

  const [templateId, setTid]    = useState("");
  const [strategy, setStrategy] = useState("");
  const [reportType, setRt]     = useState("");
  const [label, setLabel]       = useState("");
  const [description, setDesc]  = useState("");
  const [brief, setBrief]       = useState("");
  const [required, setRequired] = useState([]);
  const [optional, setOptional] = useState([]);
  const [style, setStyle]       = useState(emptyStyle());
  const [editing, setEditing]   = useState(false);
  const [busy, setBusy]         = useState(false);

  async function refresh() {
    try {
      const [t, rt] = await Promise.all([api.listTemplates(), api.listReportTypes()]);
      setRows(t); setTypes(rt);
      if (!reportType && rt.length) setRt(rt[0].report_type || rt[0].entity_id);
    } catch (err) { notify("Load failed: " + err.message, "error"); }
  }
  useEffect(() => { refresh(); }, []);

  const visible = useMemo(
    () => (filter ? rows.filter((r) => r.report_type === filter) : rows),
    [rows, filter]
  );

  // Arms grouped by report type — this is the bandit's actual arm layout.
  const armsByType = useMemo(() => {
    const m = {};
    rows.forEach((r) => {
      if (r.status && r.status !== "ACTIVE") return;
      (m[r.report_type] ||= []).push(r.strategy);
    });
    return m;
  }, [rows]);

  function resetForm() {
    setTid(""); setStrategy(""); setLabel(""); setDesc(""); setBrief("");
    setRequired([]); setOptional([]); setStyle(emptyStyle()); setEditing(false);
  }

  function loadIntoForm(row) {
    setTid(row.template_id || row.entity_id);
    setStrategy(row.strategy || "");
    setRt(row.report_type || "");
    setLabel(row.label || "");
    setDesc(row.description || "");
    setBrief(row.brief || "");
    setRequired(row.required_blocks || []);
    setOptional(row.optional_blocks || []);
    setStyle({ ...emptyStyle(), ...(row.style_profile || {}) });
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!templateId.trim() || !strategy.trim() || !reportType) return;
    setBusy(true);
    try {
      await api.upsertTemplate({
        template_id: templateId.trim(),
        strategy: strategy.trim(),
        report_type: reportType,
        label: label.trim(),
        description: description.trim(),
        brief: brief.trim(),
        required_blocks: required,
        optional_blocks: optional,
        style_profile: style,
      });
      notify(`Template "${templateId}" ${editing ? "updated" : "saved"}`);
      resetForm(); refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally { setBusy(false); }
  }

  async function handleDelete(row) {
    try {
      await api.deleteTemplate(row.template_id || row.entity_id);
      notify(`Template "${row.template_id || row.entity_id}" deleted`);
      refresh();
    } catch (err) { notify("Delete failed: " + err.message, "error"); }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-section">
        <h2 className="admin-section-title">
          {editing ? `Editing template: ${templateId}` : "Add or update template"}
        </h2>
        <p className="admin-section-sub">
          A template is one <code>(report type × presentation style)</code> pair.
          The <strong>arm</strong> is the style — and the same six style names mean
          the same thing in every report type. That is deliberate: it is what lets
          a client's learned preference <em>transfer</em>. Someone who keeps asking
          for tables in their quarterly review gets the numeric variant of their
          risk report too, without risk reports having had to learn it separately.
        </p>
        <div className="rule-box">
          <div><strong>Arm</strong> = presentation style. Shared vocabulary, so preference transfers.</div>
          <div><strong>Template</strong> = that style applied to one report type, with its own blocks and brief.</div>
          <div>Each report type offers only the styles that suit it — an executive summary has no detailed-narrative variant.</div>
        </div>
        <ul className="col-legend">
          <li><strong>Strategy</strong> — the arm key, i.e. the presentation style. Immutable once serving. <em>balanced · concise · visual · numeric · narrative · comparison.</em></li>
          <li><strong>Document</strong> — the blocks, in reading order. The preview on the right is the live generator rendering a real client’s facts, so what you see is what ships.</li>
          <li><strong>Brief</strong> — the writing instruction handed to the LLM. This is what compliance approves; it fixes structure while leaving wording to the model.</li>
          <li><strong>Style vector</strong> — where this template sits on each presentation dimension. Scored by cosine against the client's learned profile.</li>
        </ul>

        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Template ID
              <input type="text" placeholder="e.g. comparison_focused_v1" value={templateId}
                     onChange={(e) => setTid(e.target.value)} disabled={editing} required />
            </label>
            <label>
              Strategy (arm key)
              <input type="text" placeholder="e.g. comparison_focused" value={strategy}
                     onChange={(e) => setStrategy(e.target.value)} disabled={editing} required />
            </label>
            <label>
              Report type
              <select value={reportType} onChange={(e) => setRt(e.target.value)} disabled={editing}>
                {types.map((t) => (
                  <option key={t.report_type || t.entity_id} value={t.report_type || t.entity_id}>
                    {t.label || t.report_type}{t.personalisable === false ? "  (prescribed)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Label
              <input type="text" placeholder="Comparison" value={label}
                     onChange={(e) => setLabel(e.target.value)} />
            </label>
          </div>

          <div className="form-row">
            <label style={{ flex: 1 }}>
              Description
              <input type="text" placeholder="What this shape is for, in one line"
                     value={description} onChange={(e) => setDesc(e.target.value)} />
            </label>
          </div>

          <div className="form-row">
            <label style={{ flex: 1 }}>
              Writing brief (approved by compliance)
              <textarea rows={3} placeholder="Frame every figure against its benchmark…"
                        value={brief} onChange={(e) => setBrief(e.target.value)} />
            </label>
          </div>

          <div className="form-row" style={{ flexDirection: "column",
                                              alignItems: "stretch" }}>
            <label style={{ marginBottom: "8px" }}>
              Document — build it and watch the real report render
            </label>
            <TemplateCanvas blocks={required} setBlocks={setRequired}
                            reportType={reportType} strategy={strategy}
                            label={label} brief={brief} notify={notify} />
          </div>

          <div className="form-row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            <label style={{ marginBottom: "8px" }}>Style vector</label>
            <div className="style-grid">
              {DIMENSIONS.map((d) => (
                <div key={d} className="style-dim">
                  <div className="style-dim-row">
                    <span>{d.replace(/_/g, " ")}</span>
                    <b>{(style[d] ?? 0).toFixed(2)}</b>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={style[d] ?? 0.5}
                         onChange={(e) => setStyle({ ...style, [d]: parseFloat(e.target.value) })} />
                </div>
              ))}
            </div>
          </div>

          <div className="form-row">
            <button type="submit" className="btn-primary"
                    disabled={busy || !templateId.trim() || !strategy.trim()}>
              {busy ? "Saving…" : (editing ? "Update template" : "Save template")}
            </button>
            {editing && (
              <button type="button" className="btn-secondary" onClick={resetForm}>Cancel</button>
            )}
          </div>
        </form>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Arms by report type</h2>
        <p className="admin-section-sub">
          Each report type runs its own separate bandit, keyed
          <code> scope#report_type</code>. These are the arm sets — note the same
          style names recurring, which is what carries preference across them.
        </p>
        <div className="style-legend">
          {["balanced","concise","visual","numeric","narrative","comparison"].map((st) => {
            const n = rows.filter((r) => r.strategy === st).length;
            return <span key={st} className="style-chip">{st}<b>{n}</b></span>;
          })}
        </div>
        <div className="arm-map">
          {types.map((t) => {
            const id = t.report_type || t.entity_id;
            const arms = armsByType[id] || [];
            const prescribed = t.personalisable === false;
            return (
              <div key={id} className="arm-map-row">
                <div className="arm-map-name">
                  {t.label || id}
                  {prescribed
                    ? <span className="pill pill-danger">prescribed — no D1</span>
                    : <span className="pill pill-ok">{arms.length} arms</span>}
                </div>
                <code className="arm-map-arms">{arms.length ? arms.join(" · ") : "—"}</code>
              </div>
            );
          })}
        </div>
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">
          Templates ({visible.length})
          <select className="inline-filter" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">all report types</option>
            {types.map((t) => (
              <option key={t.report_type || t.entity_id} value={t.report_type || t.entity_id}>
                {t.label || t.report_type}
              </option>
            ))}
          </select>
        </h2>
        <AdminTable
          columns={[
            { key: "template_id", label: "Template", width: "230px",
              render: (r) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{r.label || r.strategy}</div>
                  <code className="code-pill">{r.template_id || r.entity_id}</code>
                </div>
              ) },
            { key: "strategy", label: "Arm key", width: "180px",
              render: (r) => <code className="code-pill">{r.strategy}</code> },
            { key: "report_type", label: "Report type", width: "200px",
              render: (r) => <span className="ts">{r.report_type}</span> },
            { key: "required_blocks", label: "Required blocks",
              render: (r) => (
                <span className="ts">{(r.required_blocks || []).join(", ") || "—"}</span>
              ) },
            { key: "status", label: "Status", width: "130px",
              render: (r) => (
                <StatusPill entityType="template"
                            entityId={r.template_id || r.entity_id}
                            status={r.status} notify={notify} onChanged={refresh} />
              ) },
          ]}
          rows={visible}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete template "${row.template_id}"? Its arm history is kept for audit.`}
          emptyText="No templates configured yet."
        />
      </div>
    </div>
  );
}
