import { useState } from "react";
import { stripRepoPrefix } from "../repoUtils";

export function FileTree({ node, onFileClick, selectedFile, depth = 0 }) {
  // null = follow auto-open (folder containing the selected file opens itself).
  // A manual click overrides until the selection moves into this folder again.
  const [userOpen, setUserOpen] = useState(null);
  const [prevSelected, setPrevSelected] = useState(selectedFile);
  const indent = { paddingLeft: 6 + depth * 13 };

  if (node.type === "file") {
    const isSelected = stripRepoPrefix(node.path) === selectedFile;

    return (
      <div
        className={`file ${isSelected ? "selected" : ""}`}
        style={indent}
        onClick={() => onFileClick(node.path)}
      >
        {node.name}
      </div>
    );
  }

  const containsSelected =
    selectedFile?.startsWith(stripRepoPrefix(node.path) + "/") ?? false;

  // Adjust during render (React's sanctioned alternative to a reset effect):
  // when selection enters this folder, clear any manual override so it opens.
  if (selectedFile !== prevSelected) {
    setPrevSelected(selectedFile);

    if (containsSelected) {
      setUserOpen(null);
    }
  }

  const open = userOpen ?? containsSelected;

  return (
    <div>
      <div className="folder" style={indent} onClick={() => setUserOpen(!open)}>
        <span className="folder-toggle" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
        {node.name}
      </div>

      {open &&
        node.children?.map((child) => (
          <FileTree
            key={child.path}
            node={child}
            onFileClick={onFileClick}
            selectedFile={selectedFile}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}
