import { useEffect, useRef, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function FileTree({ node, onFileClick, selectedFile }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (selectedFile && node.type === "directory") {
      const containsSelected = selectedFile.startsWith(
        node.path.split("/").slice(1).join("/") + "/"
      );

      if (containsSelected) {
        setOpen(true);
      }
    }
  }, [selectedFile]);

  if (node.type === "file") {
    const isSelected = node.path.split("/").slice(1).join("/") === selectedFile;

    return (
      <div
        className={`file ${isSelected ? "selected" : ""}`}
        onClick={() => onFileClick(node.path)}
      >
        📄 {node.name}
      </div>
    );
  }

  return (
    <div>
      <div className="folder" onClick={() => setOpen(!open)}>
        {open ? "📂" : "📁"} {node.name}
      </div>

      {open &&
        node.children?.map((child) => (
          <FileTree
            key={child.path}
            node={child}
            onFileClick={onFileClick}
            selectedFile={selectedFile}
          />
        ))}
    </div>
  );
}

function addPaths(node, parentPath = "") {
  const path = parentPath ? `${parentPath}/${node.name}` : node.name;

  return {
    ...node,
    path,
    children: node.children?.map((child) => addPaths(child, path)),
  };
}

function getLanguage(filePath) {
  const ext = filePath?.split(".").pop();

  const languages = {
    py: "python",
    js: "javascript",
    jsx: "jsx",
    ts: "typescript",
    tsx: "tsx",
    json: "json",
    html: "markup",
    css: "css",
    md: "markdown",
    java: "java",
    cpp: "cpp",
    c: "c",
  };

  return languages[ext] || "text";
}

function DependencyGraph({ result, onFileClick, selectedFile }) {
  const files = Object.keys(result.dependencies.forward);

  const graph = new dagre.graphlib.Graph();

  graph.setDefaultEdgeLabel(() => ({}));

  graph.setGraph({
    rankdir: "LR",
    nodesep: 80,
    ranksep: 150,
  });

  const edges = [];

  files.forEach((file) => {
    graph.setNode(file, {
      width: 160,
      height: 50,
    });

    result.dependencies.forward[file].forEach((dependency) => {
      edges.push({
        id: `${file}-${dependency}`,
        source: file,
        target: dependency,
      });

      graph.setEdge(file, dependency);
    });
  });

  dagre.layout(graph);

  const relatedFiles = selectedFile
    ? new Set([
        selectedFile,
        ...(result.dependencies.forward[selectedFile] || []),
      ])
    : new Set(files);

  const nodes = files.map((file) => {
    const position = graph.node(file);
    const isSelected = file === selectedFile;
    const isRelated = relatedFiles.has(file);

    return {
      id: file,
      position: {
        x: position.x - 80,
        y: position.y - 25,
      },
      data: {
        label: (
          <div>
            <strong>{file}</strong>

            <div style={{ marginTop: "6px", fontSize: "12px" }}>
              {result.architecture.functions
                .filter((item) => item.file === file)
                .map((item) => (
                  <div key={`function-${item.name}`}>{item.name}()</div>
                ))}

              {result.architecture.classes
                .filter((item) => item.file === file)
                .map((item) => (
                  <div key={`class-${item.name}`}>class {item.name}</div>
                ))}
            </div>
          </div>
        ),
      },
      style: {
        opacity: isRelated ? 1 : 0.25,
        border: isSelected ? "2px solid #61dafb" : "1px solid #444",
        borderRadius: "6px",
        padding: "10px",
        background: "#191a21",
        color: "#e5e7eb",
      },
    };
  });

  const styledEdges = edges.map((edge) => ({
    ...edge,
    style: {
      opacity:
        !selectedFile ||
        edge.source === selectedFile ||
        edge.target === selectedFile
          ? 1
          : 0.2,
    },
  }));

  return (
    <div style={{ height: "420px" }}>
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodeClick={(event, node) => {
          onFileClick(`${result.tree.name}/${node.id}`);
        }}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function ArchitectureGraph({ result, onFileClick }) {
  const files = result.architecture.files;
  const directories = result.architecture.directories;

  const nodes = files.map((file, index) => {
    const directory =
      Object.entries(directories).find(([, moduleFiles]) =>
        moduleFiles.includes(file)
      )?.[0] || "root";

    return {
      id: file,
      position: {
        x: (index % 3) * 240,
        y: Math.floor(index / 3) * 130,
      },
      data: {
        label: (
          <div>
            <strong>{file}</strong>

            <div
              style={{
                marginTop: "4px",
                fontSize: "11px",
                color: "#9296a5",
              }}
            >
              {directory}/
            </div>

            <div style={{ marginTop: "6px", fontSize: "12px" }}>
              {result.architecture.functions
                .filter((item) => item.file === file)
                .map((item) => (
                  <div key={`function-${item.name}`}>{item.name}()</div>
                ))}

              {result.architecture.classes
                .filter((item) => item.file === file)
                .map((item) => (
                  <div key={`class-${item.name}`}>class {item.name}</div>
                ))}
            </div>
          </div>
        ),
      },
      style: {
        background: "#191a21",
        color: "#e5e7eb",
        border: "1px solid #444",
        borderRadius: "6px",
        padding: "10px",
        boxShadow: `0 0 0 1px ${directory === "root" ? "#444" : "#61dafb"}`,
      },
    };
  });

  const edges = result.architecture.dependencies.map((dependency, index) => ({
    id: `architecture-${index}`,
    source: dependency.from,
    target: dependency.to,
  }));

  return (
    <div style={{ height: "400px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(event, node) => {
          onFileClick(`${result.tree.name}/${node.id}`);
        }}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function ExecutionFlow({ executionFlow, onFileClick }) {
  const nodes = executionFlow.map((step, index) => ({
    id: String(index),
    position: {
      x: 250,
      y: index * 100,
    },
    data: {
      label: step.function ? `${step.file} → ${step.function}()` : step.file,
    },
    style: {
      background: "#191a21",
      color: "#e5e7eb",
      border: "1px solid #444",
      borderRadius: "6px",
      padding: "10px",
    },
  }));

  const edges = executionFlow.slice(1).map((_, index) => ({
    id: `flow-${index}`,
    source: String(index),
    target: String(index + 1),
  }));

  return (
    <div style={{ height: "400px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(event, node) => {
          const step = executionFlow[Number(node.id)];

          onFileClick(`${step.file}`, step.line);
        }}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [result, setResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [executionFlow, setExecutionFlow] = useState([]);
  const [fileAnalysis, setFileAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [summary, setSummary] = useState("");
  const [summarizing, setSummarizing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [stats, setStats] = useState(null);
  const codeRef = useRef(null);
  const [targetLine, setTargetLine] = useState(null);
  const [highlightLine, setHighlightLine] = useState(null);

  async function analyzeZip() {
    if (!file) return;

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/analyze/zip`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to analyze repository");
      }

      const data = await response.json();

      data.tree = addPaths(data.tree);

      const files = Object.keys(data.code_analysis);

      const functionCount = files.reduce(
        (total, file) => total + data.code_analysis[file].functions.length,
        0
      );

      const classCount = files.reduce(
        (total, file) => total + data.code_analysis[file].classes.length,
        0
      );

      const dependencyCount = Object.values(data.dependencies.forward).reduce(
        (total, dependencies) => total + dependencies.length,
        0
      );

      setStats({
        files: files.length,
        python: files.filter((file) => file.endsWith(".py")).length,
        functions: functionCount,
        classes: classCount,
        dependencies: dependencyCount,
      });

      setResult(data);

      if (data.entry_points?.length) {
        loadExecutionFlow(data.entry_points[0], data.repository_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function analyzeGithub() {
    if (!githubUrl) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/analyze/github`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: githubUrl }),
      });

      if (!response.ok) {
        throw new Error("Failed to analyze GitHub repository");
      }

      const data = await response.json();

      data.tree = addPaths(data.tree);

      const files = Object.keys(data.code_analysis);

      const functionCount = files.reduce(
        (total, file) => total + data.code_analysis[file].functions.length,
        0
      );

      const classCount = files.reduce(
        (total, file) => total + data.code_analysis[file].classes.length,
        0
      );

      const dependencyCount = Object.values(data.dependencies.forward).reduce(
        (total, dependencies) => total + dependencies.length,
        0
      );

      setStats({
        files: files.length,
        python: files.filter((file) => file.endsWith(".py")).length,
        functions: functionCount,
        classes: classCount,
        dependencies: dependencyCount,
      });

      setResult(data);

      if (data.entry_points?.length) {
        loadExecutionFlow(data.entry_points[0], data.repository_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openFile(filePath, line = null) {
    try {
      const relativePath = filePath.split("/").slice(1).join("/");

      const response = await fetch(
        `${API_URL}/file?repository_id=${result.repository_id}&file_path=${encodeURIComponent(relativePath)}`
      );

      if (!response.ok) {
        throw new Error("Failed to open file");
      }

      const data = await response.json();

      setSelectedFile(relativePath);
      setFileContent(data.content);
      setTargetLine(line);
      setHighlightLine(line);
      setFileAnalysis(result.code_analysis[relativePath]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadExecutionFlow(entryPoint, repositoryId) {
    try {
      const response = await fetch(
        `${API_URL}/repository/${repositoryId}/flow?entry_point=${encodeURIComponent(entryPoint)}`
      );

      if (!response.ok) {
        throw new Error("Failed to load execution flow");
      }

      const data = await response.json();

      setExecutionFlow(data.steps);
    } catch (err) {
      setError(err.message);
    }
  }

  async function searchRepository() {
    if (!searchQuery.trim() || !result) return;

    try {
      const response = await fetch(
        `${API_URL}/repository/${result.repository_id}/search?query=${encodeURIComponent(searchQuery)}`
      );

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const data = await response.json();

      setSearchResults(data.results);
    } catch (err) {
      setError(err.message);
    }
  }

  async function askCodebase() {
    if (!question.trim() || !result) return;

    setAsking(true);
    setAnswer("");

    try {
      const response = await fetch(
        `${API_URL}/repository/${result.repository_id}/ask?question=${encodeURIComponent(question)}`
      );

      if (!response.ok) {
        throw new Error("Failed to ask CodeLens");
      }

      const data = await response.json();

      setAnswer(data.answer);
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  }

  async function summarizeCodebase() {
    if (!result) return;

    setSummarizing(true);
    setSummary("");

    try {
      const response = await fetch(
        `${API_URL}/repository/${result.repository_id}/summary`
      );

      if (!response.ok) {
        throw new Error("Failed to summarize codebase");
      }

      const data = await response.json();
      setSummary(data.summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setSummarizing(false);
    }
  }

  useEffect(() => {
    if (!targetLine || !codeRef.current) return;

    const lineElement = codeRef.current.querySelector(
      `[data-line-number="${targetLine}"]`
    );

    lineElement?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [fileContent, targetLine]);

  return (
    <div className="app">
      <header>
        <h1>CodeLens</h1>
        <p>AI Codebase Analyst</p>
      </header>

      <section className="upload">
        <input
          type="file"
          accept=".zip"
          onChange={(e) => setFile(e.target.files[0])}
        />

        <button onClick={analyzeZip} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>

        {file && <span>{file.name}</span>}

        <input
          type="text"
          placeholder="GitHub repository URL"
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
        />

        <button onClick={analyzeGithub} disabled={loading}>
          Analyze GitHub
        </button>
      </section>

      {error && <div className="error">{error}</div>}

      {result && (
        <>
          <div className="repo-stats">
            <div>
              <strong>{stats?.files || 0}</strong>
              <span>Files</span>
            </div>

            <div className="architecture-panel">
              <h3>Architecture Overview</h3>

              <div className="architecture-grid">
                <div>
                  <strong>{result.architecture.file_count}</strong>
                  <span>Files</span>
                </div>

                <div>
                  <strong>{result.architecture.function_count}</strong>
                  <span>Functions</span>
                </div>

                <div>
                  <strong>{result.architecture.class_count}</strong>
                  <span>Classes</span>
                </div>

                <div>
                  <strong>{result.architecture.dependency_count}</strong>
                  <span>Dependencies</span>
                </div>

                <div>
                  <strong>{result.architecture.directory_count}</strong>
                  <span>Modules</span>
                </div>
              </div>

              <div className="architecture-section">
                <h4>Architecture Graph</h4>

                <ArchitectureGraph result={result} onFileClick={openFile} />
              </div>

              <div className="architecture-section">
                <h4>Entry Points</h4>

                {result.architecture.entry_points.length === 0 ? (
                  <p>None detected</p>
                ) : (
                  <ul>
                    {result.architecture.entry_points.map((file) => (
                      <li key={file}>{file}</li>
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
                    {result.architecture.functions.map((functionItem) => (
                      <li
                        key={`${functionItem.file}-${functionItem.name}`}
                        onClick={() =>
                          openFile(
                            `${result.tree.name}/${functionItem.file}`,
                            functionItem.line
                          )
                        }
                        style={{ cursor: "pointer" }}
                      >
                        {functionItem.name}() — {functionItem.file}:
                        {functionItem.line}
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
                    {result.architecture.classes.map((classItem) => (
                      <li
                        key={`${classItem.file}-${classItem.name}`}
                        onClick={() =>
                          openFile(
                            `${result.tree.name}/${classItem.file}`,
                            classItem.line
                          )
                        }
                        style={{ cursor: "pointer" }}
                      >
                        {classItem.name} — {classItem.file}:{classItem.line}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="architecture-section">
                <h4>Modules</h4>

                <ul>
                  {Object.entries(result.architecture.directories).map(
                    ([directory, files]) => (
                      <li key={directory}>
                        <strong>{directory}/</strong>

                        <ul>
                          {files.map((file) => (
                            <li
                              key={file}
                              onClick={() =>
                                openFile(`${result.tree.name}/${file}`)
                              }
                              style={{ cursor: "pointer" }}
                            >
                              {file}
                            </li>
                          ))}
                        </ul>
                      </li>
                    )
                  )}
                </ul>
              </div>

              <div className="architecture-section">
                <h4>Module Dependencies</h4>

                {result.architecture.dependencies.length === 0 ? (
                  <p>None detected</p>
                ) : (
                  <ul>
                    {result.architecture.dependencies.map(
                      (dependency, index) => (
                        <li
                          key={index}
                          onClick={() =>
                            openFile(`${result.tree.name}/${dependency.to}`)
                          }
                          style={{ cursor: "pointer" }}
                        >
                          {dependency.from} → {dependency.to}
                        </li>
                      )
                    )}
                  </ul>
                )}
              </div>
            </div>

            <div className="code-search">
              <input
                type="text"
                placeholder="Search codebase..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    searchRepository();
                  }
                }}
              />

              <button onClick={searchRepository}>Search</button>
            </div>

            {searchResults.length > 0 && (
              <div className="search-results">
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

                          openFile(
                            `${result.tree.name}/${item.file}`,
                            match.line
                          );
                        }}
                        style={{
                          cursor: match.line ? "pointer" : "default",
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
            <div className="project-summary">
              <h3>Project Understanding</h3>

              <button onClick={summarizeCodebase} disabled={summarizing}>
                {summarizing ? "Analyzing..." : "Understand Project"}
              </button>

              {summary && (
                <div className="codebase-answer">
                  <strong>CodeLens:</strong>
                  <p style={{ whiteSpace: "pre-wrap" }}>{summary}</p>
                </div>
              )}
            </div>

            <div className="ask-codebase">
              <h3>Ask Codebase</h3>

              <div>
                <input
                  type="text"
                  placeholder="Ask about this codebase..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      askCodebase();
                    }
                  }}
                />

                <button onClick={askCodebase} disabled={asking}>
                  {asking ? "Asking..." : "Ask"}
                </button>
              </div>

              {answer && (
                <div className="codebase-answer">
                  <strong>CodeLens:</strong>
                  <p>{answer}</p>
                </div>
              )}
            </div>

            <div>
              <strong>{stats?.python || 0}</strong>
              <span>Python</span>
            </div>

            <div>
              <strong>{stats?.functions || 0}</strong>
              <span>Functions</span>
            </div>

            <div>
              <strong>{stats?.classes || 0}</strong>
              <span>Classes</span>
            </div>

            <div>
              <strong>{stats?.dependencies || 0}</strong>
              <span>Dependencies</span>
            </div>
            <div>
              <strong>{result?.entry_points?.length || 0}</strong>
              <span>Entry Points</span>
            </div>
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
                              background: "rgba(97, 218, 251, 0.35)",
                              borderLeft: "3px solid #61dafb",
                              display: "block",
                            }
                          : undefined,
                    })}
                  >
                    {fileContent}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <p>Select a file from the repository.</p>
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
                          style={{
                            cursor: dependency ? "pointer" : "default",
                          }}
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
                        onClick={() =>
                          openFile(
                            `${result.tree.name}/${selectedFile}`,
                            item.line
                          )
                        }
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
                                openFile(
                                  `${result.tree.name}/${selectedFile}`,
                                  method.line
                                )
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
                      {Object.entries(
                        result.call_graph[selectedFile] || {}
                      ).map(([functionName, calls]) =>
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
                                typeof call.target_file === "string"
                                  ? "pointer"
                                  : "default",
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

              <h4>Execution Flow</h4>

              {executionFlow.length === 0 ? (
                <p>-</p>
              ) : (
                <ExecutionFlow
                  executionFlow={executionFlow}
                  onFileClick={openFile}
                />
              )}

              <h4>Dependencies</h4>

              {selectedFile && (
                <ul>
                  {(result.dependencies.forward[selectedFile] || []).map(
                    (file) => (
                      <li
                        key={file}
                        onClick={() => openFile(`${result.tree.name}/${file}`)}
                        style={{ cursor: "pointer" }}
                      >
                        {file}
                      </li>
                    )
                  )}
                </ul>
              )}

              <h4>Used By</h4>

              {selectedFile && (
                <ul>
                  {(result.dependencies.reverse[selectedFile] || []).map(
                    (file) => (
                      <li
                        key={file}
                        onClick={() => openFile(`${result.tree.name}/${file}`)}
                        style={{ cursor: "pointer" }}
                      >
                        {file}
                      </li>
                    )
                  )}
                </ul>
              )}
            </aside>

            <div className="graph-section">
              <h3>Dependency Graph</h3>
              <DependencyGraph
                result={result}
                onFileClick={openFile}
                selectedFile={selectedFile}
              />
            </div>
          </main>
        </>
      )}
    </div>
  );
}

export default App;
