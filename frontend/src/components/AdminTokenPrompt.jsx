import { useState } from "react";
import "../styles/admin.css";

export default function AdminTokenPrompt({ title = "Admin access", onSave }) {
  const [token, setToken] = useState("");

  function saveToken(event) {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) return;
    localStorage.setItem("ape.admin_token", trimmed);
    onSave?.(trimmed);
  }

  return (
    <div className="app-page">
      <header className="app-header">
        <div className="app-header-row">
          <div className="app-brand">
            <span className="app-brand-name">APE</span>
            <span className="app-brand-dot">/</span>
            <span className="app-brand-page">{title}</span>
          </div>
        </div>
      </header>
      <main className="app-main">
        <form className="admin-token-panel" onSubmit={saveToken}>
          <label className="field-label" htmlFor="admin-token">Admin token</label>
          <div className="admin-token-row">
            <input
              id="admin-token"
              className="input"
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="current-password"
            />
            <button className="btn-primary" type="submit">Unlock</button>
          </div>
        </form>
      </main>
    </div>
  );
}
