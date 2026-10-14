import { useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";

/* ------------------------------------------------------------------ *
 * Node type system
 * Nodes are colour-coded by role: entry point (violet), source file
 * (blue), utility module (cyan), and execution-flow terminus (green).
 * The kind also drives a text chip so meaning never depends on colour
 * alone.
 * ------------------------------------------------------------------ */

const KIND_LABELS = {
  entry: "ENTRY",
  module: "SRC",
  utility: "UTIL",
};

const UTILITY_WORDS = new Set([
  "util",
  "utils",
  "utility",
  "helper",
  "helpers",
  "tool",
  "tools",
  "common",
  "lib",
  "libs",
  "const",
  "constants",
  "config",
  "configs",
  "shared",
]);

const MAX_VISIBLE_MEMBERS = 3;

function classifyFile(relativePath, entryPoints) {
  if (entryPoints.has(relativePath)) return "entry";

  const segments = relativePath.split("/");
  const stem = segments[segments.length - 1].replace(/\.[^.]+$/, "");
  const inUtilityDir = segments
    .slice(0, -1)
    .some((segment) => UTILITY_WORDS.has(segment.toLowerCase()));
  const namedUtility = stem
    .split(/[_\-.]/)
    .some((part) => UTILITY_WORDS.has(part.toLowerCase()));

  return inUtilityDir || namedUtility ? "utility" : "module";
}

function buildEntrySet(result) {
  return new Set([
    ...(result.entry_points || []),
    ...(result.architecture.entry_points || []),
  ]);
}

function buildMemberIndex(architecture) {
  const index = new Map();

  const push = (file, member) => {
    const list = index.get(file) || [];
    list.push(member);
    index.set(file, list);
  };

  architecture.functions.forEach((fn) =>
    push(fn.file, { type: "function", name: fn.name })
  );
  architecture.classes.forEach((cls) =>
    push(cls.file, { type: "class", name: cls.name })
  );

  return index;
}

// Rough monospace metrics, used only to feed dagre so ranks do not
// overlap. The real DOM size is measured by React Flow afterwards.
function measureFileNode(fileName, directory, memberCount) {
  const width = Math.min(272, Math.max(176, Math.ceil(fileName.length * 7.6) + 52));
  const charsPerLine = Math.max(14, Math.floor((width - 40) / 7.6));
  const nameLines = Math.max(1, Math.ceil(fileName.length / charsPerLine));
  const memberLines =
    Math.min(memberCount, MAX_VISIBLE_MEMBERS) +
    (memberCount > MAX_VISIBLE_MEMBERS ? 1 : 0);
  const height = 22 + nameLines * 16 + (directory ? 15 : 0) + memberLines * 15;

  return { width, height: Math.max(54, height) };
}

function measureStepNode(file, fn) {
  const width = 228;
  const charsPerLine = Math.max(14, Math.floor((width - 44) / 7.6));
  const fileLines = Math.max(1, Math.ceil(file.length / charsPerLine));
  const fnLines = fn ? Math.max(1, Math.ceil((fn.length + 3) / charsPerLine)) : 0;

  return { width, height: Math.max(56, 22 + fileLines * 16 + fnLines * 15) };
}

/* ------------------------------------------------------------------ *
 * Node components
 * ------------------------------------------------------------------ */

function CodeFileNode({ data }) {
  const { kind, kindLabel, fileName, directory, members, memberTotal } = data;

  return (
    <div className={`gnode gnode--file gnode--${kind}`}>
      <div className="gnode__head">
        <span className="gnode__chip">
          <span className="gnode__chip-dot" aria-hidden="true" />
          {kindLabel}
        </span>
        <span className="gnode__name" title={fileName}>
          {fileName}
        </span>
      </div>

      {directory && (
        <div className="gnode__dir" title={`${directory}/`}>
          {directory}/
        </div>
      )}

      {members.length > 0 && (
        <ul className="gnode__members">
          {members.map((member) => (
            <li
              key={`${member.type}-${member.name}`}
              className={member.type === "class" ? "is-class" : undefined}
            >
              {member.type === "class" ? (
                `class ${member.name}`
              ) : (
                <>
                  <span className="gnode__sig" aria-hidden="true">
                    ƒ
                  </span>
                  {member.name}()
                </>
              )}
            </li>
          ))}
          {memberTotal > members.length && (
            <li className="gnode__more">
              +{memberTotal - members.length} more
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function FlowStepNode({ data }) {
  const { kind, badge, file, fn, line } = data;

  return (
    <div className={`gnode gnode--step gnode--${kind}`}>
      <div className="gnode__head">
        <span className="gnode__chip">
          <span className="gnode__chip-dot" aria-hidden="true" />
          {badge}
        </span>
        <span className="gnode__name" title={file}>
          {file}
        </span>
      </div>

      {(fn || typeof line === "number") && (
        <div className="gnode__step">
          {fn && (
            <span className="gnode__fn" title={fn}>
              ƒ {fn}()
            </span>
          )}
          {typeof line === "number" && (
            <span className="gnode__line">L{line}</span>
          )}
        </div>
      )}
    </div>
  );
}

const nodeTypes = { codeFile: CodeFileNode, flowStep: FlowStepNode };

/* ------------------------------------------------------------------ *
 * Shared canvas
 * ------------------------------------------------------------------ */

function GraphCanvas({
  flowKey,
  nodes,
  edges,
  onNodeClick,
  onNodeEnter,
  onNodeLeave,
}) {
  return (
    <div className="graph-canvas">
      <ReactFlow
        key={flowKey}
        nodes={nodes}
        edges={edges}
        onNodeClick={onNodeClick}
        onNodeMouseEnter={onNodeEnter}
        onNodeMouseLeave={onNodeLeave}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1.1 }}
        minZoom={0.15}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        defaultMarkerColor="var(--paper-faint)"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={26}
          size={1.3}
          color="var(--line-strong)"
          bgColor="transparent"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function arrowMarker(color) {
  return {
    type: MarkerType.ArrowClosed,
    width: 9,
    height: 9,
    color,
  };
}

/* ------------------------------------------------------------------ *
 * Dependency graph (imports, left-to-right dagre layout)
 * ------------------------------------------------------------------ */

function buildDependencyModel(result) {
  const forward = result.dependencies.forward || {};
  const reverse = result.dependencies.reverse || {};
  const files = Object.keys(forward);
  const entryPoints = buildEntrySet(result);
  const memberIndex = buildMemberIndex(result.architecture);

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 72, ranksep: 150 });

  const meta = {};

  files.forEach((file) => {
    const members = memberIndex.get(file) || [];
    const base = file.split("/").pop();
    const slash = file.lastIndexOf("/");
    const directory = slash > 0 ? file.slice(0, slash) : "";
    const kind = classifyFile(file, entryPoints);
    const { width, height } = measureFileNode(base, directory, members.length);

    meta[file] = {
      base,
      directory,
      kind,
      kindLabel: KIND_LABELS[kind],
      members: members.slice(0, MAX_VISIBLE_MEMBERS),
      memberTotal: members.length,
      width,
      height,
    };

    graph.setNode(file, { width, height });
  });

  const pairs = [];
  const seen = new Set();

  files.forEach((file) => {
    (forward[file] || []).forEach((dependency) => {
      const id = `${file}->${dependency}`;
      if (seen.has(id) || !graph.hasNode(dependency)) return;
      seen.add(id);
      pairs.push({ source: file, target: dependency });
      graph.setEdge(file, dependency);
    });
  });

  dagre.layout(graph);

  const positions = {};
  files.forEach((file) => {
    const position = graph.node(file);
    positions[file] = {
      x: position.x - meta[file].width / 2,
      y: position.y - meta[file].height / 2,
    };
  });

  return { files, forward, reverse, meta, positions, pairs, entryPoints };
}

export function DependencyGraph({ result, onFileClick, selectedFile }) {
  const [hoveredId, setHoveredId] = useState(null);
  const model = useMemo(() => buildDependencyModel(result), [result]);

  const related = useMemo(() => {
    if (!selectedFile) return null;
    const set = new Set([selectedFile]);
    (model.forward[selectedFile] || []).forEach((file) => set.add(file));
    (model.reverse[selectedFile] || []).forEach((file) => set.add(file));
    return set;
  }, [model, selectedFile]);

  const nodes = useMemo(
    () =>
      model.files.map((file) => {
        const info = model.meta[file];
        const dimmed = related !== null && !related.has(file);

        return {
          id: file,
          type: "codeFile",
          position: model.positions[file],
          ariaLabel: `${info.kindLabel} file ${file}`,
          className: dimmed ? "is-dim" : undefined,
          data: {
            kind: info.kind,
            kindLabel: info.kindLabel,
            fileName: info.base,
            directory: info.directory,
            members: info.members,
            memberTotal: info.memberTotal,
          },
        };
      }),
    [model, related]
  );

  const edges = useMemo(
    () =>
      model.pairs.map(({ source, target }) => {
        const incident =
          related === null || source === selectedFile || target === selectedFile;
        const active = related !== null && incident;
        const entryFlow = model.entryPoints.has(source);
        const hot =
          hoveredId !== null &&
          (source === hoveredId || target === hoveredId);

        const classes = ["gedge", "gedge--dep"];
        if (active) classes.push("is-active");
        if (!incident) classes.push("is-dim");
        if (entryFlow && !active) classes.push("is-entry-flow");
        if (hot) classes.push("is-hot");

        return {
          id: `dep:${source}->${target}`,
          source,
          target,
          className: classes.join(" "),
          ariaLabel: `${source} depends on ${target}`,
          markerEnd: arrowMarker(
            active ? "var(--signal)" : "var(--paper-faint)"
          ),
        };
      }),
    [model, related, selectedFile, hoveredId]
  );

  return (
    <GraphCanvas
      flowKey={result.tree.name}
      nodes={nodes}
      edges={edges}
      onNodeClick={(_event, node) => {
        onFileClick(`${result.tree.name}/${node.id}`);
      }}
      onNodeEnter={(_event, node) => setHoveredId(node.id)}
      onNodeLeave={() => setHoveredId(null)}
    />
  );
}

/* ------------------------------------------------------------------ *
 * Architecture graph (module-level dependencies, same LR layout)
 * ------------------------------------------------------------------ */

function buildArchitectureModel(result) {
  const files = result.architecture.files || [];
  const directories = result.architecture.directories || {};
  const memberIndex = buildMemberIndex(result.architecture);
  const entryPoints = buildEntrySet(result);

  const dirByFile = {};
  Object.entries(directories).forEach(([directory, dirFiles]) => {
    if (directory === "root") return;
    dirFiles.forEach((file) => {
      dirByFile[file] = directory;
    });
  });

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 72, ranksep: 150 });

  const meta = {};

  files.forEach((file) => {
    const members = memberIndex.get(file) || [];
    const base = file.split("/").pop();
    const directory = dirByFile[file] || "";
    const kind = classifyFile(file, entryPoints);
    const { width, height } = measureFileNode(base, directory, members.length);

    meta[file] = {
      base,
      directory,
      kind,
      kindLabel: KIND_LABELS[kind],
      members: members.slice(0, MAX_VISIBLE_MEMBERS),
      memberTotal: members.length,
      width,
      height,
    };

    graph.setNode(file, { width, height });
  });

  const pairs = [];
  const seen = new Set();

  (result.architecture.dependencies || []).forEach((dependency) => {
    const { from, to } = dependency;
    const id = `${from}->${to}`;
    if (seen.has(id) || !graph.hasNode(from) || !graph.hasNode(to)) return;
    seen.add(id);
    pairs.push({ source: from, target: to });
    graph.setEdge(from, to);
  });

  dagre.layout(graph);

  const positions = {};
  files.forEach((file) => {
    const position = graph.node(file);
    positions[file] = {
      x: position.x - meta[file].width / 2,
      y: position.y - meta[file].height / 2,
    };
  });

  return { files, meta, positions, pairs, entryPoints };
}

export function ArchitectureGraph({ result, onFileClick, selectedFile }) {
  const [hoveredId, setHoveredId] = useState(null);
  const model = useMemo(() => buildArchitectureModel(result), [result]);

  const nodes = useMemo(
    () =>
      model.files.map((file) => {
        const info = model.meta[file];
        const dimmed =
          selectedFile !== null &&
          selectedFile !== undefined &&
          file !== selectedFile &&
          !model.pairs.some(
            (pair) =>
              (pair.source === selectedFile && pair.target === file) ||
              (pair.target === selectedFile && pair.source === file)
          );

        return {
          id: file,
          type: "codeFile",
          position: model.positions[file],
          ariaLabel: `${info.kindLabel} file ${file}`,
          className: dimmed ? "is-dim" : undefined,
          data: {
            kind: info.kind,
            kindLabel: info.kindLabel,
            fileName: info.base,
            directory: info.directory,
            members: info.members,
            memberTotal: info.memberTotal,
          },
        };
      }),
    [model, selectedFile]
  );

  const edges = useMemo(
    () =>
      model.pairs.map(({ source, target }) => {
        const active =
          selectedFile !== null &&
          selectedFile !== undefined &&
          (source === selectedFile || target === selectedFile);
        const dim =
          selectedFile !== null &&
          selectedFile !== undefined &&
          !active;
        const entryFlow = model.entryPoints.has(source);
        const hot =
          hoveredId !== null &&
          (source === hoveredId || target === hoveredId);

        const classes = ["gedge", "gedge--dep"];
        if (active) classes.push("is-active");
        if (dim) classes.push("is-dim");
        if (entryFlow && !active) classes.push("is-entry-flow");
        if (hot) classes.push("is-hot");

        return {
          id: `arch:${source}->${target}`,
          source,
          target,
          className: classes.join(" "),
          ariaLabel: `${source} depends on ${target}`,
          markerEnd: arrowMarker(
            active ? "var(--signal)" : "var(--paper-faint)"
          ),
        };
      }),
    [model, selectedFile, hoveredId]
  );

  return (
    <GraphCanvas
      flowKey={result.tree.name}
      nodes={nodes}
      edges={edges}
      onNodeClick={(_event, node) => {
        onFileClick(`${result.tree.name}/${node.id}`);
      }}
      onNodeEnter={(_event, node) => setHoveredId(node.id)}
      onNodeLeave={() => setHoveredId(null)}
    />
  );
}

/* ------------------------------------------------------------------ *
 * Execution flow (entry-point call order, top-to-bottom)
 * ------------------------------------------------------------------ */

function buildFlowModel(executionFlow) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "TB", nodesep: 44, ranksep: 64 });

  const measures = executionFlow.map((step) =>
    measureStepNode(step.file, step.function)
  );

  executionFlow.forEach((_step, index) => {
    graph.setNode(String(index), measures[index]);
  });

  for (let index = 0; index < executionFlow.length - 1; index += 1) {
    graph.setEdge(String(index), String(index + 1));
  }

  dagre.layout(graph);

  const positions = executionFlow.map((_step, index) => {
    const position = graph.node(String(index));
    const { width, height } = measures[index];
    return { x: position.x - width / 2, y: position.y - height / 2 };
  });

  return { positions, measures };
}

export function ExecutionFlow({
  executionFlow,
  onFileClick,
  repoName,
  selectedFile,
}) {
  const model = useMemo(
    () => buildFlowModel(executionFlow),
    [executionFlow]
  );

  const selectedStep = useMemo(() => {
    if (!selectedFile) return -1;
    return executionFlow.findIndex((step) => step.file === selectedFile);
  }, [executionFlow, selectedFile]);

  const stepCount = executionFlow.length;

  const nodes = useMemo(
    () =>
      executionFlow.map((step, index) => {
        const kind =
          index === 0 ? "entry" : index === stepCount - 1 ? "end" : "module";
        const badge =
          index === 0
            ? "START"
            : index === stepCount - 1
              ? "END"
              : String(index + 1).padStart(2, "0");
        const dimmed = selectedStep >= 0 && index !== selectedStep;

        return {
          id: String(index),
          type: "flowStep",
          position: model.positions[index],
          ariaLabel: `Execution step ${index + 1}: ${step.file}${
            step.function ? ` → ${step.function}` : ""
          }`,
          className: dimmed ? "is-dim" : undefined,
          data: {
            kind,
            badge,
            file: step.file,
            fn: step.function,
            line: step.line,
          },
        };
      }),
    [executionFlow, model, selectedStep, stepCount]
  );

  const edges = useMemo(
    () =>
      executionFlow.slice(1).map((_step, index) => {
        const active =
          selectedStep >= 0 &&
          (index === selectedStep - 1 || index + 1 === selectedStep);
        const dim = selectedStep >= 0 && !active;

        const classes = ["gedge", "gedge--flow"];
        if (active) classes.push("is-active");
        if (dim) classes.push("is-dim");

        return {
          id: `flow:${index}`,
          source: String(index),
          target: String(index + 1),
          type: "smoothstep",
          className: classes.join(" "),
          ariaLabel: `Step ${index + 1} to step ${index + 2}`,
          markerEnd: arrowMarker(
            active ? "var(--signal)" : "var(--signal-3)"
          ),
          // Staggered negative delays make the chain read as a sequence
          // travelling from START to END rather than a simultaneous pulse.
          style: { animationDelay: `${index * -0.32}s` },
        };
      }),
    [executionFlow, selectedStep]
  );

  return (
    <GraphCanvas
      flowKey={repoName}
      nodes={nodes}
      edges={edges}
      onNodeClick={(_event, node) => {
        const step = executionFlow[Number(node.id)];

        // step.file is repo-relative (e.g. "pkg/main.py"), so it must be
        // prefixed with the repo name before passing to onFileClick,
        // which strips that prefix. Previously the prefix was missing and
        // the first path segment was silently dropped.
        onFileClick(`${repoName}/${step.file}`, step.line);
      }}
    />
  );
}
