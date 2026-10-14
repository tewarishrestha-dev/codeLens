// Normalizes any path-like value (string, or nested {file, line} / {path})
// to a repo-relative forward-slash path. The backend now emits forward
// slashes on every platform; this is a defensive guard for older payloads
// and for paths that arrive with backslashes from cached data.
export function toPosix(path) {
  return typeof path === "string" ? path.replace(/\\/g, "/") : path;
}

// Strips the repository-name prefix that tree/graph nodes carry
// ("<repoName>/pkg/main.py" -> "pkg/main.py") so the result is the
// repo-relative path the backend expects.
export function stripRepoPrefix(fullPath) {
  const posix = toPosix(fullPath);
  const segments = posix.split("/");

  return segments.length > 1 ? segments.slice(1).join("/") : posix;
}

export function addPaths(node, parentPath = "") {
  const path = parentPath ? `${parentPath}/${node.name}` : node.name;

  return {
    ...node,
    path,
    children: node.children?.map((child) => addPaths(child, path)),
  };
}

export function getLanguage(filePath) {
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

export function computeStats(data) {
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

  return {
    files: files.length,
    python: files.filter((file) => file.endsWith(".py")).length,
    functions: functionCount,
    classes: classCount,
    dependencies: dependencyCount,
  };
}
