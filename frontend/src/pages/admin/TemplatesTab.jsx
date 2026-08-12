import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import StatusPill from "./StatusPill.jsx";
import TemplateCanvas from "./TemplateCanvas.jsx";

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

  function resetForm() {
    setTid(""); setStrategy(""); setLabel(""); setDesc(""); setBrief("");
    setRequired([]); setEditing(false);
  }

  function loadIntoForm(row) {
    setTid(row.template_id || row.entity_id);
    setStrategy(row.strategy || "");
    setRt(row.report_type || "");
    setLabel(row.label || "");
    setDesc(row.description || "");
    setBrief(row.brief || "");
    setRequired(row.required_blocks || []);
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
          A template is an ordered list of blocks, belonging to exactly one
          report type — its blocks assume that type's facts, so it cannot be
          used under another. Create as many per report type as you need;
          the advisor picks one at generation time, or lets the composer
          design a one-off from the block registry.
        </p>
        <div className="rule-box">
          <div><strong>Nothing selects between them.</strong> A person does. No bandit, no exploration, no reward.</div>
          <div><strong>What adapts</strong> is the wording and block order the composer produces — driven by the client's learned profile and their stated preferences, not by which template won.</div>
        </div>
        <ul className="col-legend">
          <li><strong>Name</strong> — how this template appears in the advisor's picker. Make it say what the reader gets.</li>
          <li><strong>Document</strong> — the blocks, in reading order. The preview on the right is the live generator rendering a real client’s facts, so what you see is what ships.</li>
          <li><strong>Brief</strong> — the writing instruction handed to the LLM. This is what compliance approves; it fixes structure while leaving wording to the model.</li>
        </ul>

        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Template ID
              <input type="text" placeholder="e.g. comparison_focused_v1" value={templateId}
                     onChange={(e) => setTid(e.target.value)} disabled={editing} required />
            </label>
            <label>
              Strategy
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
