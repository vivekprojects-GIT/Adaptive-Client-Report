import { useEffect, useMemo, useState } from "react";
import { api } from "../../api.js";
import AdminTable from "./AdminTable.jsx";
import InstructionQualityPanel from "./InstructionQualityPanel.jsx";

/**
 * InstructionsTab — full lifecycle for per-strategy instruction text.
 *
 * Strategy → instruction is one-to-many (versioned). At any time exactly one
 * version per strategy is ACTIVE; the rest are DRAFT or INACTIVE. The
 * synthesizer LLM uses the ACTIVE version when rendering a response.
 *
 * The top of the tab shows a coverage badge: "X of Y strategies have an
 * active instruction". Strategies with no instruction at all are flagged so
 * the admin can publish one.
 */
export default function InstructionsTab({ notify }) {
  const [strategies, setStrategies] = useState([]);
  const [instructions, setInst]     = useState([]);
  const [strategyId, setSid]        = useState("");
  const [version, setVersion]       = useState("");
  const [text, setText]             = useState("");
  const [uri, setUri]               = useState("");
  const [activate, setActivate]     = useState(true);
  const [busy, setBusy]             = useState(false);
  const [filter, setFilter]         = useState("");   // strategy_id filter for the list

  async function refresh() {
    try {
      const [s, i] = await Promise.all([api.listStrategies(), api.listInstructions()]);
      setStrategies(s);
      setInst(i);
      if (s.length && !strategyId) setSid(s[0].strategy_id);
    } catch (err) {
      notify("Load failed: " + err.message, "error");
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  // --- Coverage stats ---
  const { activeByStrategy, missing } = useMemo(() => {
    const active = new Map();
    for (const i of instructions) {
      if (i.status === "ACTIVE") active.set(i.entity_id, i);
    }
    const miss = strategies.filter((s) => !active.has(s.strategy_id)).map((s) => s.strategy_id);
    return { activeByStrategy: active, missing: miss };
  }, [strategies, instructions]);

  const filteredRows = filter
    ? instructions.filter((r) => r.entity_id === filter)
    : instructions;

  // --- Handlers ---
  async function handleSubmit(e) {
    e.preventDefault();
    if (!strategyId || !version.trim() || !text.trim()) {
      notify("Strategy, version and text are required", "error");
      return;
    }
    setBusy(true);
    try {
      await api.publishInstruction({
        strategy_id: strategyId,
        version:     version.trim(),
        instruction_text: text,
        instruction_uri:  uri || null,
        activate,
      });
      notify(
        activate
          ? `Instruction ${strategyId}@${version} published & activated`
          : `Instruction ${strategyId}@${version} published as DRAFT`
      );
      setText(""); setUri(""); setVersion("");
      refresh();
    } catch (err) {
      notify("Save failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleActivate(row) {
    setBusy(true);
    try {
      await api.activateInstruction(row.entity_id, row.version);
      notify(`Activated ${row.entity_id}@${row.version}`);
      refresh();
    } catch (err) {
      notify("Activate failed: " + err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function loadIntoForm(row) {
    setSid(row.entity_id);
    setVersion("v" + (parseVersion(row.version) + 1));  // suggest the next version
    setText(row.instruction_text || "");
    setUri(row.instruction_uri || "");
    setActivate(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
    notify(`Loaded ${row.entity_id}@${row.version} into form — bump version to publish a new revision`);
  }

  async function handleDelete(row) {
    try {
      await api.deleteInstruction(row.entity_id, row.version);
      notify(`Deleted ${row.entity_id}@${row.version}`);
      refresh();
    } catch (err) {
      notify("Delete failed: " + err.message, "error");
    }
  }

  return (
    <div className="admin-tab-content">
      {/* Instruction quality panel — tells admin which instructions need fixing */}
      <div className="admin-section">
        <InstructionQualityPanel notify={notify} />
      </div>

      {/* Coverage banner */}
      <div className={`admin-coverage ${missing.length === 0 ? "ok" : "warn"}`}>
        <strong>
          {activeByStrategy.size} of {strategies.length} strategies have an active instruction
        </strong>
        {missing.length > 0 && (
          <div className="admin-coverage-missing">
            Missing: {missing.map((m) => (
              <button
                key={m}
                className="missing-chip"
                onClick={() => { setSid(m); setVersion("v1"); setText(""); window.scrollTo({top: 0, behavior:"smooth"}); }}
                title="Click to start drafting an instruction for this strategy"
              >
                {m}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="admin-section">
        <h2 className="admin-section-title">Publish a new instruction version</h2>
        <p className="admin-section-sub">
          Instructions are versioned per strategy. Publishing creates a new
          version; activating it deactivates the previous version and makes
          the new one ACTIVE — used by the synthesizer from the next turn onward.
        </p>
        <ul className="col-legend">
          <li><strong>Strategy</strong> — which arm this instruction belongs to. Strategies with no instruction yet show "(no instruction)" — those are the ones to prioritize.
            <em> e.g. decision_card, comparison_table.</em></li>
          <li><strong>Version</strong> — free-form tag for this revision. Convention is v1, v2, v3. Pick the next number after the current ACTIVE version; old versions stay browsable so you can revert.
            <em> e.g. v1 (first draft), v2 (tightened on retirement examples), v3 (fixed tax_implications regression).</em></li>
          <li><strong>URI (optional)</strong> — external link to the source of truth, e.g. a Notion doc or S3 object the instruction was authored in. Stored alongside the text; not used at runtime.
            <em> e.g. s3://ape/instructions/decision_card/v2.md or https://notion.so/page-id.</em></li>
          <li><strong>Instruction text</strong> — the actual system-prompt fragment the synthesizer sees when this strategy is picked. Be concrete about structure, length, and tone.
            <em> e.g. "Format the answer as a 3-row decision card with sections Recommendation, Why, Caveats. Keep each under 40 words."</em></li>
          <li><strong>Activate immediately</strong> — if checked, this version becomes ACTIVE on save and the previous ACTIVE flips to INACTIVE. If unchecked, version is saved as DRAFT and you activate it later from the table.
            <em> e.g. check it for safe edits, leave unchecked for risky rewrites you want to review first.</em></li>
        </ul>
        <form className="admin-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Strategy
              <select value={strategyId} onChange={(e) => setSid(e.target.value)}>
                {strategies.map((s) => (
                  <option key={s.strategy_id} value={s.strategy_id}>
                    {s.strategy_id}{!activeByStrategy.has(s.strategy_id) ? "  (no instruction)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Version
              <input
                type="text"
                placeholder="e.g. v2"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                required
              />
            </label>
            <label className="grow">
              URI (optional)
              <input
                type="text"
                placeholder="s3://ape/instructions/..."
                value={uri}
                onChange={(e) => setUri(e.target.value)}
              />
            </label>
          </div>
          <label>
            Instruction text
            <textarea
              rows={6}
              placeholder="e.g. Format your response as a two-column pros/cons table."
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
          </label>
          <div className="form-row form-actions">
            <label className="check-inline">
              <input
                type="checkbox"
                checked={activate}
                onChange={(e) => setActivate(e.target.checked)}
              />
              <span>Activate immediately (deactivates previous version)</span>
            </label>
            <div className="form-spacer"/>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Saving…" : (activate ? "Publish & activate" : "Publish as DRAFT")}
            </button>
          </div>
        </form>
      </div>

      <div className="admin-section">
        <div className="instructions-list-head">
          <h2 className="admin-section-title">
            All instructions ({instructions.length})
          </h2>
          <label className="instructions-filter">
            Filter by strategy:
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">(all)</option>
              {strategies.map((s) => (
                <option key={s.strategy_id} value={s.strategy_id}>{s.strategy_id}</option>
              ))}
            </select>
          </label>
        </div>
        <AdminTable
          columns={[
            { key: "entity_id", label: "Strategy", width: "220px",
              render: (r) => <code className="code-pill">{r.entity_id}</code> },
            { key: "version", label: "Version", width: "80px",
              render: (r) => <span className="ts">{r.version}</span> },
            { key: "status", label: "Status", width: "100px",
              render: (r) => (
                <span className={r.status === "ACTIVE" ? "status-chip" : "status-chip status-chip-muted"}>
                  {r.status || "—"}
                </span>
              ) },
            { key: "instruction_text", label: "Instruction text",
              render: (r) => <span className="instruction-preview">{r.instruction_text}</span> },
            { key: "ts", label: "Updated", width: "160px",
              render: (r) => <span className="ts">{(r.ts || "").slice(0, 19).replace("T", " ")}</span> },
            { key: "_activate", label: "", width: "120px",
              render: (r) => r.status !== "ACTIVE" && (
                <button
                  className="admin-row-btn"
                  onClick={() => handleActivate(r)}
                  disabled={busy}
                  title="Make this the active version for the strategy"
                >
                  Activate
                </button>
              ) },
          ]}
          rows={filteredRows.map((r, i) => ({ ...r, _key: `${r.entity_id}_${r.version}_${i}` }))}
          onEdit={loadIntoForm}
          onDelete={handleDelete}
          deleteConfirm={(row) => `Delete ${row.entity_id}@${row.version}? ${row.status === "ACTIVE" ? "This is the ACTIVE version — the synthesizer will fall back to default behavior." : "This is a non-active version."}`}
          emptyText={filter ? `No instructions for strategy "${filter}".` : "No instructions yet. Publish one above or run /admin/seed."}
        />
      </div>
    </div>
  );
}

function parseVersion(v) {
  if (!v) return 1;
  const m = String(v).match(/(\d+)/);
  return m ? parseInt(m[1], 10) : 1;
}
