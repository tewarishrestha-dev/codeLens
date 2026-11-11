import { useEffect, useState } from "react";
import { API_URL, fetchJson, getStoredLlmConfig, saveStoredLlmConfig } from "../api";

// Settings: backend health/model info, LLM cloud provider + display prefs.
export function SettingsPage({ aiStatus }) {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [reducedMotion, setReducedMotion] = useState(false);

  const initialLlm = getStoredLlmConfig();
  const [provider, setProvider] = useState(initialLlm.provider || "default");
  const [apiKey, setApiKey] = useState(initialLlm.apiKey || "");
  const [model, setModel] = useState(initialLlm.model || "");
  const [savedFeedback, setSavedFeedback] = useState("");

  useEffect(() => {
    fetchJson(`${API_URL}/health`)
      .then(setHealth)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("reduce-motion", reducedMotion);
  }, [reducedMotion]);

  function handleSaveLlm(e) {
    e.preventDefault();
    saveStoredLlmConfig({
      provider: provider === "default" ? "" : provider,
      apiKey: apiKey.trim(),
      model: model.trim(),
    });
    setSavedFeedback("Settings saved successfully!");
    aiStatus("success", "AI model preferences updated.");
    setTimeout(() => setSavedFeedback(""), 3000);
  }

  function handleResetLlm() {
    saveStoredLlmConfig({ provider: "", apiKey: "", model: "" });
    setProvider("default");
    setApiKey("");
    setModel("");
    setSavedFeedback("Reset to backend defaults.");
    setTimeout(() => setSavedFeedback(""), 3000);
  }

  return (
    <div className="page settings-page">
      <div className="page-header">
        <p className="page-kicker">
          <span className="kicker-index">05</span> System
        </p>
        <h2>Settings</h2>
        <p>Runtime status, AI model provider, and display preferences.</p>
      </div>

      <div className="settings-section">
        <h3>AI Model Provider</h3>
        <p className="settings-note">
          Configure an AI provider for code analysis and Q&amp;A. For cloud deployments
          (e.g. Render), providing a free Google Gemini or Groq API key allows CodeLens to answer
          without requiring local Ollama.
        </p>

        <form onSubmit={handleSaveLlm} className="llm-config-form">
          <div className="form-group">
            <label htmlFor="llm-provider">Provider</label>
            <select
              id="llm-provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="settings-select"
            >
              <option value="default">Backend Default (Ollama / Server Env)</option>
              <option value="gemini">Google Gemini (Recommended for Cloud)</option>
              <option value="groq">Groq (Ultra-fast inference)</option>
              <option value="openai">OpenAI / Compatible API</option>
            </select>
          </div>

          {provider !== "default" && (
            <>
              <div className="form-group">
                <label htmlFor="llm-key">API Key</label>
                <input
                  id="llm-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    provider === "gemini"
                      ? "AIzaSy..."
                      : provider === "groq"
                      ? "gsk_..."
                      : "sk-..."
                  }
                  className="settings-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="llm-model">Model Name (optional)</label>
                <input
                  id="llm-model"
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder={
                    provider === "gemini"
                      ? "gemini-1.5-flash (default)"
                      : provider === "groq"
                      ? "llama-3.3-70b-versatile (default)"
                      : "gpt-4o-mini (default)"
                  }
                  className="settings-input"
                />
              </div>
            </>
          )}

          <div className="form-actions">
            <button type="submit" className="button-primary">
              Save AI Settings
            </button>
            {provider !== "default" && (
              <button
                type="button"
                className="button-secondary"
                onClick={handleResetLlm}
              >
                Reset to Default
              </button>
            )}
            {savedFeedback && (
              <span className="save-feedback">{savedFeedback}</span>
            )}
          </div>
        </form>
      </div>

      <div className="settings-section">
        <h3>Backend Health</h3>
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
            {health.llm && (
              <>
                <li>
                  <span>Active Server LLM</span>
                  <span className="settings-value">{health.llm.provider}</span>
                </li>
                <li>
                  <span>Ollama Base URL</span>
                  <span className="settings-value">{health.llm.ollama_base_url}</span>
                </li>
              </>
            )}
          </ul>
        ) : (
          !error && <p>Checking backend…</p>
        )}
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
        <h3>About CodeLens</h3>
        <p className="settings-note">
          CodeLens maps a repository&rsquo;s architecture, indexes symbols across
          Python and JavaScript/TypeScript, and answers questions with
          evidence-grounded responses.
        </p>
      </div>
    </div>
  );
}
