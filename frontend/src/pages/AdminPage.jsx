import { useState } from "react";
import { Link } from "react-router-dom";
import Toast from "../components/Toast.jsx";
import ReportTypesTab from "./admin/ReportTypesTab.jsx";
import TemplatesTab   from "./admin/TemplatesTab.jsx";
import ThompsonTab    from "./admin/ThompsonTab.jsx";
import D2StateTab    from "./admin/D2StateTab.jsx";
import D1StateTab    from "./admin/D1StateTab.jsx";
import AuditTab       from "./admin/AuditTab.jsx";
import "../styles/app-shell.css";
import "../styles/admin.css";

const TABS = [
  { id: "reporttypes",  label: "Report Types" },
  { id: "templates",    label: "Templates" },
  { id: "thompson",     label: "Selection (Thompson)" },
  { id: "d1state",      label: "Templates (D1)" },
  { id: "d2",           label: "Answers (D2)" },
  { id: "audit",        label: "Audit Log" },
];

export default function AdminPage() {
  const [active, setActive] = useState("reporttypes");
  const [toast, setToast]   = useState({ msg: null, kind: "" });

  function notify(msg, kind = "ok") { setToast({ msg, kind }); }

  return (
    <div className="app-page">
      <header className="app-header">
        <div className="app-header-row">
          <div className="app-brand">
            <span className="app-brand-name">APE</span>
            <span className="app-brand-dot">/</span>
            <span className="app-brand-page">Configuration</span>
          </div>
          <div className="app-actions">
            <Link to="/"          className="app-link">Advisor</Link>
          </div>
        </div>
        <div className="app-header-row app-header-row-tabs">
          <nav className="app-tabs" aria-label="Configuration sections">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`app-tab ${active === t.id ? "active" : ""}`}
                onClick={() => setActive(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="app-main">
        {active === "reporttypes"  && <ReportTypesTab notify={notify} />}
        {active === "templates"    && <TemplatesTab   notify={notify} />}
        {active === "thompson"     && <ThompsonTab    notify={notify} />}
        {active === "d1state"      && <D1StateTab     notify={notify} />}
        {active === "d2"           && <D2StateTab     notify={notify} />}
        {active === "audit"        && <AuditTab       notify={notify} />}
      </main>

      <Toast
        message={toast.msg}
        kind={toast.kind}
        onClose={() => setToast({ msg: null, kind: "" })}
      />
    </div>
  );
}
