import { useState } from "react";
import { computeStats } from "../repoUtils";
import { API_URL, fetchJson } from "../api";

const DEMO_REPOS = [
  { name: "Pallets / Click", url: "https://github.com/pallets/click", badge: "Python" },
  { name: "Express / Router", url: "https://github.com/pillarjs/router", badge: "JavaScript" },
];

// Command Center: analyze a repo (zip, GitHub, or Demo), then jump into the
// workspace. Recent persisted projects are listed for quick reopening.
export function HomePage({ onAnalyzed, onNavigate, aiStatus, repoList, onOpenRepo }) {
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  async function analyzeZip() {
    if (!file) return;

    setLoading(true);
    setLoadingStep("Uploading and parsing ZIP archive…");
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
      setLoadingStep("");
    }
  }

  async function analyzeGithub(targetUrl) {
    const urlToUse = targetUrl || githubUrl;
    if (!urlToUse) return;

    setLoading(true);
    setLoadingStep("Cloning repository and analyzing code graph…");
    setError("");
    aiStatus("loading", `Analyzing ${urlToUse}…`);

    try {
      const data = await fetchJson(`${API_URL}/analyze/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlToUse }),
      });

      onAnalyzed(data, computeStats(data));
      aiStatus("success", `${data.name} mapped!`);
      onNavigate("explorer");
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Analysis failed.");
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0];
      if (dropped.name.endsWith(".zip")) {
        setFile(dropped);
      } else {
        setError("Please drop a valid .zip archive.");
      }
    }
  }

  return (
    <div className="page home-page">
      <div className="home-hero">
        <p className="hero-kicker">
          <span className="kicker-index">01</span> Command Center — codebase intelligence
        </p>
        <h2 className="home-title">Take the code apart.</h2>
        <p className="home-subtitle">
          Point CodeLens at a repository. It maps the architecture, indexes
          functions and classes across Python and JavaScript/TypeScript, and lets you interrogate the code with an
          evidence-grounded AI.
        </p>
      </div>

      <div className="home-cards">
        <div
          className={`home-card ${isDragging ? "drag-active" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <p className="entry-label">A — Upload</p>
          <h3>ZIP Archive</h3>
          <p>Drop a <code>.zip</code> of any project or browse your local filesystem.</p>
          <input
            type="file"
            accept=".zip"
            id="zip-upload"
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
          <p>Paste a public repository URL to fetch and map the codebase.</p>
          <input
            type="text"
            placeholder="https://github.com/user/repo"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            disabled={loading}
          />
          <button onClick={() => analyzeGithub()} disabled={loading || !githubUrl}>
            {loading ? "Cloning…" : "Analyze GitHub"}
          </button>
        </div>

        <div className="home-card demo-card">
          <p className="entry-label">C — Quick Demo</p>
          <h3>Try Sample Repos</h3>
          <p>Instant 1-click exploration without needing to upload files.</p>
          <div className="demo-buttons">
            {DEMO_REPOS.map((demo) => (
              <button
                key={demo.name}
                className="demo-button"
                onClick={() => {
                  setGithubUrl(demo.url);
                  analyzeGithub(demo.url);
                }}
                disabled={loading}
              >
                <span>{demo.name}</span>
                <span className="demo-badge">{demo.badge}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Full-Width Workspace Intelligence & Engine Status Panel */}
      <div className="home-intelligence-grid">
        <div className="intel-card glass-panel">
          <div className="intel-header">
            <span className="intel-dot" />
            <h4>AST INGESTION ENGINE</h4>
          </div>
          <div className="intel-metric">v2.0 ACTIVE</div>
          <p className="intel-desc">
            Direct Python AST + JavaScript/TypeScript tokenizer parsing functions, classes, calls &amp; dependencies without third-party CLI requirements.
          </p>
          <div className="intel-tags">
            <span className="intel-tag">.py</span>
            <span className="intel-tag">.js</span>
            <span className="intel-tag">.jsx</span>
            <span className="intel-tag">.ts</span>
            <span className="intel-tag">.tsx</span>
          </div>
        </div>

        <div className="intel-card glass-panel">
          <div className="intel-header">
            <span className="intel-dot dot-cyan" />
            <h4>EXECUTION FLOW RESOLVER</h4>
          </div>
          <div className="intel-metric">GRAPH STUDIO</div>
          <p className="intel-desc">
            Traces entry-point call chains, resolves ambiguous method candidates across files, and displays animated interactive dependency flows.
          </p>
          <div className="intel-tags">
            <span className="intel-tag">Call Graphs</span>
            <span className="intel-tag">Forward &amp; Reverse</span>
            <span className="intel-tag">Dagre Layout</span>
          </div>
        </div>

        <div className="intel-card glass-panel">
          <div className="intel-header">
            <span className="intel-dot dot-purple" />
            <h4>EVIDENCE CITATION ENGINE</h4>
          </div>
          <div className="intel-metric">STRICT GROUNDING</div>
          <p className="intel-desc">
            Every AI statement is validated against extracted code blocks. Claims with unverifiable line citations are demoted into unverified notes.
          </p>
          <div className="intel-tags">
            <span className="intel-tag">[file:line]</span>
            <span className="intel-tag">Multi-LLM</span>
            <span className="intel-tag">Zero Guessing</span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-banner">
          <span className="spinner-dot" />
          <span>{loadingStep || "Analyzing codebase… this takes a few seconds"}</span>
        </div>
      )}

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
