import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import Toast from "../components/Toast.jsx";
import IntentsTab     from "./admin/IntentsTab.jsx";
import StrategiesTab  from "./admin/StrategiesTab.jsx";
import InstructionsTab from "./admin/InstructionsTab.jsx";
import PoliciesTab    from "./admin/PoliciesTab.jsx";
import OffersTab     from "./admin/OffersTab.jsx";
import SignalRulesTab from "./admin/SignalRulesTab.jsx";
import RewardScaleTab from "./admin/RewardScaleTab.jsx";
import AuditTab       from "./admin/AuditTab.jsx";
import "../styles/admin.css";

const TABS = [
  { id: "intents",      label: "Intents" },
  { id: "strategies",   label: "Strategies" },
  { id: "instructions", label: "Instructions" },
  { id: "policies",     label: "Policies" },
  { id: "offers",       label: "Outreach" },
  { id: "signals",      label: "Signal Routing" },
  { id: "rewards",      label: "Reward Scale" },
  { id: "audit",        label: "Audit Log" },
];

export default function AdminPage() {
  const [active, setActive] = useState("intents");
  const [toast, setToast]   = useState({ msg: null, kind: "" });

  function notify(msg, kind = "ok") { setToast({ msg, kind }); }

  return (
    <div className="admin-page">
      <header className="admin-header">
        <div className="admin-header-row">
          <div>
            <h1>Configuration</h1>
            <div className="admin-sub">Admin-managed settings for the APE engine</div>
          </div>
          <nav className="admin-nav">
            <Link to="/" className="admin-back">← Back to chat</Link>
            <Link to="/analytics" className="admin-back">Analytics</Link>
          </nav>
        </div>
        <div className="admin-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`admin-tab ${active === t.id ? "active" : ""}`}
              onClick={() => setActive(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      <main className="admin-main">
        {active === "intents"      && <IntentsTab     notify={notify} />}
        {active === "strategies"   && <StrategiesTab  notify={notify} />}
        {active === "instructions" && <InstructionsTab notify={notify} />}
        {active === "policies"     && <PoliciesTab    notify={notify} />}
        {active === "offers"       && <OffersTab      notify={notify} />}
        {active === "signals"      && <SignalRulesTab notify={notify} />}
        {active === "rewards"      && <RewardScaleTab notify={notify} />}
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
