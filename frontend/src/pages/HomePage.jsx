import { useState } from "react";
import { computeStats } from "../repoUtils";
import { API_URL, fetchJson } from "../api";

// Command Center: analyze a repo (zip or GitHub), then jump into the
// workspace. Recent persisted projects are listed for quick reopening.
export function HomePage({ onAnalyzed, onNavigate, aiStatus, repoList, onOpenRepo }) {
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyzeZip() {
    if (!file) return;

    setLoading(true);
    setError("");
    aiStatus("loading", "Analyzing your ZIP…");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const data = await fetchJson(`${API_URL}/analyze/zip`, {
        method: "POST",
        body: formData,
      });

      onAnalyzed(data, computeStats(data));
      aiStatus("success", `${data.name} mapped!`);
      onNavigate("explorer");
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function analyzeGithub() {
    if (!githubUrl) return;

    setLoading(true);
    setError("");
    aiStatus("loading", "Cloning from GitHub…");

    try {
      const data = await fetchJson(`${API_URL}/analyze/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: githubUrl }),
      });

      onAnalyzed(data, computeStats(data));
      aiStatus("success", `${data.name} mapped!`);
      onNavigate("explorer");
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page home-page">
      <div className="home-hero">
        <p className="hero-kicker">
          <span className="kicker-index">01</span> Command Center — local analysis
        </p>
        <h2 className="home-title">Take the code apart.</h2>
        <p className="home-subtitle">
          Point CodeLens at a repository. It maps the architecture, indexes
          every function and class, and lets you interrogate the code with an
          evidence-grounded AI.
        </p>
      </div>

      <div className="home-cards">
        <div className="home-card">
          <p className="entry-label">A — Upload</p>
          <h3>ZIP Archive</h3>
          <p>Drop a <code>.zip</code> of any project. Parsed locally, nothing leaves your machine except the model call.</p>
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <button onClick={analyzeZip} disabled={loading || !file}>
            {loading ? "Analyzing…" : "Analyze ZIP"}
          </button>
          {file && <span className="home-file-name">{file.name}</span>}
        </div>

        <div className="home-card">
          <p className="entry-label">B — Remote</p>
          <h3>GitHub URL</h3>
          <p>Paste a public repo URL. CodeLens fetches the default branch archive.</p>
          <input
            type="text"
            placeholder="https://github.com/user/repo"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
          />
          <button onClick={analyzeGithub} disabled={loading || !githubUrl}>
            {loading ? "Cloning…" : "Analyze GitHub"}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {repoList.length > 0 && (
        <div className="home-recent">
          <h3>Recent projects</h3>
          <div className="recent-list">
            {repoList.slice(0, 5).map((entry, index) => (
              <div
                key={entry.repository_id}
                className={`recent-item ${entry.available ? "" : "missing"}`}
              >
                <span className="recent-index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="recent-info">
                  <span className="recent-name">{entry.name}</span>
                  {!entry.available && (
                    <span className="recent-badge">Files missing</span>
                  )}
                </div>
                <span aria-hidden="true" />
                <button
                  className="recent-open"
                  disabled={!entry.available}
                  onClick={() => onOpenRepo(entry.repository_id)}
                >
                  Open
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="home-hint">
        {repoList.length > 0
          ? "Switch, reopen, or remove projects in "
          : "Analyzed a repo before? "}
        <button className="link-button" onClick={() => onNavigate("repositories")}>
          Repositories
        </button>
        {" "}— workspaces persist across restarts. Or go straight to{" "}
        <button className="link-button" onClick={() => onNavigate("ask")}>
          Ask CodeLens
        </button>
        .
      </div>
    </div>
  );
}
