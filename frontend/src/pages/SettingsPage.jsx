import { useEffect, useState } from "react";
import { API_URL, fetchJson } from "../api";

// Settings: backend health/model info + display prefs (session-only).
export function SettingsPage({ aiStatus }) {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    fetchJson(`${API_URL}/health`)
      .then(setHealth)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("reduce-motion", reducedMotion);
  }, [reducedMotion]);

  return (
    <div className="page settings-page">
      <div className="page-header">
        <p className="page-kicker">
          <span className="kicker-index">05</span> System
        </p>
        <h2>Settings</h2>
        <p>Runtime status and display preferences.</p>
      </div>

      <div className="settings-section">
        <h3>Backend</h3>
        {error && <div className="error">{error}</div>}
        {health ? (
          <ul className="settings-list">
            <li>
              <span>Status</span>
              <span className="settings-value ok">{health.status}</span>
            </li>
            <li>
              <span>API endpoint</span>
              <span className="settings-value">{API_URL}</span>
            </li>
          </ul>
        ) : (
          !error && <p>Checking backend…</p>
        )}
        <p className="settings-note">
          Model: <code>ollama/qwen2.5-coder:3b</code> (configured on the backend;
          not changeable from the UI).
        </p>
      </div>

      <div className="settings-section">
        <h3>Display</h3>
        <label className="settings-toggle">
          <input
            type="checkbox"
            checked={reducedMotion}
            onChange={(e) => {
              setReducedMotion(e.target.checked);
              aiStatus("idle", e.target.checked ? "Motion reduced." : "");
            }}
          />
          <span>Reduce motion (disable companion float &amp; transitions)</span>
        </label>
      </div>

      <div className="settings-section">
        <h3>About</h3>
        <p className="settings-note">
          CodeLens maps a repository&rsquo;s architecture, indexes symbols, and
          answers questions with evidence-grounded responses. Unsupported model
          claims are demoted rather than asserted.
        </p>
      </div>
    </div>
  );
}
