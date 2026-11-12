import { useState } from "react";

export function LandingPage({ onEnterApp, onOpenAuth, user }) {
  return (
    <div className="landing-container">
      {/* Ambient background glows */}
      <div className="ambient-spotlight spotlight-top" aria-hidden="true" />
      <div className="ambient-spotlight spotlight-bottom" aria-hidden="true" />

      {/* Floating Glass Navigation */}
      <header className="landing-nav glass-nav">
        <div className="landing-brand">
          <span className="brand-dot-glow" />
          <span className="landing-logo-text">CODELENS</span>
        </div>

        <div className="landing-nav-pills">
          <span className="nav-pill-tag">AST Mapping</span>
          <span className="nav-pill-tag">Call Graph</span>
          <span className="nav-pill-tag">Evidence Citations</span>
        </div>

        <div className="landing-nav-action">
          {user ? (
            <button className="nav-pill-btn primary" onClick={onEnterApp}>
              <span>Enter Workspace</span>
              <span className="btn-arrow">→</span>
            </button>
          ) : (
            <button className="nav-pill-btn" onClick={onOpenAuth}>
              <span>Sign In</span>
            </button>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="landing-hero">
        <div className="hero-kicker-pill">
          <span className="kicker-bullet">✦</span>
          <span>01 · AI-POWERED CODEBASE INTELLIGENCE</span>
        </div>

        <div className="hero-branding">
          <h1 className="hero-display-brand">CODELENS</h1>
        </div>

        <div className="hero-motto">
          <span className="motto-line-1">Beyond the syntax.</span>
          <span className="motto-line-2">Inside the logic.</span>
        </div>

        <p className="hero-description">
          Take any repository apart. CodeLens maps architecture, traces
          cross-file execution flows across Python &amp; JavaScript, and
          interrogates the code with evidence-grounded AI citations.
        </p>

        <div className="hero-cta-group">
          <button
            type="button"
            className="hero-btn-primary"
            onClick={user ? onEnterApp : onOpenAuth}
          >
            <span>{user ? "Open Workspace" : "Get Started"}</span>
            <span className="btn-arrow">→</span>
          </button>
          <button
            type="button"
            className="hero-btn-secondary"
            onClick={onEnterApp}
          >
            <span className="sparkle-icon">⚡</span>
            <span>Try Live Demo</span>
          </button>
        </div>

        {/* Cinematic Workspace Preview Card */}
        <div className="hero-preview-frame glass-panel">
          <div className="preview-window-bar">
            <div className="window-dots">
              <span className="dot dot-red" />
              <span className="dot dot-yellow" />
              <span className="dot dot-green" />
            </div>
            <div className="window-title">codelens-workspace // architecture.flow</div>
            <span className="window-badge">ENGINE v2.0 ACTIVE</span>
          </div>

          <div className="preview-canvas-content">
            <div className="preview-metric-row">
              <div className="preview-metric">
                <span className="metric-val">100%</span>
                <span className="metric-lbl">Grounded Answers</span>
              </div>
              <div className="preview-metric">
                <span className="metric-val">Py + JS</span>
                <span className="metric-lbl">Multi-Language AST</span>
              </div>
              <div className="preview-metric">
                <span className="metric-val">0.3s</span>
                <span className="metric-lbl">Indexing Speed</span>
              </div>
            </div>

            <div className="preview-graph-flow">
              <div className="flow-step">
                <span className="flow-badge">ENTRY</span>
                <code>main.py : run()</code>
              </div>
              <span className="flow-connector">→</span>
              <div className="flow-step">
                <span className="flow-badge">CALL TARGET</span>
                <code>context_builder.py : build()</code>
              </div>
              <span className="flow-connector">→</span>
              <div className="flow-step active-flow">
                <span className="flow-badge">VERIFIED [click.core:2052]</span>
                <code>llm_service.py : ask()</code>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Grid */}
        <section className="landing-features-grid">
          <div className="feature-card glass-panel">
            <div className="feature-kicker">CAPABILITY 01</div>
            <h3>Cross-File Call Chains</h3>
            <p>
              Follow execution from entry points deep into ambiguous method targets
              with full resolution and graph visualization.
            </p>
          </div>

          <div className="feature-card glass-panel">
            <div className="feature-kicker">CAPABILITY 02</div>
            <h3>Polyglot AST Ingestion</h3>
            <p>
              Parses imports, functions, classes, and calls across Python, JavaScript,
              and TypeScript without external dependencies.
            </p>
          </div>

          <div className="feature-card glass-panel">
            <div className="feature-kicker">CAPABILITY 03</div>
            <h3>Honest Evidence Citations</h3>
            <p>
              Every claim is grounded with <code>[file:line]</code> citations verified against
              retrieved source blocks. Unsupported claims are demoted.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-left">
          <span>CODELENS &copy; {new Date().getFullYear()}</span>
          <span className="footer-sep">·</span>
          <span className="footer-motto">Beyond the syntax. Inside the logic.</span>
        </div>
        <div className="footer-right">
          <span className="footer-badge">RENDER CLOUD READY</span>
        </div>
      </footer>
    </div>
  );
}
