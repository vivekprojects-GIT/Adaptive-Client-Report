import { Link } from "react-router-dom";
import "../styles/advisor.css";

/**
 * The navigation rail shared by the advisor console and Configuration.
 *
 * The advisor screen switches views in place, so it passes `onSelect`.
 * Configuration is a separate route, so there the same items link back to
 * the advisor screen and name the view to open — one rail, one place to
 * look, whichever page the advisor is on.
 */
export const NAV = [
  ["clients", "Clients"], ["reports", "Reports"],
  ["segments", "Segments"], ["registry", "Registries"],
];

// Line icons drawn on one 16px grid so they read as a set. Decorative:
// the label beside each one carries the meaning.
const ICON_PATHS = {
  clients:  "M5.5 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1 14c0-2.5 2-4 4.5-4s4.5 1.5 4.5 4M11 7a2 2 0 1 0 0-4M12 10c1.8.3 3 1.6 3 4",
  reports:  "M3.5 1.5h6l3 3v10h-9zM9.5 1.5v3h3M5.5 8h5M5.5 10.5h5M5.5 13h3",
  segments: "M8 1.5A6.5 6.5 0 1 0 14.5 8H8zM10 1.8A6.5 6.5 0 0 1 14.2 6H10z",
  registry: "M8 1.5 14.5 5 8 8.5 1.5 5zM1.5 8 8 11.5 14.5 8M1.5 11 8 14.5 14.5 11",
  config:   "M2 4h7M12 4h2M2 12h2M7 12h7M10.5 2.5v3M5.5 10.5v3",
};

function NavIcon({ name }) {
  return (
    <svg className="adv-nav-ic" viewBox="0 0 16 16" width="16" height="16"
         aria-hidden="true" fill="none" stroke="currentColor"
         strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

export default function AppRail({ active, onSelect }) {
  return (
    <aside className="adv-nav">
      <div className="adv-brand">
        <img className="adv-logo-img" src="/static/brand/capgeminiWhite.svg"
             alt="Capgemini" width="118" height="27" />
        <span>Adaptive Client Reporting</span>
      </div>
      <nav aria-label="Main">
        {NAV.map(([id, label]) => {
          const cls = `adv-nav-item ${active === id ? "on" : ""}`;
          const cur = active === id ? "page" : undefined;
          return onSelect
            ? <button key={id} className={cls} aria-current={cur}
                      onClick={() => onSelect(id)}>
                <NavIcon name={id} />{label}
              </button>
            : <Link key={id} className={cls} to="/" state={{ view: id }}>
                <NavIcon name={id} />{label}
              </Link>;
        })}
        {active === "config"
          ? <span className="adv-nav-item on" aria-current="page">
              <NavIcon name="config" />Configuration
            </span>
          : <Link className="adv-nav-item" to="/admin">
              <NavIcon name="config" />Configuration
            </Link>}
      </nav>
      <div className="adv-user">
        <span className="adv-avatar" aria-hidden="true">AA</span>
        <div><b>Advisor Admin</b><span>admin@wealth.com</span></div>
      </div>
    </aside>
  );
}
