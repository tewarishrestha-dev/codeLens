import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function FileTree({ node, onFileClick }) {
  const [open, setOpen] = useState(false);

  if (node.type === "file") {
    return (
      <div className="file" onClick={() => onFileClick(node.path)}>
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
          />
        ))}
    </div>
  );
}

function addPaths(node, parentPath = "") {
  const path = parentPath
    ? `${parentPath}/${node.name}`
    : node.name;

  return {
    ...node,
    path,
    children: node.children?.map((child) =>
      addPaths(child, path)
    ),
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

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileAnalysis, setFileAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openFile(filePath) {
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
      setFileAnalysis(result.code_analysis[relativePath]);
    } catch (err) {
      setError(err.message);
    }
  }

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
      </section>

      {error && <div className="error">{error}</div>}

      {result && (
        <main className="workspace">

          <aside className="panel tree-panel">
            <h3>{result.name}</h3>

            <FileTree
              node={result.tree}
              onFileClick={openFile}
            />
          </aside>

          <section className="panel code-panel">
            <h3>{selectedFile || "Select a file"}</h3>

            {selectedFile ? (
              <SyntaxHighlighter
                language={getLanguage(selectedFile)}
                style={vscDarkPlus}
                showLineNumbers
                wrapLongLines={false}
              >
                {fileContent}
              </SyntaxHighlighter>
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
                  {fileAnalysis.imports.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                <h4>Functions</h4>
                <ul>
                  {fileAnalysis.functions.map((item) => (
                    <li key={item.name}>
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
                          <li key={method.name}>
                            {method.name}()
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>

                <h4>Calls</h4>
                <ul>
                  {fileAnalysis.calls.map((call, index) => (
                    <li key={index}>
                      {call.function} → {call.calls}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Select a file to inspect it.</p>
            )}
          </aside>

        </main>
      )}
    </div>
  );
}

export default App;