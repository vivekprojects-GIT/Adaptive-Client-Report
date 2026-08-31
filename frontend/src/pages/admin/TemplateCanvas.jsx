import { useEffect, useRef, useState } from "react";
import { api } from "../../api.js";

/**
 * TemplateCanvas — build a template by arranging blocks, and see the real
 * document as you go.
 *
 * The preview is NOT a mock-up. It posts the draft to
 * /config/templates/preview, which runs the same build_report ->
 * enforce_mandatory -> grounding -> render_html path that generation uses,
 * against a real client's frozen facts. What the author sees here is
 * literally what the client receives — there is no second renderer that
 * could drift from the first.
 *
 * Two things the preview teaches that a checkbox list cannot:
 *   - blocks the coverage gate had to ADD (forget the fees table and it
 *     appears anyway, flagged)
 *   - blocks that silently could not build for this client's data
 */

// Display names for the blocks we have bothered to name. The palette
// itself comes from /registry/blocks - see usePalette below - so this map
// only prettifies; it never decides what exists.
const NICE = {
  kpi_grid: "KPI grid",
  callout: "Callout banner",
  narrative: "Narrative",
  key_takeaways: "Key takeaways",
  explainer: "Plain-English explainer",
  disclosures: "Disclosures",
  performance_history: "Return over time",
  returns_table: "Return by period",
  comparison_chart: "Portfolio vs benchmark",
  comparison_table: "Contribution table",
  top_contributors: "Top contributors",
  top_detractors: "Top detractors",
  performance_line: "Return this period",
  allocation_donut: "Asset allocation",
  allocation_vs_target: "Allocation vs target",
  holdings_table: "Holdings table",
  risk_card: "Risk level",
  fees_table: "Fees and costs",
  wealth_cover: "Statement cover",
  asset_class_table: "Asset classes vs mandate",
  currency_split: "Currency exposure",
  holdings_by_sector: "Holdings by sector",
  sector_analysis: "Sector analysis",
};

const CATEGORY_TITLE = {
  headline: "Headline",
  prose: "Prose",
  performance: "Performance",
  attribution: "Attribution",
  allocation: "Composition",
  costs: "Money",
  risk: "Risk",
  smallprint: "Small print",
};

function titleFor(id) {
  return NICE[id] || String(id).replace(/_/g, " ").replace(
    /^./, (c) => c.toUpperCase());
}

const CHART_KINDS = ["donut", "pie", "bar", "hbar", "line", "area", "stacked",
                     "waterfall", "treemap", "funnel", "gauge", "progress",
                     "radar", "heatmap", "scatter", "bubble", "combo",
                     "histogram"];

function labelFor(spec) {
  const [type, opt] = String(spec).split(":");
  if (type === "chart") return `Chart — ${opt || "donut"}`;
  return titleFor(type);
}

/**
 * The palette, from the server.
 *
 * Every block the registry declares, grouped by the fact category it
 * covers. Fetched rather than listed here so that adding a block to the
 * backend is enough to make it selectable - the previous hardcoded copy
 * meant a new block existed everywhere except the screen where somebody
 * would choose it.
 *
 * Chart variants are filtered out: they arrive as chart:donut, chart:bar
 * and so on, and the canvas already has a dedicated chart control with a
 * kind selector. Listing eighteen of them again would bury the blocks.
 */
function usePalette() {
  const [groups, setGroups] = useState([]);
  useEffect(() => {
    let alive = true;
    api.registryBlocks()
      .then((r) => {
        if (!alive) return;
        const cats = (r && r.categories) || [];
        setGroups(cats.map((c) => [
          CATEGORY_TITLE[c.category] || titleFor(c.category),
          (c.blocks || [])
            .filter((b) => b.kind !== "chart")
            .map((b) => [b.block, titleFor(b.block), b.shows]),
        ]).filter(([, items]) => items.length));
      })
      .catch(() => setGroups([]));
    return () => { alive = false; };
  }, []);
  return groups;
}

export default function TemplateCanvas({
  blocks, setBlocks, reportType, strategy, label, brief, notify,
}) {
  const palette               = usePalette();
  const [preview, setPreview] = useState(null);
  const [busy, setBusy]       = useState(false);
  const [err, setErr]         = useState(null);
  const [chartKind, setKind]  = useState("donut");
  const [dragFrom, setDrag]   = useState(null);
  const timer = useRef(null);

  // Debounced: every reorder would otherwise be a round trip through the
  // whole generator.
  useEffect(() => {
    if (!blocks.length || !reportType) { setPreview(null); return; }
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setBusy(true);
      try {
        setPreview(await api.previewTemplate({
          report_type: reportType, required_blocks: blocks,
          strategy, label, brief,
        }));
        setErr(null);
      } catch (e) { setErr(e.message); setPreview(null); }
      finally { setBusy(false); }
    }, 450);
    return () => clearTimeout(timer.current);
  }, [blocks, reportType, strategy, label, brief]);

  // Functional updates throughout: rapid clicks land in the same React
  // tick, and closing over `blocks` would make every click after the first
  // overwrite the ones before it.
  const add = (spec) => setBlocks((prev) =>
    prev.includes(spec) ? prev : [...prev, spec]);
  const remove = (i) => setBlocks((prev) => prev.filter((_, j) => j !== i));
  const move = (i, d) => setBlocks((prev) => {
    const j = i + d;
    if (j < 0 || j >= prev.length) return prev;
    const next = [...prev];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  });
  function drop(to) {
    setBlocks((prev) => {
      if (dragFrom === null || dragFrom === to) return prev;
      const next = [...prev];
      const [item] = next.splice(dragFrom, 1);
      next.splice(to, 0, item);
      return next;
    });
    setDrag(null);
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "200px 260px 1fr",
                  gap: 16, alignItems: "start" }}>

      {/* palette */}
      <div>
        <div style={hdr}>Blocks</div>
        {palette.map(([group, items]) => (
          <div key={group} style={{ marginBottom: 10 }}>
            <div style={grpLbl}>{group}</div>
            {items.map(([id, name, shows]) => (
              /* title carries the registry's own description of the block,
                 so an author can tell two similar ones apart without
                 adding it. */
              <button key={id} type="button" onClick={() => add(id)} title={shows || name}
                      disabled={blocks.includes(id)} style={chip(blocks.includes(id))}>
                {name}
              </button>
            ))}
          </div>
        ))}
        <div style={grpLbl}>Chart</div>
        <select value={chartKind} onChange={(e) => setKind(e.target.value)}
                style={{ width: "100%", padding: "5px 7px", fontSize: 12 }}>
          {CHART_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        <button type="button" onClick={() => add(`chart:${chartKind}`)}
                style={{ ...chip(false), marginTop: 5 }}>
          + add {chartKind} chart
        </button>
      </div>

      {/* canvas */}
      <div>
        <div style={hdr}>
          Document order
          <span style={{ float: "right", color: "#94a3b8", fontWeight: 400 }}>
            {blocks.length}
          </span>
        </div>
        {blocks.length === 0 && (
          <div style={{ ...box, color: "#94a3b8", fontSize: 12 }}>
            Click blocks on the left to build the document. Order here is the
            order the client reads.
          </div>
        )}
        {blocks.map((spec, i) => (
          <div key={spec + i} draggable
               onDragStart={() => setDrag(i)}
               onDragOver={(e) => e.preventDefault()}
               onDrop={() => drop(i)}
               style={{ ...box, display: "flex", alignItems: "center", gap: 6,
                        cursor: "grab",
                        borderColor: preview?.enforced_blocks?.includes(spec)
                          ? "#b45309" : "#e2e8f0" }}>
            <span style={{ color: "#cbd5e1", fontSize: 11, width: 14 }}>{i + 1}</span>
            <span style={{ flex: 1, fontSize: 12.5 }}>{labelFor(spec)}</span>
            <button type="button" onClick={() => move(i, -1)} style={mini}>↑</button>
            <button type="button" onClick={() => move(i, 1)} style={mini}>↓</button>
            <button type="button" onClick={() => remove(i)}
                    style={{ ...mini, color: "#b91c1c" }}>×</button>
          </div>
        ))}

        {preview?.enforced_blocks?.length > 0 && (
          <div style={{ ...note, background: "#fffbeb", borderColor: "#fde68a",
                        color: "#92400e" }}>
            <b>Added automatically:</b> {preview.enforced_blocks.join(", ")}.
            These categories are mandatory — personalisation changes how facts
            are shown, never whether the client is told them.
          </div>
        )}
        {preview?.unsupported_blocks?.length > 0 && (
          <div style={{ ...note, background: "#f8fafc", color: "#64748b" }}>
            <b>Not rendered for this client:</b>{" "}
            {preview.unsupported_blocks.join(", ")} — their data source has
            nothing to fill it with, so the block is skipped rather than faked.
          </div>
        )}
      </div>

      {/* live preview */}
      <div>
        <div style={hdr}>
          Live preview
          <span style={{ float: "right", fontWeight: 400, color: "#94a3b8" }}>
            {busy ? "rendering…"
                  : preview ? `${preview.client_name} · ${preview.period}` : ""}
          </span>
        </div>
        {err && <div style={{ ...note, background: "#fef2f2", color: "#b91c1c",
                              borderColor: "#fecaca" }}>{err}</div>}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 8,
                      overflow: "hidden", background: "#f8fafc" }}>
          {preview
            ? <iframe title="template preview" srcDoc={preview.html}
                      style={{ width: "100%", height: 620, border: 0,
                               background: "#fff" }} />
            : <div style={{ height: 620, display: "flex", alignItems: "center",
                            justifyContent: "center", color: "#94a3b8",
                            fontSize: 13 }}>
                Add a block to see the real report
              </div>}
        </div>
        {preview && (
          <div style={{ fontSize: 11.5, color: "#94a3b8", marginTop: 6 }}>
            Rendered through the live generator against {preview.client_name}'s
            frozen facts — {preview.validation_summary}.
          </div>
        )}
      </div>
    </div>
  );
}

const hdr = { fontSize: 12, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: ".05em", color: "#64748b", marginBottom: 8 };
const grpLbl = { fontSize: 10.5, textTransform: "uppercase", color: "#94a3b8",
                 letterSpacing: ".05em", margin: "8px 0 4px" };
const box = { border: "1px solid #e2e8f0", borderRadius: 6, padding: "7px 9px",
              marginBottom: 5, background: "#fff" };
const note = { border: "1px solid #e2e8f0", borderRadius: 6, padding: "8px 10px",
               marginTop: 8, fontSize: 11.5, lineHeight: 1.5 };
const mini = { border: "1px solid #e2e8f0", background: "#fff", borderRadius: 4,
               width: 20, height: 20, cursor: "pointer", fontSize: 11,
               color: "#64748b", padding: 0 };
const chip = (on) => ({
  display: "block", width: "100%", textAlign: "left", marginBottom: 3,
  border: "1px solid " + (on ? "#dbeafe" : "#e2e8f0"),
  background: on ? "#eff6ff" : "#fff", color: on ? "#93c5fd" : "#334155",
  borderRadius: 5, padding: "5px 8px", fontSize: 12,
  cursor: on ? "default" : "pointer",
});
