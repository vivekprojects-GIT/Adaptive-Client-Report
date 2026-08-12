import { useState } from "react";

/**
 * The three registries, drawn as trees.
 *
 * A tree because the nesting IS the information. A template belongs to
 * exactly one report type; a block covers exactly one fact category; a
 * learned profile belongs to one client and one report type. Flat lists
 * of any of these hide the only relationship worth knowing.
 *
 * Everything here is read-only. Authoring lives under Configuration —
 * this is for seeing what exists and how it hangs together, and a tree
 * that also edited would be two jobs in one control.
 */

function Node({ label, meta, count, children, defaultOpen = false, tone }) {
  const [open, setOpen] = useState(defaultOpen);
  const hasKids = Boolean(children);
  return (
    <li className={`tr-node ${open ? "open" : ""}`}>
      <div className={`tr-row ${hasKids ? "clickable" : ""} ${tone || ""}`}
           onClick={hasKids ? () => setOpen(!open) : undefined}
           role={hasKids ? "button" : undefined}
           tabIndex={hasKids ? 0 : undefined}
           onKeyDown={hasKids ? (e) => {
             if (e.key === "Enter" || e.key === " ") {
               e.preventDefault(); setOpen(!open);
             }
           } : undefined}>
        {hasKids ? <i className="tr-caret">{open ? "▾" : "▸"}</i>
                 : <i className="tr-leaf" />}
        <span className="tr-label">{label}</span>
        {meta && <span className="tr-meta">{meta}</span>}
        {count !== undefined && <b className="tr-count">{count}</b>}
      </div>
      {hasKids && open && <ul className="tr-kids">{children}</ul>}
    </li>
  );
}

/* ---- 1. templates: report type -> template -> blocks ------------------ */
export function TemplateTree({ data }) {
  if (!data?.report_types?.length) return <div className="adv-none">Nothing yet.</div>;
  return (
    <ul className="tr">
      {data.report_types.map((rt) => (
        <Node key={rt.report_type} label={rt.label}
              meta={rt.prescribed ? "prescribed" : ""}
              count={rt.templates.length}
              defaultOpen={rt.report_type === "quarterly_portfolio_review"}>
          {rt.templates.length === 0
            ? <li className="tr-empty">no templates yet — add one under Configuration</li>
            : rt.templates.map((t) => (
                <Node key={t.template_id} label={t.label}
                      meta={t.description} count={t.blocks.length}>
                  {t.blocks.map((b, i) => (
                    <li key={`${b}-${i}`} className="tr-node">
                      <div className="tr-row">
                        <i className="tr-leaf" />
                        <span className="tr-label mono">{b}</span>
                        <span className="tr-meta">{i + 1}</span>
                      </div>
                    </li>
                  ))}
                </Node>
              ))}
        </Node>
      ))}
    </ul>
  );
}

/* ---- 2. blocks: category -> block ------------------------------------ */
export function BlockTree({ data }) {
  if (!data?.categories?.length) return <div className="adv-none">Nothing yet.</div>;
  return (
    <ul className="tr">
      {data.categories.map((c) => (
        <Node key={c.category} label={c.category} count={c.blocks.length}
              defaultOpen={c.category === "headline"}>
          {c.blocks.map((b) => (
            <Node key={b.block} label={<span className="mono">{b.block}</span>}
                  meta={b.shows}
                  tone={b.kind === "chart" ? "chart" : ""} />
          ))}
        </Node>
      ))}
    </ul>
  );
}

/* ---- 3. preferences: client -> report type -> what was learned -------- */
export function PreferenceTree({ data }) {
  if (!data?.clients?.length) {
    return (
      <div className="adv-none">
        No client has generated a preference yet. They appear here as
        clients open reports, highlight sections and ask questions.
      </div>
    );
  }
  return (
    <ul className="tr">
      {data.clients.map((c) => (
        <Node key={c.client_id} label={c.name} meta={c.client_id}
              count={c.scopes.length}>
          {c.scopes.map((s) => (
            <Node key={s.scope} label={s.scope.replace(/_/g, " ")}
                  meta={`${s.signals} signal${s.signals === 1 ? "" : "s"}`}
                  tone={s.report_type ? "" : "wide"}>
              {Object.keys(s.moved).length === 0 && !s.stated.length
                ? <li className="tr-empty">nothing has moved off the population prior</li>
                : null}
              {Object.entries(s.moved).map(([dim, v]) => (
                <li key={dim} className="tr-node">
                  <div className="tr-row">
                    <i className="tr-leaf" />
                    <span className="tr-label">{dim.replace(/_/g, " ")}</span>
                    <i className="tr-bar"
                       style={{ width: `${Math.max(4, v * 60)}px`,
                                background: v > 0.5 ? "#047857" : "#b45309" }} />
                    <b className="tr-count">{v.toFixed(2)}</b>
                  </div>
                </li>
              ))}
              {s.stated.map((p, i) => (
                <li key={`said-${i}`} className="tr-node">
                  <div className="tr-row">
                    <i className="tr-leaf" />
                    <span className="tr-label">“{p.phrase}”</span>
                    <span className={`tr-tag ${p.actionable ? "ok" : "human"}`}>
                      {p.actionable ? p.aspect : `${p.aspect} · needs a human`}
                    </span>
                    {p.count > 1 && <b className="tr-count">×{p.count}</b>}
                  </div>
                </li>
              ))}
            </Node>
          ))}
        </Node>
      ))}
    </ul>
  );
}
