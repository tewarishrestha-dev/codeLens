// Repositories view: lists persisted workspaces from the backend index and
// lets the user open, switch, or remove them. Entries whose files were
// deleted on disk are flagged instead of being served as usable.
export function RepositoriesPage({
  repoList,
  repos,
  activeId,
  onOpenRepo,
  onRemoveRepo,
  onNavigate,
}) {
  function formatOpened(entry) {
    if (!entry.last_opened_at) return "";

    const date = new Date(entry.last_opened_at);

    return Number.isNaN(date.getTime())
      ? ""
      : `opened ${date.toLocaleDateString()}`;
  }

  function handleRemove(entry, event) {
    event.stopPropagation();

    const confirmed = window.confirm(
      `Remove "${entry.name}" from CodeLens?\n\n` +
        "The workspace entry and its index will be deleted. " +
        "The project files themselves are not touched."
    );

    if (confirmed) {
      onRemoveRepo(entry.repository_id);
    }
  }

  return (
    <div className="page repos-page">
      <div className="page-header">
        <p className="page-kicker">
          <span className="kicker-index">02</span> Workspaces
        </p>
        <h2>Repositories</h2>
        <p>
          Your analyzed projects. Workspaces persist across restarts — reopening
          a project re-analyzes it from its files if needed.
        </p>
      </div>

      {repoList.length === 0 ? (
        <div className="empty-state">
          <p>No repositories analyzed yet.</p>
          <button onClick={() => onNavigate("home")}>Analyze a repository</button>
        </div>
      ) : (
        <div className="repo-grid">
          {repoList.map((entry, index) => {
            const loaded = repos[entry.repository_id];
            const isActive = entry.repository_id === activeId;
            const missing = !entry.available;

            return (
              <div
                key={entry.repository_id}
                className={`repo-card ${isActive ? "active" : ""} ${missing ? "missing" : ""}`}
                onClick={() => {
                  if (missing) return;
                  onOpenRepo(entry.repository_id);
                }}
                title={missing ? "Project files are missing on disk" : entry.path}
              >
                <span className="repo-index">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <div className="repo-info">
                  <h3>{entry.name}</h3>

                  <p className="repo-card-meta">
                    {missing
                      ? "Files missing on disk"
                      : loaded?.stats
                        ? `${loaded.stats.files} files · ${loaded.stats.functions} functions`
                        : formatOpened(entry) || "Ready to open"}
                  </p>
                </div>

                <div className="repo-card-actions">
                  {isActive && <span className="repo-badge">Active</span>}
                  {missing ? (
                    <span className="repo-badge missing">Unavailable</span>
                  ) : (
                    <button
                      className="repo-open"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenRepo(entry.repository_id);
                      }}
                    >
                      Open
                    </button>
                  )}
                  <button
                    className="repo-remove"
                    onClick={(event) => handleRemove(entry, event)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
