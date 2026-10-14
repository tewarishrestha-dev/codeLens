import { useEffect, useRef, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FileTree } from "../components/FileTree";
import {
  ArchitectureGraph,
  DependencyGraph,
  ExecutionFlow,
} from "../components/Graphs";
import { getLanguage, stripRepoPrefix, toPosix } from "../repoUtils";
import { API_URL, fetchJson } from "../api";

// Internal explorer views. Top-level navigation is unchanged — these are
// tabs inside Code Explorer only.
const VIEW_CODE = "code";
const VIEW_STUDIO = "studio";

// Graph Studio selector options. Each maps 1:1 to an existing graph
// component; switching remounts one component and never mutates others.
const GRAPHS = [
  { id: "dependency", label: "Dependency" },
  { id: "architecture", label: "Architecture" },
  { id: "flow", label: "Execution Flow" },
];

// Code Explorer: file tree, syntax-highlighted viewer, per-file analysis,
// code search, and a dedicated Graph Studio for dependency / architecture
// / execution-flow graphs. Analysis success is the existing App-level
// `result` payload (full repository analysis loaded via loadRepo).
export function ExplorerPage({ result, aiStatus, openRequest, onOpenRequestConsumed }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileAnalysis, setFileAnalysis] = useState(null);
  // Execution flow steps + explicit status so Graph Studio can show
  // loading / empty / error instead of a blank or broken canvas.
  const [flowState, setFlowState] = useState({
    status: "idle",
    steps: [],
    message: "",
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [error, setError] = useState("");
  // Architecture overview is content-heavy; keep it collapsed by default
  // so the three-column workspace keeps useful vertical space.
  const [archOpen, setArchOpen] = useState(false);
  // Internal view + which single graph Graph Studio is showing.
  const [explorerView, setExplorerView] = useState(VIEW_CODE);
  const [graphKind, setGraphKind] = useState("dependency");
  const codeRef = useRef(null);
  const [targetLine, setTargetLine] = useState(null);
  const [highlightLine, setHighlightLine] = useState(null);
  // Large overlay viewer for the selected source file. Opened by openFile;
  // closed by the user without clearing selectedFile (analysis stays intact).
  // Opening from Graph Studio and closing returns to Graph Studio with the
  // same graph still selected — explorerView is never cleared by the overlay.
  const [viewerOpen, setViewerOpen] = useState(false);

  // Graph Studio is gated on the existing analysis payload. `result` is
  // only set after a successful loadRepo, which is the app's source of
  // truth for "analysis completed". No new analysis mechanism is introduced.
  const graphDataReady = Boolean(
    result &&
      result.dependencies &&
      result.architecture &&
      Array.isArray(result.architecture.files)
  );

  // Load the default execution flow on mount. Per-repo state resets
  // naturally because this page unmounts whenever navigation leaves it
  // (App keys ExplorerPage by activeId).
  // `idle` is treated as loading while entry points exist; empty/error
  // are set only in async callbacks (allowed by the lint rule).
  useEffect(() => {
    if (!result?.entry_points?.length) {
      return undefined;
    }

    let cancelled = false;

    fetchJson(
      `${API_URL}/repository/${result.repository_id}/flow?entry_point=${encodeURIComponent(result.entry_points[0])}`
    )
      .then((data) => {
        if (cancelled) return;
        const steps = data.steps || [];
        setFlowState({
          status: steps.length > 0 ? "ready" : "empty",
          steps,
          message:
            steps.length > 0
              ? ""
              : "The backend returned an empty execution flow for this entry point.",
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setFlowState({
          status: "error",
          steps: [],
          message: err.message || "Could not load the execution flow.",
        });
        setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [result]);

  async function openFile(filePath, line = null) {
    try {
      const relativePath = stripRepoPrefix(toPosix(filePath));

      const data = await fetchJson(
        `${API_URL}/file?repository_id=${result.repository_id}&file_path=${encodeURIComponent(relativePath)}`
      );

      setSelectedFile(relativePath);
      setFileContent(data.content);
      setTargetLine(line);
      setHighlightLine(line);
      setFileAnalysis(result.code_analysis[relativePath]);
      setViewerOpen(true);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  // Consume an open-file request from another page (e.g. Ask citations).
  // Companion states reflect the real fetch outcome, never a guess.
  useEffect(() => {
    if (!openRequest || !result) return;
    if (openRequest.repo !== result.repository_id) return;

    const relativePath = stripRepoPrefix(toPosix(openRequest.file));
    const line = openRequest.line;

    aiStatus("thinking", "Jumping to source…");

    fetchJson(
      `${API_URL}/file?repository_id=${result.repository_id}&file_path=${encodeURIComponent(relativePath)}`
    )
      .then((data) => {
        setSelectedFile(relativePath);
        setFileContent(data.content);
        setTargetLine(line);
        setHighlightLine(line);
        setFileAnalysis(result.code_analysis[relativePath]);
        setViewerOpen(true);
        setError("");
        aiStatus(
          "success",
          line ? `Opened ${relativePath}:${line}` : `Opened ${relativePath}`
        );
        onOpenRequestConsumed();
      })
      .catch((err) => {
        setError(err.message);
        aiStatus("error", "Couldn't open that file.");
      });
  }, [openRequest, result, onOpenRequestConsumed, aiStatus]);

  async function searchRepository() {
    if (!searchQuery.trim() || !result) return;

    aiStatus("thinking", "Searching…");

    try {
      const data = await fetchJson(
        `${API_URL}/repository/${result.repository_id}/search?query=${encodeURIComponent(searchQuery)}`
      );

      setSearchResults(data.results);

      const count = data.results.length;
      aiStatus(
        "success",
        count === 0 ? "No matches." : `${count} match${count === 1 ? "" : "es"}.`
      );
    } catch (err) {
      setError(err.message);
      aiStatus("error", "Search failed.");
    }
  }

  useEffect(() => {
    if (!targetLine || !codeRef.current) return;

    const lineElement = codeRef.current.querySelector(
      `[data-line-number="${targetLine}"]`
    );

    lineElement?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [fileContent, targetLine]);

  // Escape closes the large viewer without clearing the selected file or
  // the internal explorer view, so Graph Studio and analysis stay intact.
  useEffect(() => {
    if (!viewerOpen) return undefined;

    function onKeyDown(event) {
      if (event.key === "Escape") {
        setViewerOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [viewerOpen]);

  function renderFlowStage() {
    if (!result?.entry_points?.length) {
      return (
        <div className="graph-studio-message">
          <p className="graph-studio-message-title">No execution flow</p>
          <p>No entry points detected, so there is no execution flow.</p>
        </div>
      );
    }

    // idle = fetch in flight (initial mount / repo switch remount)
    if (flowState.status === "idle" || flowState.status === "loading") {
      return (
        <div className="graph-studio-message" role="status">
          <p className="graph-studio-message-title">Loading execution flow…</p>
          <p>Fetching the call sequence for the primary entry point.</p>
        </div>
      );
    }

    if (flowState.status === "error") {
      return (
        <div className="graph-studio-message graph-studio-message--error">
          <p className="graph-studio-message-title">Execution flow unavailable</p>
          <p>{flowState.message}</p>
        </div>
      );
    }

    if (flowState.status === "empty") {
      return (
        <div className="graph-studio-message">
          <p className="graph-studio-message-title">No execution flow</p>
          <p>{flowState.message}</p>
        </div>
      );
    }

    return (
      <ExecutionFlow
        executionFlow={flowState.steps}
        onFileClick={openFile}
        repoName={result.tree.name}
        selectedFile={selectedFile}
      />
    );
  }

  function renderGraphStudio() {
    if (!graphDataReady) {
      return (
        <div className="graph-studio">
          <div className="graph-studio-message graph-studio-message--error">
            <p className="graph-studio-message-title">Graph data unavailable</p>
            <p>
              This repository does not have dependency or architecture data
              from analysis. Re-analyze the project from the Command Center,
              then reopen it here.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="graph-studio">
        <div
          className="graph-studio-tabs"
          role="tablist"
          aria-label="Graph type"
        >
          {GRAPHS.map((graph) => (
            <button
              key={graph.id}
              type="button"
              role="tab"
              id={`graph-studio-tab-${graph.id}`}
              aria-selected={graphKind === graph.id}
              aria-controls="graph-studio-stage"
              data-kind={graph.id}
              className={`graph-studio-tab${
                graphKind === graph.id ? " active" : ""
              }`}
              onClick={() => setGraphKind(graph.id)}
            >
              {graph.label}
            </button>
          ))}
        </div>

        <div
          className="graph-studio-stage"
          id="graph-studio-stage"
          role="tabpanel"
          aria-labelledby={`graph-studio-tab-${graphKind}`}
        >
          {graphKind === "dependency" && (
            <DependencyGraph
              key={`dep-${result.repository_id}`}
              result={result}
              onFileClick={openFile}
              selectedFile={selectedFile}
            />
          )}
          {graphKind === "architecture" && (
            <ArchitectureGraph
              key={`arch-${result.repository_id}`}
              result={result}
              onFileClick={openFile}
              selectedFile={selectedFile}
            />
          )}
          {graphKind === "flow" && renderFlowStage()}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="page explorer-page">
        <div className="empty-state">
          <p>No repository loaded.</p>
          <p className="empty-hint">
            Analyze one from the{" "}
            <strong>Command Center</strong> first. Graph Studio unlocks once
            analysis completes.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page explorer-page">
      <div className="repo-stats">
        <div className="repo-stats-name">
          <strong>{result.name}</strong>
          <span>Code Explorer</span>
        </div>
        <div><strong>{result.stats?.files ?? result.architecture.file_count}</strong><span>Files</span></div>
        <div><strong>{result.stats?.python ?? 0}</strong><span>Python</span></div>
        <div><strong>{result.architecture.function_count}</strong><span>Functions</span></div>
        <div><strong>{result.architecture.class_count}</strong><span>Classes</span></div>
        <div><strong>{result.architecture.dependency_count}</strong><span>Dependencies</span></div>
        <div><strong>{result.entry_points?.length || 0}</strong><span>Entry Points</span></div>
      </div>

      <div
        className="explorer-view-tabs"
        role="tablist"
        aria-label="Code Explorer views"
      >
        <button
          type="button"
          role="tab"
          id="explorer-tab-code"
          aria-selected={explorerView === VIEW_CODE}
          aria-controls="explorer-view-panel"
          className={`explorer-view-tab${
            explorerView === VIEW_CODE ? " active" : ""
          }`}
          onClick={() => setExplorerView(VIEW_CODE)}
        >
          Code
        </button>
        <button
          type="button"
          role="tab"
          id="explorer-tab-studio"
          aria-selected={explorerView === VIEW_STUDIO}
          aria-controls="explorer-view-panel"
          className={`explorer-view-tab${
            explorerView === VIEW_STUDIO ? " active" : ""
          }`}
          onClick={() => setExplorerView(VIEW_STUDIO)}
          disabled={!graphDataReady}
          title={
            graphDataReady
              ? "Open Graph Studio"
              : "Graph Studio needs successful analysis data"
          }
        >
          Graph Studio
        </button>
      </div>

      <div
        id="explorer-view-panel"
        role="tabpanel"
        aria-labelledby={`explorer-tab-${explorerView}`}
        className="explorer-view-panel"
      >
      {error && <div className="error">{error}</div>}

      {explorerView === VIEW_CODE && (
        <>
          <div className={`architecture-panel${archOpen ? " open" : ""}`}>
            <button
              type="button"
              className="architecture-toggle"
              onClick={() => setArchOpen((v) => !v)}
              aria-expanded={archOpen}
            >
              <h3>Architecture Overview</h3>
              <span className="architecture-toggle-icon" aria-hidden="true">
                {archOpen ? "▾" : "▸"}
              </span>
            </button>

            {archOpen && (
              <div className="architecture-body">
                <div className="architecture-grid">
                  <div><strong>{result.architecture.file_count}</strong><span>Files</span></div>
                  <div><strong>{result.architecture.function_count}</strong><span>Functions</span></div>
                  <div><strong>{result.architecture.class_count}</strong><span>Classes</span></div>
                  <div><strong>{result.architecture.dependency_count}</strong><span>Dependencies</span></div>
                  <div><strong>{result.architecture.directory_count}</strong><span>Modules</span></div>
                </div>

                <div className="architecture-section">
                  <h4>Entry Points</h4>
                  {result.architecture.entry_points.length === 0 ? (
                    <p>None detected</p>
                  ) : (
                    <ul>
                      {result.architecture.entry_points.map((file) => (
                        <li
                          key={file}
                          onClick={() => openFile(`${result.tree.name}/${file}`)}
                          style={{ cursor: "pointer" }}
                        >
                          {file}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="architecture-section">
                  <h4>Functions</h4>
                  {result.architecture.functions.length === 0 ? (
                    <p>None detected</p>
                  ) : (
                    <ul>
                      {result.architecture.functions.map((item) => (
                        <li
                          key={`${item.file}-${item.name}`}
                          onClick={() => openFile(`${result.tree.name}/${item.file}`, item.line)}
                          style={{ cursor: "pointer" }}
                        >
                          {item.name}() — {item.file}:{item.line}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="architecture-section">
                  <h4>Classes</h4>
                  {result.architecture.classes.length === 0 ? (
                    <p>None detected</p>
                  ) : (
                    <ul>
                      {result.architecture.classes.map((item) => (
                        <li
                          key={`${item.file}-${item.name}`}
                          onClick={() => openFile(`${result.tree.name}/${item.file}`, item.line)}
                          style={{ cursor: "pointer" }}
                        >
                          {item.name} — {item.file}:{item.line}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="architecture-section">
                  <h4>Modules</h4>
                  <ul>
                    {Object.entries(result.architecture.directories).map(([directory, files]) => (
                      <li key={directory}>
                        <strong>{directory}/</strong>
                        <ul>
                          {files.map((file) => (
                            <li
                              key={file}
                              onClick={() => openFile(`${result.tree.name}/${file}`)}
                              style={{ cursor: "pointer" }}
                            >
                              {file}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="architecture-section">
                  <h4>Module Dependencies</h4>
                  {result.architecture.dependencies.length === 0 ? (
                    <p>None detected</p>
                  ) : (
                    <ul>
                      {result.architecture.dependencies.map((dependency, index) => (
                        <li
                          key={index}
                          onClick={() => openFile(`${result.tree.name}/${dependency.to}`)}
                          style={{ cursor: "pointer" }}
                        >
                          {dependency.from} → {dependency.to}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <p className="architecture-studio-hint">
                  Visual graphs live in{" "}
                  <button
                    type="button"
                    className="inline-link"
                    onClick={() => setExplorerView(VIEW_STUDIO)}
                    disabled={!graphDataReady}
                  >
                    Graph Studio
                  </button>
                  .
                </p>
              </div>
            )}
          </div>

          <div className="code-search">
            <div className="code-search-bar">
              <input
                type="search"
                placeholder="Search the codebase…"
                aria-label="Search the codebase"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && searchRepository()}
              />
              <button type="button" onClick={searchRepository}>
                Search
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="code-search-results">
                {searchResults.map((item) => (
                  <div
                    key={item.file}
                    onClick={() => openFile(`${result.tree.name}/${item.file}`)}
                  >
                    <strong>{item.file}</strong>
                    {item.matches.map((match, index) => (
                      <div
                        key={index}
                        onClick={(event) => {
                          event.stopPropagation();
                          openFile(`${result.tree.name}/${item.file}`, match.line);
                        }}
                      >
                        {match.type}: {match.name}
                        {match.line && ` — line ${match.line}`}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>

          <main className="workspace">
            <aside className="panel tree-panel">
              <h3>{result.name}</h3>

              {result.tree.children?.map((child) => (
                <FileTree
                  key={child.path}
                  node={child}
                  onFileClick={openFile}
                  selectedFile={selectedFile}
                />
              ))}
            </aside>

            <section className="panel code-panel">
              <h3>{selectedFile || "Select a file"}</h3>

              {selectedFile ? (
                <div ref={codeRef}>
                  <SyntaxHighlighter
                    language={getLanguage(selectedFile)}
                    style={vscDarkPlus}
                    showLineNumbers
                    wrapLines
                    wrapLongLines={false}
                    lineProps={(lineNumber) => ({
                      "data-line-number": lineNumber,
                      style:
                        lineNumber === highlightLine
                          ? {
                              background: "var(--signal-wash)",
                              borderLeft: "3px solid var(--signal)",
                              display: "block",
                            }
                          : undefined,
                    })}
                  >
                    {fileContent}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <div className="code-empty-state">
                  <span className="code-empty-icon" aria-hidden="true">
                    ⟨/⟩
                  </span>
                  <p className="code-empty-title">Select a file to inspect it</p>
                  <p className="code-empty-hint">
                    Choose any file from the tree, jump via search, or open an
                    entry point. Source opens in the code viewer; per-file
                    analysis appears on the right. Graphs are in Graph Studio.
                  </p>
                </div>
              )}
            </section>

            <aside className="panel analysis-panel">
              <h3>Code Analysis</h3>

              {fileAnalysis ? (
                <>
                  <h4>Imports</h4>
                  <ul>
                    {fileAnalysis.imports.map((item) => {
                      const dependency = (
                        result.dependencies.forward[selectedFile] || []
                      ).find((file) => file.startsWith(item));

                      return (
                        <li
                          key={item}
                          onClick={() => {
                            if (dependency) {
                              openFile(`${result.tree.name}/${dependency}`);
                            }
                          }}
                          style={{ cursor: dependency ? "pointer" : "default" }}
                        >
                          {item}
                        </li>
                      );
                    })}
                  </ul>

                  <h4>Functions</h4>
                  <ul>
                    {fileAnalysis.functions.map((item) => (
                      <li
                        key={item.name}
                        onClick={() => openFile(`${result.tree.name}/${selectedFile}`, item.line)}
                        style={{ cursor: "pointer" }}
                      >
                        {item.name}() — line {item.line}
                      </li>
                    ))}
                  </ul>

                  <h4>Classes</h4>
                  <ul>
                    {fileAnalysis.classes.map((item) => (
                      <li key={item.name}>
                        {item.name}
                        <ul>
                          {item.methods.map((method) => (
                            <li
                              key={method.name}
                              onClick={() =>
                                openFile(`${result.tree.name}/${selectedFile}`, method.line)
                              }
                              style={{ cursor: "pointer" }}
                            >
                              {method.name}() — line {method.line}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>

                  <h4>Calls</h4>
                  {selectedFile && (
                    <ul>
                      {Object.entries(result.call_graph[selectedFile] || {}).map(
                        ([functionName, calls]) =>
                          calls.map((call, index) => (
                            <li
                              key={`${functionName}-${index}`}
                              onClick={() => {
                                if (typeof call.target_file === "string") {
                                  openFile(
                                    `${result.tree.name}/${call.target_file}`,
                                    call.target_line
                                  );
                                }
                              }}
                              style={{
                                cursor:
                                  typeof call.target_file === "string" ? "pointer" : "default",
                              }}
                            >
                              {functionName}() → {call.calls} — line {call.line}
                            </li>
                          ))
                      )}
                    </ul>
                  )}
                </>
              ) : (
                <p>Select a file to inspect it.</p>
              )}

              <h4>Entry Points</h4>
              <ul>
                {(result.entry_points || []).map((file) => (
                  <li
                    key={file}
                    onClick={() => openFile(`${result.tree.name}/${file}`)}
                    style={{ cursor: "pointer" }}
                  >
                    {file}
                  </li>
                ))}
              </ul>

              <h4>Dependencies</h4>
              {selectedFile && (
                <ul>
                  {(result.dependencies.forward[selectedFile] || []).map((file) => (
                    <li
                      key={file}
                      onClick={() => openFile(`${result.tree.name}/${file}`)}
                      style={{ cursor: "pointer" }}
                    >
                      {file}
                    </li>
                  ))}
                </ul>
              )}

              <h4>Used By</h4>
              {selectedFile && (
                <ul>
                  {(result.dependencies.reverse[selectedFile] || []).map((file) => (
                    <li
                      key={file}
                      onClick={() => openFile(`${result.tree.name}/${file}`)}
                      style={{ cursor: "pointer" }}
                    >
                      {file}
                    </li>
                  ))}
                </ul>
              )}

              <p className="analysis-studio-hint">
                Dependency and execution-flow graphs:{" "}
                <button
                  type="button"
                  className="inline-link"
                  onClick={() => setExplorerView(VIEW_STUDIO)}
                  disabled={!graphDataReady}
                >
                  Graph Studio
                </button>
              </p>
            </aside>
          </main>
        </>
      )}

      {explorerView === VIEW_STUDIO && renderGraphStudio()}
      </div>

      {/* Large code viewer overlay. Layers above the workspace while open;
          closing it returns to the previous internal view (Code or Graph
          Studio) with selection and graph choice intact. */}
      {viewerOpen && selectedFile && (
        <div
          className="code-viewer-overlay"
          role="dialog"
          aria-modal="false"
          aria-label={`Code viewer: ${selectedFile}`}
        >
          <div className="code-viewer-panel">
            <header className="code-viewer-header">
              <div className="code-viewer-meta">
                <span className="code-viewer-filename">
                  {selectedFile.split("/").pop()}
                </span>
                <span className="code-viewer-path" title={selectedFile}>
                  {selectedFile}
                </span>
              </div>
              <button
                type="button"
                className="code-viewer-close"
                onClick={() => setViewerOpen(false)}
                aria-label="Close code viewer"
                title="Close (Esc)"
              >
                ×
              </button>
            </header>

            <div className="code-viewer-body" ref={codeRef}>
              <SyntaxHighlighter
                language={getLanguage(selectedFile)}
                style={vscDarkPlus}
                showLineNumbers
                wrapLines
                wrapLongLines={false}
                lineProps={(lineNumber) => ({
                  "data-line-number": lineNumber,
                  style:
                    lineNumber === highlightLine
                      ? {
                          background: "var(--signal-wash)",
                          borderLeft: "3px solid var(--signal)",
                          display: "block",
                        }
                      : undefined,
                })}
              >
                {fileContent}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
