import { useState } from "react";
import Toast from "../components/Toast.jsx";
import AppRail from "../components/AppRail.jsx";
import ReportTypesTab from "./admin/ReportTypesTab.jsx";
import TemplatesTab   from "./admin/TemplatesTab.jsx";
import SelectionTab   from "./admin/SelectionTab.jsx";
import D2StateTab    from "./admin/D2StateTab.jsx";
import AuditTab       from "./admin/AuditTab.jsx";
import "../styles/app-shell.css";
import "../styles/admin.css";

const TABS = [
  { id: "reporttypes",  label: "Report types" },
  { id: "templates",    label: "Templates" },
  { id: "d2",           label: "Answer learning" },
  { id: "selection",    label: "Learning settings" },
  { id: "audit",        label: "Audit log" },
];

export default function AdminPage() {
  const [active, setActive] = useState("reporttypes");
  const [toast, setToast]   = useState({ msg: null, kind: "" });

  function notify(msg, kind = "ok") { setToast({ msg, kind }); }

  return (
    <div className="adv">
      <AppRail active="config" />
      <div className="app-page">
      <header className="adv-head adm-head">
        <div className="adv-head-title">
          <h1>Configuration</h1>
          <p>Report types, templates and how the system learns from clients.</p>
        </div>
      </header>
      <nav className="app-tabs adm-tabs" aria-label="Configuration sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`app-tab ${active === t.id ? "active" : ""}`}
            aria-current={active === t.id ? "page" : undefined}
            onClick={() => setActive(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {active === "reporttypes"  && <ReportTypesTab notify={notify} />}
        {active === "templates"    && <TemplatesTab   notify={notify} />}
        {active === "selection"    && <SelectionTab   notify={notify} />}
        {active === "d2"           && <D2StateTab     notify={notify} />}
        {active === "audit"        && <AuditTab       notify={notify} />}
      </main>

      <Toast
        message={toast.msg}
        kind={toast.kind}
        onClose={() => setToast({ msg: null, kind: "" })}
      />
      </div>
    </div>
  );
}
