import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useUrlState } from "../hooks/useUrlState.js";

/**
 * Every report layout an adviser can pick, shown as the document it
 * produces. Thumbnails are the real generator (the same path as
 * generation) rendering John Doe, a fictional demo client, so browsing
 * layouts never exposes a real portfolio.
 */

const DOC_WIDTH = 900;          // the width the document is laid out at
const renders = new Map();      // template id -> Promise<render>
let running = 0;
const queue = [];

// A handful of renders at a time, so eighty cards do not land at once.
function fetchRender(id) {
  const key = id;
  if (!renders.has(key)) {
    renders.set(key, new Promise((resolve, reject) => {
      queue.push(() => api.renderTemplate(id)
        .then(resolve, (e) => { renders.delete(key); reject(e); })
        .finally(() => { running--; pump(); }));
      pump();
    }));
  }
  return renders.get(key);
}
function pump() {
  while (running < 4 && queue.length) { running++; queue.shift()(); }
}

// Thumbnails show the top of the page only: no scrollbars, no clicks.
const THUMB_CSS = "<style>html,body{overflow:hidden!important}</style>";

function when(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function usageLine(u) {
  if (!u?.reports) return "Not used yet";
  return `Used for ${u.reports} report${u.reports === 1 ? "" : "s"}`
    + (u.clients ? ` · ${u.clients} client${u.clients === 1 ? "" : "s"}` : "");
}

function Thumb({ id, onReady }) {
  const box = useRef(null);
  const [visible, setVisible] = useState(false);
  const [doc, setDoc] = useState(null);
  const [err, setErr] = useState(false);
  const [scale, setScale] = useState(0.27);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); },
                                        { rootMargin: "300px" });
    io.observe(el);
    const ro = new ResizeObserver(([e]) => setScale(e.contentRect.width / DOC_WIDTH));
    ro.observe(el);
    return () => { io.disconnect(); ro.disconnect(); };
  }, []);

  useEffect(() => {
    if (!visible) return;
    let alive = true;
    setDoc(null); setErr(false);
    fetchRender(id)
      .then((r) => { if (alive) { setDoc(r); onReady?.(r); } })
      .catch(() => alive && setErr(true));
    return () => { alive = false; };
  }, [visible, id, onReady]);

  return (
    <div className="tg-thumb" ref={box} aria-hidden="true">
      {doc
        ? <iframe title="" tabIndex={-1} srcDoc={doc.html + THUMB_CSS}
                  style={{ width: DOC_WIDTH, height: DOC_WIDTH * 1.4, transform: `scale(${scale})` }} />
        : err
        ? <div className="tg-thumb-msg">Preview unavailable</div>
        : <div className="tg-skel"><i /><i /><i /><i /></div>}
    </div>
  );
}

function Card({ t, onOpen }) {
  return (
    <li>
      <button type="button" className="tg-card" onClick={() => onOpen(t.template_id)}
              aria-label={`${t.label}, ${t.report_type_label}. Open preview`}>
        <Thumb id={t.template_id} />
        <div className="tg-card-body">
          <div className="tg-card-top">
            <h3>{t.label}</h3>
            {t.prescribed && <span className="adv-pill warn">Prescribed</span>}
          </div>
          {t.description && <p className="tg-desc">{t.description}</p>}
          <div className="tg-meta">
            <span>{t.sections.length} section{t.sections.length === 1 ? "" : "s"}</span>
            <span className={t.usage?.reports ? "" : "tg-muted"}>{usageLine(t.usage)}</span>
          </div>
        </div>
      </button>
    </li>
  );
}

function Detail({ t, list, onClose, onMove, onUse }) {
  const [doc, setDoc] = useState(null);
  const [err, setErr] = useState("");
  const dialog = useRef(null);

  useEffect(() => {
    let alive = true;
    setDoc(null); setErr("");
    fetchRender(t.template_id)
      .then((r) => alive && setDoc(r)).catch((e) => alive && setErr(e.message));
    return () => { alive = false; };
  }, [t.template_id]);

  useEffect(() => {
    dialog.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight" && !/^(SELECT|INPUT|TEXTAREA)$/.test(e.target.tagName)) onMove(1);
      else if (e.key === "ArrowLeft" && !/^(SELECT|INPUT|TEXTAREA)$/.test(e.target.tagName)) onMove(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onMove]);

  const idx = list.findIndex((x) => x.template_id === t.template_id);
  const added = doc?.enforced_labels || [];

  return (
    <div className="tg-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="tg-dialog" role="dialog" aria-modal="true" aria-labelledby="tg-title"
           tabIndex={-1} ref={dialog}>
        <header className="tg-dhd">
          <div className="tg-dhd-title">
            <span className="tg-eyebrow">{t.report_type_label}</span>
            <h2 id="tg-title">{t.label}</h2>
          </div>
          <div className="tg-dhd-nav">
            <span className="tg-count">{idx + 1} of {list.length}</span>
            <button type="button" className="tg-icon" onClick={() => onMove(-1)}
                    aria-label="Previous template" disabled={idx <= 0}>‹</button>
            <button type="button" className="tg-icon" onClick={() => onMove(1)}
                    aria-label="Next template" disabled={idx >= list.length - 1}>›</button>
            <button type="button" className="tg-icon" onClick={onClose} aria-label="Close">✕</button>
          </div>
        </header>

        <div className="tg-dbody">
          <div className="tg-doc">
            {doc ? <iframe title={`${t.label} preview`} srcDoc={doc.html} />
              : err ? <div className="tg-thumb-msg">Could not render this template: {err}</div>
              : <div className="tg-thumb-msg">Rendering…</div>}
          </div>

          <aside className="tg-side">
            {t.description && <p className="tg-lede">{t.description}</p>}

            <div className="tg-actions">
              <button type="button" className="adv-btn" onClick={() => onUse(t)}>Use this template</button>
              <Link className="adv-btn ghost" to={`/admin?tab=templates&edit=${encodeURIComponent(t.template_id)}`}>
                Edit in Configuration</Link>
            </div>

            <p className="tg-demo">
              Shown with <b>{doc?.client_name || "John Doe"}</b>, a fictional demo client.
              Real clients' reports use their own figures.
            </p>

            <dl className="tg-facts">
              <div><dt>Sections</dt><dd>{t.sections.length}</dd></div>
              <div><dt>Used for</dt>
                <dd>{t.usage?.reports ? `${t.usage.reports} reports` : "Not used yet"}</dd></div>
              <div><dt>Last used</dt><dd>{t.usage?.last_used ? when(t.usage.last_used) : "–"}</dd></div>
            </dl>

            <section>
              <h3 className="tg-h">Sections, in reading order</h3>
              <ol className="tg-sections">
                {t.sections.map((s, i) => <li key={`${s.block}-${i}`}>{s.label}</li>)}
              </ol>
              {added.length > 0 && (
                <p className="tg-note">Always added for compliance or completeness: {added.join(", ")}.</p>)}
            </section>

            {t.brief && (
              <section>
                <h3 className="tg-h">Writing brief</h3>
                <p className="tg-brief">{t.brief}</p>
              </section>)}

            {t.prescribed && (
              <p className="tg-note">This report type is prescribed: its wording and order are fixed and are
                not personalised.</p>)}
          </aside>
        </div>
      </div>
    </div>
  );
}

export default function TemplateGallery({ onUse }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [rtype, setRtype] = useUrlState("rtype", "");
  const [q, setQ] = useUrlState("q", "");
  const [open, setOpen] = useUrlState("open", "");

  useEffect(() => {
    api.templateGallery().then(setData).catch((e) => setErr(e.message));
  }, []);

  const list = useMemo(() => {
    if (!data) return [];
    const needle = q.trim().toLowerCase();
    return data.templates.filter((t) =>
      (!rtype || t.report_type === rtype)
      && (!needle || [t.label, t.description, t.report_type_label, ...t.sections.map((s) => s.label)]
            .join(" ").toLowerCase().includes(needle)));
  }, [data, rtype, q]);

  const groups = useMemo(() => {
    const m = new Map();
    for (const t of list) {
      if (!m.has(t.report_type)) m.set(t.report_type, { label: t.report_type_label, prescribed: t.prescribed, items: [] });
      m.get(t.report_type).items.push(t);
    }
    return [...m.entries()];
  }, [list]);

  const current = list.find((t) => t.template_id === open)
    || data?.templates.find((t) => t.template_id === open);
  const move = useCallback((d) => {
    const i = list.findIndex((t) => t.template_id === open);
    const next = list[i + d];
    if (next) setOpen(next.template_id);
  }, [list, open, setOpen]);
  const close = useCallback(() => setOpen(""), [setOpen]);

  if (err) return <section className="adv-panel"><div className="adv-none">Could not load templates: {err}</div></section>;
  if (!data) return <section className="adv-panel"><div className="adv-none">Loading templates…</div></section>;

  const used = data.templates.filter((t) => t.usage?.reports).length;

  return (
    <div className="tg">
      <section className="adv-panel tg-bar" aria-label="Filter templates">
        <input className="adv-search tg-search" type="search" placeholder="Search by name or section…"
               value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search templates" />
        <select className="tg-select" value={rtype} onChange={(e) => setRtype(e.target.value)}
                aria-label="Report type">
          <option value="">All report types ({data.templates.length})</option>
          {data.report_types.filter((r) => r.count).map((r) => (
            <option key={r.report_type} value={r.report_type}>{r.label} ({r.count})</option>))}
        </select>
        <p className="tg-summary">
          {list.length === data.templates.length
            ? `${data.templates.length} templates across ${groups.length} report types · ${used} in use`
            : `Showing ${list.length} of ${data.templates.length} templates`}
          {" · Previews use John Doe, a fictional demo client"}
        </p>
      </section>

      {!list.length && (
        <section className="adv-panel"><div className="adv-none">
          No templates match “{q}”. <button type="button" className="tg-link" onClick={() => { setQ(""); setRtype(""); }}>
            Clear filters</button></div></section>)}

      {groups.map(([rt, g]) => (
        <section key={rt} className="tg-group" aria-labelledby={`tg-${rt}`}>
          <header className="tg-group-hd">
            <h2 id={`tg-${rt}`}>{g.label}</h2>
            <span className="tg-count">{g.items.length} template{g.items.length === 1 ? "" : "s"}</span>
          </header>
          <ul className="tg-grid">
            {g.items.map((t) => <Card key={t.template_id} t={t} onOpen={setOpen} />)}
          </ul>
        </section>
      ))}

      {current && (
        <Detail t={current} list={list} onClose={close} onMove={move}
                onUse={(t) => { setOpen(""); onUse(t); }} />)}
    </div>
  );
}
