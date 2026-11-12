import { useState } from "react";

export function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (!isOpen) return null;

  function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (isSignUp && !name) {
      setError("Please enter your name.");
      return;
    }

    const user = {
      name: isSignUp ? name : email.split("@")[0],
      email: email,
      isGuest: false,
      loginTime: new Date().toISOString(),
    };

    try {
      localStorage.setItem("codelens.user", JSON.stringify(user));
    } catch {
      // storage unavailable
    }

    onAuthSuccess(user);
  }

  function handleGuestMode() {
    const guestUser = {
      name: "Guest Developer",
      email: "guest@codelens.local",
      isGuest: true,
      loginTime: new Date().toISOString(),
    };

    try {
      localStorage.setItem("codelens.user", JSON.stringify(guestUser));
    } catch {
      // storage unavailable
    }

    onAuthSuccess(guestUser);
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div
        className="auth-modal glass-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <button
          className="auth-close-btn"
          onClick={onClose}
          aria-label="Close modal"
        >
          ✕
        </button>

        <div className="auth-header">
          <div className="auth-brand-badge">
            <span className="auth-dot" />
            <span>CODELENS AUTH</span>
          </div>
          <h2 className="auth-title">
            {isSignUp ? "Create an Account" : "Welcome Back"}
          </h2>
          <p className="auth-subtitle">
            {isSignUp
              ? "Join CodeLens to index, analyze, and interrogate your codebases."
              : "Sign in to access your intelligence workspaces and repositories."}
          </p>
        </div>

        <div className="auth-tabs-pill">
          <button
            type="button"
            className={`auth-tab ${!isSignUp ? "active" : ""}`}
            onClick={() => {
              setIsSignUp(false);
              setError("");
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${isSignUp ? "active" : ""}`}
            onClick={() => {
              setIsSignUp(true);
              setError("");
            }}
          >
            Create Account
          </button>
        </div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {isSignUp && (
            <div className="auth-input-group">
              <label htmlFor="auth-name">Full Name</label>
              <input
                id="auth-name"
                type="text"
                placeholder="Alex Turing"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
          )}

          <div className="auth-input-group">
            <label htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              placeholder="alex@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus={!isSignUp}
            />
          </div>

          <div className="auth-input-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="auth-submit-btn">
            {isSignUp ? "Create Account →" : "Sign In →"}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <button
          type="button"
          className="auth-guest-btn"
          onClick={handleGuestMode}
        >
          <span className="guest-sparkle">⚡</span>
          <span>Continue as Guest (Instant Demo Mode)</span>
        </button>
      </div>
    </div>
  );
}
