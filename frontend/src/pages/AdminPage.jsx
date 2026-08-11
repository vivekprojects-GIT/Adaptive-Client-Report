import { useState } from "react";
import { Link } from "react-router-dom";
import Toast from "../components/Toast.jsx";
import IntentsTab     from "./admin/IntentsTab.jsx";
import StrategiesTab  from "./admin/StrategiesTab.jsx";
import InstructionsTab from "./admin/InstructionsTab.jsx";
import PoliciesTab    from "./admin/PoliciesTab.jsx";
import ReportTypesTab from "./admin/ReportTypesTab.jsx";
import TemplatesTab   from "./admin/TemplatesTab.jsx";
import SignalRulesTab from "./admin/SignalRulesTab.jsx";
import RewardScaleTab from "./admin/RewardScaleTab.jsx";
import UcbConfigTab   from "./admin/UcbConfigTab.jsx";
import ResearchTab    from "./admin/ResearchTab.jsx";
import BanditStateTab from "./admin/BanditStateTab.jsx";
import AuditTab       from "./admin/AuditTab.jsx";
import "../styles/app-shell.css";
import "../styles/admin.css";
// Shared styles for quality panels (also rendered on the analytics page).
import "../styles/quality.css";

const TABS = [
  { id: "intents",      label: "Intents" },
  { id: "strategies",   label: "Strategies" },
  { id: "instructions", label: "Instructions" },
  { id: "policies",     label: "Policies" },
  { id: "reporttypes",  label: "Report Types" },
  { id: "templates",    label: "Templates" },
  { id: "signals",      label: "Signal Routing" },
  { id: "rewards",      label: "Reward Scale" },
  { id: "ucb",          label: "Selection Score" },
  { id: "bandit",       label: "Bandit State" },
  { id: "research",     label: "Research" },
  { id: "audit",        label: "Audit Log" },
];

export default function AdminPage() {
  const [active, setActive] = useState("intents");
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
            <Link to="/"          className="app-link">Reports</Link>
            <Link to="/analytics" className="app-link">Analytics</Link>
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
        {active === "intents"      && <IntentsTab     notify={notify} />}
        {active === "strategies"   && <StrategiesTab  notify={notify} />}
        {active === "instructions" && <InstructionsTab notify={notify} />}
        {active === "policies"     && <PoliciesTab    notify={notify} />}
        {active === "reporttypes"  && <ReportTypesTab notify={notify} />}
        {active === "templates"    && <TemplatesTab   notify={notify} />}
        {active === "signals"      && <SignalRulesTab notify={notify} />}
        {active === "rewards"      && <RewardScaleTab notify={notify} />}
        {active === "ucb"          && <UcbConfigTab   notify={notify} />}
        {active === "bandit"       && <BanditStateTab notify={notify} />}
        {active === "research"     && <ResearchTab />}
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
