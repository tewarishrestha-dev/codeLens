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
        label: file,
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

function App() {
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [result, setResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileAnalysis, setFileAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
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

                  <ul>
                    {(result.call_graph[selectedFile] || []).map(
                      (call, index) => (
                        <li
                          key={index}
                          onClick={() =>
                            openFile(
                              `${result.tree.name}/${call.target_file}`,
                              1
                            )
                          }
                          style={{ cursor: "pointer" }}
                        >
                          {call.function} → {call.calls} — line {call.line}
                        </li>
                      )
                    )}
                  </ul>
                </>
              ) : (
                <p>Select a file to inspect it.</p>
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
