import { useCallback, useEffect, useState } from "react";
import { HomePage } from "./pages/HomePage";
import { RepositoriesPage } from "./pages/RepositoriesPage";
import { ExplorerPage } from "./pages/ExplorerPage";
import { AskPage } from "./pages/AskPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AiCompanion } from "./components/AiCompanion";
import { Atmosphere } from "./components/Atmosphere";
import { addPaths, computeStats } from "./repoUtils";
import { API_URL, fetchJson } from "./api";
import "./App.css";

const PAGES = [
  { id: "home", label: "Command Center" },
  { id: "repositories", label: "Repositories" },
  { id: "explorer", label: "Code Explorer" },
  { id: "ask", label: "Ask CodeLens" },
  { id: "settings", label: "Settings" },
];

const ACTIVE_REPO_KEY = "codelens.activeRepoId";
const THEME_KEY = "codelens.theme";

function readStoredTheme() {
  try {
    return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function App() {
  const [page, setPage] = useState("home");
  // Full analysis payloads, keyed by repository_id. Populated when a
  // workspace is analyzed or opened (including reopen after a restart).
  const [repos, setRepos] = useState({});
  // Lightweight metadata list from the backend index (survives restarts).
  const [repoList, setRepoList] = useState([]);
  const [activeId, setActiveId] = useState(null);
  // Companion state. eventKey increments on every real event so the
  // companion can distinguish repeated identical messages.
  const [ai, setAi] = useState({ status: "idle", message: "", eventKey: 0 });
  // Visual theme: dark is the default; persisted in localStorage.
  const [theme, setTheme] = useState(readStoredTheme);

  // Open-file request shared between Ask (citations) and Explorer.
  const [openRequest, setOpenRequest] = useState(null);

  const activeRepo = activeId ? repos[activeId] : null;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;

    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // Storage unavailable — theme just won't persist.
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const aiStatus = useCallback((status, message = "") => {
    setAi((prev) => ({ status, message, eventKey: prev.eventKey + 1 }));
  }, []);

  const refreshRepoList = useCallback(async () => {
    try {
      const data = await fetchJson(`${API_URL}/repositories`);
      setRepoList(data.repositories);
      return data.repositories;
    } catch {
      // Backend unreachable (e.g. dev server without API). Leave the
      // list empty; pages show their empty states.
      return null;
    }
  }, []);

  // Fetch the full analysis payload for a workspace and make it active.
  // Used by first analysis, reopening a project, and restart recovery.
  const loadRepo = useCallback(async (repositoryId) => {
    const data = await fetchJson(`${API_URL}/repository/${repositoryId}`);

    const repo = {
      ...data,
      tree: addPaths(data.tree),
      stats: computeStats(data),
    };

    setRepos((prev) => ({ ...prev, [repositoryId]: repo }));
    setActiveId(repositoryId);

    try {
      localStorage.setItem(ACTIVE_REPO_KEY, repositoryId);
    } catch {
      // Storage unavailable — recovery just won't persist.
    }

    return repo;
  }, []);

  const removeRepo = useCallback(
    async (repositoryId) => {
      await fetchJson(`${API_URL}/repository/${repositoryId}`, {
        method: "DELETE",
      });

      setRepos((prev) => {
        const next = { ...prev };
        delete next[repositoryId];
        return next;
      });

      setActiveId((current) => {
        if (current === repositoryId) {
          try {
            localStorage.removeItem(ACTIVE_REPO_KEY);
          } catch {
            // Ignore storage failures.
          }

          return null;
        }

        return current;
      });

      await refreshRepoList();
      aiStatus("success", "Project removed.");
    },
    [aiStatus, refreshRepoList]
  );

  const handleAnalyzed = useCallback(
    (data, stats) => {
      const repo = { ...data, tree: addPaths(data.tree), stats };

      setRepos((prev) => ({ ...prev, [data.repository_id]: repo }));
      setActiveId(data.repository_id);

      try {
        localStorage.setItem(ACTIVE_REPO_KEY, data.repository_id);
      } catch {
        // Ignore storage failures.
      }

      refreshRepoList();
    },
    [refreshRepoList]
  );

  // Opens a repo-relative file in the Code Explorer. Used by Ask citations
  // and the evidence panel.
  const openFile = useCallback(
    (file, line = null) => {
      if (!activeRepo) return;

      setOpenRequest({ file, line, repo: activeRepo.repository_id });
      setPage("explorer");
    },
    [activeRepo]
  );

  const consumeOpenRequest = useCallback(() => setOpenRequest(null), []);

  // User-driven navigation gives the companion a subtle curious flourish
  // (visual only — no message) unless a request is already in flight.
  const navigate = useCallback(
    (nextPage) => {
      setPage(nextPage);

      setAi((prev) =>
        prev.status === "idle" || prev.status === "curious"
          ? { status: "curious", message: "", eventKey: prev.eventKey + 1 }
          : prev
      );
    },
    []
  );

  // Clicking the robot is a shortcut to Ask (or home when no repo is
  // loaded) — user-initiated, so it never counts as unsolicited chat.
  const activateCompanion = useCallback(() => {
    setPage(activeRepo ? "ask" : "home");
  }, [activeRepo]);

  const openRepo = useCallback(
    async (repositoryId) => {
      aiStatus("loading", "Opening project…");

      try {
        await loadRepo(repositoryId);
        setPage("explorer");
        aiStatus("success", "Project ready.");
      } catch (err) {
        aiStatus("error", "Could not open project.");

        if (err.message.includes("410") || err.message.includes("404")) {
          // Workspace vanished (deleted files or already removed) — drop
          // it from the list so stale entries don't linger.
          await refreshRepoList();
        }
      }
    },
    [aiStatus, loadRepo, refreshRepoList]
  );

  // On mount: load the persisted workspace index, then recover the last
  // active project if it still exists. Runs once — loadRepo is stable.
  useEffect(() => {
    let cancelled = false;

    fetchJson(`${API_URL}/repositories`)
      .then((data) => {
        if (cancelled) return;

        setRepoList(data.repositories);

        let savedId = null;

        try {
          savedId = localStorage.getItem(ACTIVE_REPO_KEY);
        } catch {
          // Ignore storage failures.
        }

        if (!savedId) return;

        const saved = data.repositories.find(
          (entry) => entry.repository_id === savedId && entry.available
        );

        if (!saved) return;

        loadRepo(savedId).catch(() => {
          // Backend error mid-restore; user can reopen manually.
        });
      })
      .catch(() => {
        // Backend unreachable — pages show empty states.
      });

    return () => {
      cancelled = true;
    };
  }, [loadRepo]);

  function renderPage() {
    switch (page) {
      case "home":
        return (
          <HomePage
            onAnalyzed={handleAnalyzed}
            onNavigate={navigate}
            aiStatus={aiStatus}
            repoList={repoList}
            onOpenRepo={openRepo}
          />
        );
      case "repositories":
        return (
          <RepositoriesPage
            repoList={repoList}
            repos={repos}
            activeId={activeId}
            onOpenRepo={openRepo}
            onRemoveRepo={removeRepo}
            onNavigate={navigate}
          />
        );
      case "explorer":
        return (
          <ExplorerPage
            key={activeId ?? "none"}
            result={activeRepo}
            aiStatus={aiStatus}
            openRequest={openRequest}
            onOpenRequestConsumed={consumeOpenRequest}
          />
        );
      case "ask":
        return <AskPage result={activeRepo} aiStatus={aiStatus} onOpenFile={openFile} />;
      case "settings":
        return <SettingsPage aiStatus={aiStatus} />;
      default:
        return null;
    }
  }

  return (
    <div className="app-shell">
      <Atmosphere />
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">CodeLens</span>
          <span className="brand-tag">AI developer workspace</span>
        </div>

        <nav className="sidebar-nav">
          {PAGES.map((item, index) => (
            <button
              key={item.id}
              className={`nav-item ${page === item.id ? "active" : ""}`}
              onClick={() => navigate(item.id)}
            >
              <span className="nav-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            <span className="theme-toggle-icon" aria-hidden="true">
              {theme === "dark" ? "◐" : "◑"}
            </span>
            <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
          </button>
          {activeRepo ? (
            <div className="sidebar-active-repo" title={activeRepo.name}>
              <span className="repo-dot" />
              <span className="repo-name">{activeRepo.name}</span>
            </div>
          ) : (
            <div className="sidebar-active-repo muted">No repo loaded</div>
          )}
        </div>
      </aside>

      <main className="app-content">{renderPage()}</main>

      <AiCompanion
        status={ai.status}
        message={ai.message}
        eventKey={ai.eventKey}
        onActivate={activateCompanion}
      />
    </div>
  );
}

export default App;
