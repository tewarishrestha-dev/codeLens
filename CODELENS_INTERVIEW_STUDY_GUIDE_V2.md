# CodeLens: Comprehensive Interview Study Guide (Post-Upgrade Edition)
**Author:** @Shrestha Tewari &nbsp;|&nbsp; **Updated:** November 2026 &nbsp;|&nbsp; **Architecture Level:** Senior Full-Stack & Systems / AI Engineer

---

## Table of Contents
1. [The Big Picture & The Problem It Solves](#1-the-big-picture--the-problem-it-solves)
2. [The 30-Second Elevator Pitch (Memorize This)](#2-the-30-second-elevator-pitch-memorize-this)
3. [Summary of Major Architectural Changes (Before vs. After)](#3-summary-of-major-architectural-changes-before-vs-after)
4. [Every File, One Line Each (Complete Project Map)](#4-every-file-one-line-each-complete-project-map)
5. [The Four Core Journeys Through the System](#5-the-four-core-journeys-through-the-system)
6. [Part 1: API Gateway & HTTP Routing (`backend/app/main.py`)](#part-1-api-gateway--http-routing-backendappmainpy)
7. [Part 2: Ingest & Security Guard (`github_service.py`, `zip_service.py`, `file_reader.py`)](#part-2-ingest--security-guard)
8. [Part 3: Python AST Parser (`code_parser.py`, `repository_parser.py`)](#part-3-python-ast-parser)
9. [Part 4: JavaScript & TypeScript Parser (`js_parser.py`) — NEW](#part-4-javascript--typescript-parser-js_parserpy--new)
10. [Part 5: Dependency Analyzer with 4-Tier Fallback (`dependency_analyzer.py`) — UPGRADED](#part-5-dependency-analyzer-with-4-tier-fallback-dependency_analyzerpy--upgraded)
11. [Part 6: Call Graph & Execution Flow DFS (`call_analyzer.py`, `repository_analyzer.py`)](#part-6-call-graph--execution-flow-dfs)
12. [Part 7: Scanner, Architecture Summary & Entry Point Detection](#part-7-scanner-architecture-summary--entry-point-detection)
13. [Part 8: Persistence & Workspace Store (`repository_store.py`)](#part-8-persistence--workspace-store-repository_storepy)
14. [Part 9: Code Search & Lexical Retrieval (`code_search.py`)](#part-9-code-search--lexical-retrieval-code_searchpy)
15. [Part 10: Context Builder & Brace-Aware Code Slicing (`context_builder.py`)](#part-10-context-builder--brace-aware-code-slicing-context_builderpy)
16. [Part 11: Multi-Provider LLM Engine & Citation Verifier (`llm_service.py`) — UPGRADED](#part-11-multi-provider-llm-engine--citation-verifier-llm_servicepy--upgraded)
17. [Part 12: Modern Frontend Architecture & Graph Studio (`frontend/src/`) — UPGRADED](#part-12-modern-frontend-architecture--graph-studio-frontendsrc--upgraded)
18. [Part 13: Cloud Deployment, Docker & Render (`render.yaml`, `DEPLOYMENT.md`) — NEW](#part-13-cloud-deployment-docker--render-renderyaml-deploymentmd--new)
19. [Part 14: Automated Testing & Test Suite Architecture](#part-14-automated-testing--test-suite-architecture)
20. [Part 15: The Weakness-Fix Matrix (Interview Stories: Before vs. After)](#part-15-the-weakness-fix-matrix-interview-stories-before-vs-after)
21. [Part 16: Honest Limits & What to Say Like a Senior Engineer](#part-16-honest-limits--what-to-say-like-a-senior-engineer)
22. [Part 17: Claims You Can Make vs. Claims You Must Never Make](#part-17-claims-you-can-make-vs-claims-you-must-never-make)
23. [Part 18: Master Interview Question Bank with High-Scoring Answers](#part-18-master-interview-question-bank-with-high-scoring-answers)

---

## 1. The Big Picture & The Problem It Solves

### The Big Picture
**CodeLens** is a multi-language codebase comprehension platform. It ingests any Python or JavaScript/TypeScript repository (via GitHub URL or ZIP archive), analyzes its internal architecture **without executing the code** (static analysis), draws interactive dependency and execution flow graphs, and provides a grounded, citation-validated AI companion powered by local or cloud LLMs.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                CODELENS PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [ INGESTION ]         [ STATIC PARSERS ]             [ ARCHITECTURE MAPS ]     │
│  - GitHub ZIP          - Python (ast module)          - File Dependency Graph   │
│  - File Upload         - JS/TS (Regex Tokenizer)      - Function Call Graph     │
│  - Path Traversal      - Class / Func / Imports       - Execution Flow (DFS)    │
│    Guards                                             - 4-Tier Import Fallback  │
│         │                      │                                │               │
│         └──────────────────────┼────────────────────────────────┘               │
│                                ▼                                                │
│                 [ PERSISTENCE & CACHE ENGINE ]                                  │
│                 - In-Memory Fast Lookup                                         │
│                 - Atomic Write JSON Index                                       │
│                 - Thread-Safe Reentrant Lock                                    │
│                                │                                                │
│         ┌──────────────────────┴────────────────────────────────┐               │
│         ▼                                                       ▼               │
│  [ RETRIEVAL & GROUNDED AI ]                     [ FRONTEND GRAPH STUDIO ]      │
│  - Lexical Keyword Search                        - React 19 + Vite + Dagre      │
│  - Subclass Inheritance Expansion                - Obsidian Glass Nodes         │
│  - Brace-Aware Indentation Slicing               - RankDir Toggles (LR vs TB)   │
│  - Multi-Provider (Ollama, Gemini, Groq, OpenAI) - Connected & Test Filtering   │
│  - Citation & Grounding Post-Verifier            - Slide-Out AI Companion       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### The Problem It Solves
When a developer joins a team or inspects an open-source codebase of 200+ files:
1. **Cognitive Overload:** Where is the starting point? Which module orchestrates what?
2. **Hidden Blast Radius:** If I modify `file_reader.py` or `models.py`, which 15 files will break?
3. **AI Hallucinations:** Asking ChatGPT or generic tools about private or complex code results in fabricated function names and bogus line numbers.

CodeLens solves this by:
- Statically mapping architecture deterministically without installing dependencies or running untrusted code.
- Building an execution trace from entry points to leaf utilities.
- Enforcing strict lexical grounding: answers cite exact lines (`[file:line]`), and a post-validation engine verifies whether cited lines exist and contain the claims made.

---

## 2. The 30-Second Elevator Pitch (Memorize This)

> *"CodeLens is a static codebase analysis and grounded AI exploration platform for Python and JavaScript/TypeScript repositories. It ingests projects from GitHub URLs or ZIPs and extracts imports, functions, classes, and calls using Python's `ast` module and a custom JS/TS tokenizer—never executing untrusted code.*
>
> *I map relationships using a 4-tier dependency resolution engine, build function call graphs, and trace execution flows from heuristically identified entry points via Depth-First Search. This is visualized in a React Flow and Dagre graph studio with obsidian glass aesthetics, dynamic filtering, and orientation toggles.*
>
> *For questions, I use deterministic lexical retrieval with class inheritance expansion, slice code with brace and indentation awareness, and feed the context to a multi-provider LLM engine supporting local Ollama, Google Gemini, Groq, or OpenAI. Finally, a post-generation citation engine validates that every cited line and identifier exists in the context before presenting the answer to the user."*

---

## 3. Summary of Major Architectural Changes (Before vs. After)

In your interview, showing **how the system evolved** demonstrates engineering maturity, debugging capability, and architectural foresight.

| Feature / Area | Before (Previous Version) | After (Current Upgraded Version) |
|---|---|---|
| **Language Support** | Python only (`.py` files via standard `ast` module). | **Multi-Language**: Python + JavaScript, TypeScript, JSX, TSX, MJS, CJS via new `js_parser.py`. |
| **LLM Providers** | Local Ollama only (`qwen2.5-coder:3b` at `127.0.0.1:11434`). Hard failure if Ollama was down. | **Multi-Provider Engine**: Local Ollama + Cloud **Google Gemini**, **Groq** (Llama 3.3 70B), **OpenAI**, and custom base URLs. |
| **API Key & Model Selection** | Hardcoded environment variables only. Server restart needed to switch. | **Dynamic Per-Request Overrides**: Extracted from HTTP headers (`x-llm-provider`, `x-api-key`, `x-llm-model`) and configurable via UI Settings. |
| **Dependency Resolution** | Rigid exact-path matching. Failed on package imports; only **11 of 31** files resolved dependencies. | **4-Tier Fallback Resolver**: (1) same-dir, (2) parent-package, (3) unique suffix, (4) extension matching. Tested and verified on complex packages. |
| **Entry Point Detection** | 4 hardcoded Python names (`main.py`, `app.py`, `server.py`, `manage.py`). | Extended to `__init__.py`, `cli.py`, `core.py`, `wsgi.py`, `asgi.py`, `index.js/ts`, `app.js/ts`, plus automatic top-level package fallback. |
| **Code Slicing** | Indentation-only scan; broke on multi-line signatures (Black format) and non-Python code. | **Brace-Aware Depth Tracker**: Supports C-style/JS/TS braces `{}` + Python AST line boundaries. |
| **Cloud Deployment** | Local Docker Compose only, hardcoded Windows path `E:/CodeLensData`. | **Render Cloud Blueprint (`render.yaml`)**: Web Service for FastAPI, Static Site for Vite React, dynamic backend override in `api.js`. |
| **Frontend UI/UX** | Monolithic single-page layout, basic React Flow rendering. | **Full Redesign**: AW Media-inspired Landing Page, Glowing Cursor, Auth Modal, Lenis Smooth Scroll, 3-column Command Center, obsidian glass nodes, LR/TB toggles, search in graph. |
| **AI Companion** | Inline text output with raw error traces on connection failures. | **Collapsible AI Companion Drawer**: Grounded citation pills, unverified claim warnings, copy actions, and friendly fallback diagnostics. |
| **Automated Tests** | 74 unit tests passing, but 4 broken scratch scripts with hardcoded local Windows paths. | **76+ Passing Automated Tests** across 8 structured test suites (`unittest`), with dedicated JS parsing and persistence suites. |

---

## 4. Every File, One Line Each (Complete Project Map)

### Backend (`/backend/app`)
| Layer | File | One-Line Purpose |
|---|---|---|
| **HTTP** | `main.py` | FastAPI application gateway, route handlers, error translators (404/410/503), and CORS configuration. |
| **Ingest** | `github_service.py` | Fetches a GitHub repository archive via public ZIP stream (main/master) and unpacks safely. |
| **Ingest** | `zip_service.py` | Extracts an uploaded `.zip` into an isolated temporary folder. |
| **Security** | `file_reader.py` | Reads files from disk with strict path traversal verification (`is_relative_to`) and UTF-8-BOM normalization. |
| **Analysis** | `repository_scanner.py` | Recursively scans workspace directories to construct the nested file tree for the UI explorer. |
| **Analysis** | `repository_parser.py` | Orchestrates multi-language parsing across all files, ignoring caches and virtualenvs. |
| **Analysis** | `code_parser.py` | Parses Python files into imports, functions, classes, and calls using Python's `ast` module. |
| **Analysis** | `js_parser.py` *(NEW)* | Regex-based parser extracting imports, classes, functions, arrow methods, and calls from JS/TS code. |
| **Analysis** | `dependency_analyzer.py` *(UPGRADED)* | Constructs forward and reverse dependency graphs using 4-tier fallback path resolution. |
| **Analysis** | `call_analyzer.py` | Builds caller-callee relationship graph and traces sequential execution flow using DFS. |
| **Analysis** | `architecture_analyzer.py` | Aggregates summary metrics (file counts, function counts, directories, entry points) for the UI. |
| **Analysis** | `repository_analyzer.py` *(UPGRADED)* | The conductor function `analyze_repository` executing all scanning and graph stages in order. |
| **State** | `repository_store.py` | Thread-safe workspace manager using an in-memory cache and atomic JSON metadata persistence. |
| **Retrieval** | `code_search.py` | Deterministic lexical search engine featuring whole-word matching and class inheritance expansion. |
| **Retrieval** | `context_builder.py` *(UPGRADED)* | Slices relevant functions with brace-depth and line caps, compiling line-numbered prompt bundles. |
| **AI Engine** | `llm_service.py` *(UPGRADED)* | Multi-provider LLM dispatcher (Ollama/Gemini/Groq/OpenAI) with lexical citation and grounding verification. |
| **Models** | `models/github.py` | Pydantic schema validating GitHub repository ingestion payloads (`url: str`). |

### Frontend (`/frontend/src`)
| Layer | File | One-Line Purpose |
|---|---|---|
| **Entry** | `main.jsx` / `App.jsx` | Application bootstrap, view switching, Lenis smooth scrolling, and global state container. |
| **Networking**| `api.js` *(NEW)* | Fetch wrapper handling dynamic backend URL overrides and injecting `x-llm-*` headers. |
| **Component** | `components/Graphs.jsx` *(UPGRADED)*| React Flow + Dagre visualization with obsidian glass nodes, RankDir (LR/TB), and filter controls. |
| **Component** | `components/AiCompanion.jsx` *(NEW)*| Slide-out AI assistant drawer displaying verified citations, unverified claims, and code context. |
| **Component** | `components/LandingPage.jsx` *(NEW)*| Visual presentation landing page featuring AW Media aesthetics and feature highlights. |
| **Component** | `components/AuthModal.jsx` *(NEW)*| Glassmorphism modal interface for user authentication and onboarding. |
| **Component** | `components/GlowingCursor.jsx` *(NEW)*| Smooth trailing canvas mouse light effect with acceleration physics. |
| **Component** | `components/Atmosphere.jsx` *(NEW)*| Ambient background gradients and visual glass effects. |
| **Page** | `pages/HomePage.jsx` *(UPGRADED)*| 3-column Command Center dashboard for repository selection, upload, and status metrics. |
| **Page** | `pages/ExplorerPage.jsx` | Integrated workspace combining the file tree, interactive code editor, and Graph Studio. |
| **Page** | `pages/AskPage.jsx` | Full-screen Q&A workspace for codebase reasoning and architectural queries. |
| **Page** | `pages/SettingsPage.jsx` *(UPGRADED)*| Configuration panel for selecting LLM providers (Ollama/Gemini/Groq/OpenAI) and API keys. |
| **Page** | `pages/RepositoriesPage.jsx`| Saved workspace manager for browsing, inspecting, and deleting stored repositories. |

---

## 5. The Four Core Journeys Through the System

### Journey A: Ingest and Analyze a Repository (`POST /analyze/github` or `POST /analyze/zip`)
1. **Download/Unpack:** `github_service.py` fetches the branch ZIP into an isolated `mkdtemp` folder; `zip_service.py` writes uploaded bytes to a temp file and extracts.
2. **Scan Directory Tree:** `repository_scanner.py` traverses directory entries, skipping build caches (`.git`, `node_modules`, `__pycache__`), and flags viewable source files.
3. **Multi-Language Parse:** `repository_parser.py` iterates over every file. If `.py`, it delegates to `code_parser.py` (AST). If `.js`, `.ts`, `.jsx`, `.tsx`, it delegates to `js_parser.py` (Regex Tokenizer).
4. **Dependency Resolution:** `dependency_analyzer.py` runs the 4-tier fallback matching across all extracted imports to build the forward and reverse file dependency graphs.
5. **Call Graph & Flow:** `call_analyzer.py` indexes all defined functions, resolves caller-callee links (flagging ambiguous names), identifies entry roots, and executes DFS for execution flow.
6. **Architecture Metric Assembly:** `architecture_analyzer.py` counts total files, classes, functions, and directories.
7. **Atomic Persistence:** `repository_store.py` acquires an `RLock`, generates a UUID4 workspace ID (or reuses existing for identical paths), saves the metadata atomically to `repositories.json`, caches the full analysis in memory, and returns the workspace payload.

### Journey B: Ask a Question with Lexical Grounding (`GET /repository/{id}/ask`)
1. **Load Workspace:** `load_repository_or_404` loads the workspace from memory or rebuilds it if missing from cache.
2. **Lexical Retrieval:** `code_search.py` strips stop words, tokenizes the question, expands class hierarchies to include subclass methods, and ranks files and functions by relevance.
3. **Context Assembly & Slicing:** `context_builder.py` takes the top 5 files, slices function bodies with brace-aware depth tracking, caps functions at 60 lines, and numbers every line (`42: def ...`). It then follows the call graph up to 3 calls deep.
4. **Header Extraction:** `main.py` extracts `x-llm-provider`, `x-api-key`, and `x-llm-model` from request headers passed by `api.js`.
5. **Multi-Provider Dispatch:** `llm_service.py` constructs a strict prompt with anti-hallucination rules and dispatches to Gemini, Groq, OpenAI, or local Ollama.
6. **Post-Validation & Grounding:** `validate_citations` scans the LLM's output for `[file:line]`, verifies positional accuracy against context lines, rescues symbol-based citations (`[func:line]`), splits claims, and flags any claims whose distinct identifiers do not appear on the cited line.

### Journey C: Graph Studio & Architecture Navigation
1. The frontend receives the workspace JSON.
2. `Graphs.jsx` builds a Dagre layout model.
3. User selects **LR** (Left-to-Right) or **TB** (Top-to-Bottom) orientation; Dagre recalculates node coordinates `(x, y)` instantly.
4. User clicks **"Connected Only"** or **"Hide Tests"**; the model filters out orphan nodes or test files (`test_*.py`, `.spec.ts`) to present an uncluttered system overview.
5. Clicking any node updates `selectedFile` in `ExplorerPage.jsx`, highlighting the node in obsidian glass and loading the exact file into the syntax viewer.

### Journey D: Cloud Production Deployment (Render)
1. User connects repo to Render via Blueprint (`render.yaml`).
2. Render creates the FastAPI backend web service using `requirements.txt` and starts `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
3. Render creates the frontend static site with `npm run build` and automatically routes the backend URL to `VITE_API_URL`.
4. If the user provides a free Google Gemini or Groq API key, CodeLens immediately runs full AI Q&A in the cloud with zero GPU costs.

---

## Part 1: API Gateway & HTTP Routing (`backend/app/main.py`)

### In One Line
`main.py` is the HTTP front door: it manages CORS, parses dynamic client headers, delegates tasks to service modules, and translates internal exceptions into explicit HTTP status codes (200, 403, 404, 410, 503).

### Key Upgrades & New Capabilities
1. **Dynamic LLM Options Extraction:**
   ```python
   def _extract_llm_options(request: Request) -> dict:
       options = {}
       if provider := request.headers.get("x-llm-provider"):
           options["provider"] = provider
       if api_key := request.headers.get("x-api-key"):
           options["api_key"] = api_key
       if model := request.headers.get("x-llm-model"):
           options["model"] = model
       return options
   ```
   *Why this matters:* Users can switch between Gemini, Groq, OpenAI, or Ollama in the UI without reconfiguring environment variables or restarting the backend.
2. **Diagnostic Endpoints:**
   `GET /health` and `GET /llm/status` report active providers and configured API keys so the UI can warn users before they query a disconnected model.
3. **Clean HTTP Error Differentiation:**
   - `404 Not Found`: Repository ID does not exist in the index.
   - `410 Gone`: Repository metadata exists, but disk files were deleted (instructs the UI to prompt re-analysis).
   - `403 Forbidden`: `read_file` blocked an attempted path traversal escape.

### Interview Talking Point
> *"I designed the route handlers in `main.py` to be thin delegators. All real work resides in pure service functions. Furthermore, I deliberately use synchronous `def` instead of `async def` for handlers that execute blocking I/O (like file reads and outbound requests to LLMs or GitHub). Because FastAPI runs standard `def` routes in an internal `anyio` worker thread pool, slow network calls never block the server's asynchronous event loop."*

---

## Part 2: Ingest & Security Guard

### Files: `github_service.py`, `zip_service.py`, `file_reader.py`

### 1. `github_service.py: clone_repository(url)`
- **Mechanism:** Avoids `git clone`. Formats the URL into `https://github.com/{owner}/{repo}/archive/refs/heads/main.zip` (with fallback to `master.zip`).
- **Extraction:** Downloads the stream, writes to a temporary file in `CODELENS_DATA_DIR`, extracts with Python's standard `zipfile`, and isolates into `tempfile.mkdtemp`.
- **Why no `git clone`?** Container images do not need the `git` binary installed, network payload is reduced (no commit history), and untrusted git hooks (`.git/hooks/`) are never executed.

### 2. `file_reader.py: read_file(repo_path, relative_path)`
Your primary security barrier against Path Traversal:
```python
repo_path = repo_path.resolve()
file_path = (repo_path / relative_path).resolve()
if not file_path.is_relative_to(repo_path):
    raise ValueError("File is outside repository")
return file_path.read_text(encoding="utf-8-sig", errors="replace")
```
- `.resolve()` evaluates all symbolic links and collapses `../` segments into a canonical absolute path.
- `.is_relative_to(repo_path)` mathematically checks if the canonical target is within the workspace boundary. A malicious path like `../../../../etc/passwd` triggers `ValueError` -> converted to `403 Forbidden`.
- `utf-8-sig` silently strips Windows Byte Order Marks (BOM), and `errors="replace"` ensures corrupted or binary bytes render replacement glyphs (``) rather than crashing the worker.

---

## Part 3: Python AST Parser (`code_parser.py`, `repository_parser.py`)

### In One Line
Reads Python source code into an Abstract Syntax Tree (AST) using Python's standard `ast` module, extracting imports, functions, classes, and call sites without executing the file.

### How It Works
1. `ast.parse(source)` compiles the text into an abstract syntax tree.
2. **Top-Level Definitions (`tree.body`):**
   - `ast.Import`: Extracts alias names (`import os, sys`).
   - `ast.ImportFrom`: Extracts module roots (`from app.services import code_search`).
   - `ast.FunctionDef` & `ast.AsyncFunctionDef`: Records name, line number, and positional argument names.
   - `ast.ClassDef`: Extracts class name, base class names (via `_base_names`), and scans inner methods.
3. **Call Extraction (`ast.walk`):**
   - Visits all function definitions (both standard and `async def`).
   - For every `ast.Call`:
     - If `func` is `ast.Name`, callee is `child.func.id` (e.g. `read_file(...)`).
     - If `func` is `ast.Attribute`, callee is `child.func.attr` (e.g. `self.db.write(...)` -> `write`).

### Fixes & Edge Cases Addressed
- **Async Function Support:** Inspects both `ast.FunctionDef` and `ast.AsyncFunctionDef`.
- **Robust Exception Isolation:** Any syntax error (e.g. legacy Python 2 or invalid code) is caught, returning empty definitions rather than terminating the analysis of the entire project.

---

## Part 4: JavaScript & TypeScript Parser (`js_parser.py`) — NEW

### In One Line
A custom, multi-dialect tokenizer extracting architectural primitives from JavaScript, TypeScript, JSX, and TSX files without requiring Node.js or heavy external parsers.

### Why It Was Added
In modern full-stack development, projects routinely combine Python backends with JS/TS frontends or microservices. CodeLens was expanded to support `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, and `.cjs` files.

### Tokenizer Specifications
```python
IMPORT_STATIC_RE = re.compile(
    r"""(?:import|export)\s+(?:[\w*\s{},$]+\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE
)
REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+[\w*\s{},$]+\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE
)
DYNAMIC_IMPORT_RE = re.compile(
    r"""import\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE
)
CLASS_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$.][\w$.]*))?""", re.MULTILINE
)
FUNC_DECL_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function(?:\s+([A-Za-z_$][\w$]*))?\s*\(([^)]*)\)""", re.MULTILINE
)
ARROW_OR_EXPR_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>""", re.MULTILINE
)
METHOD_RE = re.compile(
    r"""^[ \t]+(?:async\s+)?(?:static\s+)?(?:get\s+|set\s+)?([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{""", re.MULTILINE
)
```

### TypeScript Parameter Sanitization (`_clean_args`)
To ensure arguments match Python's schema, TypeScript type signatures and defaults are stripped:
- `user: User = defaultUser` -> `user`
- `...rest: any[]` -> `rest`

### Interview Talking Point
> *"Rather than forcing a heavy Node.js or Tree-Sitter dependency into the Python container, I implemented a robust regex-based static analyzer for JS/TS that matches the exact output schema of the Python AST parser. It extracts CommonJS, ES Modules, dynamic imports, class hierarchies, arrow functions, and method calls while cleaning out TypeScript annotations."*

---

## Part 5: Dependency Analyzer with 4-Tier Fallback (`dependency_analyzer.py`) — UPGRADED

### In One Line
Maps which file imports which other file across the workspace, generating both `forward` ("what do I need?") and `reverse` ("who relies on me?") dependency graphs.

### The Problem in the Previous Version
In the early version, dependency matching used naive exact-path comparison. Only **11 of 31** files in CodeLens resolved dependencies. Intra-package imports (e.g. `from click import core`, `import utils`, or relative imports) failed completely.

### The 4-Tier Fallback Resolution Engine
When resolving an import statement `module`:

```
   Import Statement: "core" inside "src/click/__init__.py"
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  1. Direct Phone Book Lookup                            │
  │     Does "core" exist directly in files?                │ ──► NO
  └──────────────────────────┬──────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  2. Same-Directory Lookup                               │
  │     Check: "{file_dir}/{module}"                        │ ──► MATCH FOUND:
  │     -> "src/click/core" in files!                       │     "src/click/core.py"
  └──────────────────────────┬──────────────────────────────┘
                             │ (if still unresolved)
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  3. Parent-Package Traversal                            │
  │     Walk up package directories:                        │
  │     -> "{parent_dir}/{module}"                          │
  └──────────────────────────┬──────────────────────────────┘
                             │ (if still unresolved)
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  4. Unique Suffix Matching & Extension Resolution       │
  │     Does exactly one key in the repo end with           │
  │     "/{module}" or match extensions (.py/.js/.ts)?      │
  └─────────────────────────────────────────────────────────┘
```

```python
# 1. Exact match
target = files.get(module)

# Fallback 1: Same-directory lookup — {file_dir}/{module}
if not target and file_dir:
    same_dir_key = f"{file_dir}/{module}"
    target = files.get(same_dir_key)

# Fallback 2: Parent-package lookup — walk up to package root
if not target and file_dir:
    dir_parts = file_dir.split("/")
    for i in range(len(dir_parts) - 1, 0, -1):
        pkg_key = "/".join(dir_parts[:i]) + "/" + module
        if pkg_key in files:
            target = files[pkg_key]
            break

# Fallback 3: Suffix-match — exactly one key ending with /{module}
if not target:
    suffix = "/" + module
    matches = [v for k, v in files.items() if k.endswith(suffix)]
    if len(matches) == 1:
        target = matches[0]

# Fallback 4: Extension-based lookup in all_paths
if not target:
    for ext in [".py", ".js", ".jsx", ".ts", ".tsx"]:
        if module + ext in all_paths:
            target = module + ext
            break
```

### Interview Talking Point
> *"By implementing a 4-tier resolution strategy—same-directory lookup, parent-package traversal, unique suffix matching, and extension fallback—we transformed the dependency analyzer from resolving only 35% of files to near 100% resolution across intra-package imports in standard Python and JS architectures."*

---

## Part 6: Call Graph & Execution Flow DFS (`call_analyzer.py`, `repository_analyzer.py`)

### 1. The Call Graph
- **Phone Book Construction:** Creates a dictionary mapping `function_name -> list of {file, line}`.
- **Linker:** For every call site detected by parsers:
  - Non-project symbols (`print`, `len`, external libraries) are skipped.
  - If multiple functions share the same name, all candidates are preserved in `targets`, and `ambiguous: true` is flagged.

### 2. Execution Flow via DFS (`build_execution_flow`)
- **Root Identification:** A root is defined as a function in the entry point file that is **never called by any other function in the repository**. In web frameworks (FastAPI, Express), route handlers are roots because the framework invokes them, not internal code.
- **Depth-First Traversal:**
  ```python
  visited = set()
  def walk(file, function, line):
      key = (file, function)
      if key in visited:
          return
      visited.add(key)
      flow.append({"file": file, "function": function, "line": line})
      for target in call_graph.get(file, {}).get(function, []):
          for dest in target.get("targets", []):
              walk(dest["file"], dest["name"], dest["line"])
  ```
- **Complexity:** $O(V + E)$ time complexity where $V$ is functions and $E$ is calls. Space complexity is $O(V)$ for the `visited` set and recursion stack.

---

## Part 7: Scanner, Architecture Summary & Entry Point Detection

### Entry Point Expansion
Previously limited to 4 hardcoded files, `repository_analyzer.py` now recognizes:
- **Python:** `main.py`, `app.py`, `server.py`, `manage.py`, `cli.py`, `core.py`, `wsgi.py`, `asgi.py`.
- **JavaScript / TypeScript:** `index.js`, `index.ts`, `index.jsx`, `index.tsx`, `main.js`, `main.ts`, `app.js`, `app.ts`.
- **Package Fallback:** If none of the above are present, it selects top-level package initializers (`__init__.py` with path depth $\le 3$).

---

## Part 8: Persistence & Workspace Store (`repository_store.py`)

### The Architecture Rule
- **Metadata is Precious, Saved to Disk:** `repositories.json` stores `{repository_id, name, path, created_at, last_opened_at}`.
- **Analysis is Derived, Cached in Memory:** Graphs, ASTs, and trees can always be recomputed from source files on disk. Keeping them in an in-memory dictionary `repositories = {}` keeps the JSON index tiny and prevents stale cache bugs when analyzer logic updates.

### Atomic Swaps with `os.replace`
```python
path = _index_path()
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(_load_index(), indent=2), encoding="utf-8")
os.replace(tmp, path)
```
*Why this matters:* If the operating system or container crashes while writing JSON, `os.replace` guarantees POSIX atomicity: readers see either the old valid index or the new complete index, never a truncated half-written file.

---

## Part 9: Code Search & Lexical Retrieval (`code_search.py`)

### In One Line
A deterministic lexical retrieval engine combining whole-word keyword matching, function signature weighting, and class inheritance expansion.

### Search Pipeline
1. **Keyword Normalization:** Converts query to lowercase, extracts identifiers `[A-Za-z_][A-Za-z0-9_]*`, and drops common question stop words (`how`, `why`, `explain`, `does`).
2. **Path Match Boost:** Explicit filenames in queries (e.g. `main.py`) receive top priority.
3. **Class Inheritance Expansion:** If a query mentions a base class (e.g. `Command`), `_related_classes` traverses subclasses (e.g. `Group`), promoting methods like `Group.invoke` even if their function bodies do not explicitly contain the keyword `Command`.
4. **Scoring Model:**
   - **Name Match:** Keyword matches function/class name directly $\rightarrow$ Relevance `1000`, File Weight `3`.
   - **Inherited Method:** Subclass method matching class query $\rightarrow$ Relevance `999`.
   - **Body Match:** Keywords appearing in function body $\rightarrow$ Distinct keywords + signature boost, Weight `5`.
   - **Import Match:** Keyword appears in an import path $\rightarrow$ Relevance `1`, Weight `1`.

---

## Part 10: Context Builder & Brace-Aware Code Slicing (`context_builder.py`) — UPGRADED

### In One Line
Compiles line-numbered source code snippets from ranked search results, enforcing strict size budgets and following call chains.

### Slicing with Brace-Depth Tracking
In previous versions, function slicing used Python indentation alone. When given multi-line parameter lists or JavaScript/TypeScript code, functions were truncated prematurely. 

`context_builder.py` now tracks curly brace depth for C-style languages:
```python
first_chunk = "".join(lines[start:min(start + 3, len(lines))])
if "{" in first_chunk:
    depth = 0
    started = False
    for i in range(start, len(lines)):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        if "{" in line:
            started = True
        if started and depth <= 0:
            return "\n".join(lines[start:i + 1])
```

### Hard Context Budgets
- `MAX_CONTEXT_FILES = 5`: Limits context to top 5 files.
- `MAX_ENTRIES_PER_FILE = 40`: Caps code blocks per file.
- `MAX_SOURCE_LINES = 60`: Functions longer than 60 lines are cleanly truncated with `... (N more lines omitted)`.
- `MAX_EXPANSION_MATCHES = 3`: Only top 3 matches per file follow call chains.

---

## Part 11: Multi-Provider LLM Engine & Citation Verifier (`llm_service.py`) — UPGRADED

### In One Line
Dispatches structured context to local or cloud LLMs and subjects every generated sentence to lexical citation and claim validation.

### Multi-Provider Architecture
```
                         ┌───────────────────────────┐
                         │   Request / Main Route    │
                         └─────────────┬─────────────┘
                                       │ (Headers: x-llm-provider, x-api-key, x-llm-model)
                                       ▼
                         ┌───────────────────────────┐
                         │    _invoke_model Dispatch │
                         └─────────────┬─────────────┘
                                       │
         ┌───────────────────┬─────────┴─────────┬───────────────────┐
         ▼                   ▼                   ▼                   ▼
 ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
 │ Google Gemini │   │     Groq      │   │    OpenAI     │   │ Local Ollama  │
 │ (1.5 Flash /  │   │  (Llama 3.3   │   │  (GPT-4o /    │   │ (Qwen 2.5     │
 │    Pro)       │   │    70B)       │   │   Mini)       │   │    Coder)     │
 └───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

- **Google Gemini:** Native integration using `generativelanguage.googleapis.com` (free cloud AI option).
- **Groq:** Ultra-low latency inference using OpenAI-compatible API with `temperature: 0.2`.
- **OpenAI:** GPT-4o / GPT-4o-mini with custom `base_url` support for OpenRouter or enterprise proxies.
- **Local Ollama:** Default fallback for private offline code analysis.

### Lexical Citation Verification Pipeline (`validate_citations`)
1. **Citation Extraction:** Scans output for `[file:line]`.
2. **Positional Validation:** Checks whether the retrieved code contains that exact line number.
3. **Symbol Rescue:** If the model wrote `[invoke:204]`, resolves `invoke` to its real file path (`[src/click/core.py:204]`).
4. **Sentence Splitting:** Breaks answer into individual claims.
5. **Identifier Support Check:** For each claim with a citation, extracts distinctive identifiers (words with underscores, camelCase, or length $\ge 6$). All distinctive words must appear in the cited function's source. If missing $\rightarrow$ claim is moved to the **Flagged** section.

---

## Part 12: Modern Frontend Architecture & Graph Studio (`frontend/src/`) — UPGRADED

### 1. Dynamic API Overrides (`api.js`)
Frontend can run on a static CDN (like Render or Vercel) while communicating with a backend running locally or in the cloud. Users can set or change the backend API URL directly in the UI without rebuilding the frontend bundle.

### 2. Graph Studio Overhaul (`Graphs.jsx`)
- **Obsidian Glass Nodes:** Semi-transparent dark cards showing file names, directory breadcrumbs, and member counts.
- **RankDir Toggles:** Switch layout between **LR** (Left-to-Right) and **TB** (Top-to-Bottom) with Dagre layout recalculations.
- **Noise Elimination:**
  - `connectedOnly`: Hides isolated nodes with zero edges to focus on core architecture.
  - `hideTests`: Removes `test_*.py` and `*.spec.ts` files from graph clutter.
- **Execution Flow Timing:** Directed edges animate with staggered CSS delays (`index * -0.32s`), illustrating execution travel.

### 3. AI Companion Drawer (`AiCompanion.jsx`)
- Slide-out glass drawer showing streaming-ready Q&A, active provider badges, verified citation tags, and unverified warnings.

---

## Part 13: Cloud Deployment, Docker & Render (`render.yaml`, `DEPLOYMENT.md`) — NEW

### Render Infrastructure as Code (`render.yaml`)
```yaml
services:
  - type: web
    name: codelens-backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: CODELENS_DATA_DIR
        value: /tmp/codelens_data
      - key: CODELENS_CORS_ORIGINS
        value: "*"
    healthCheckPath: /health

  - type: web
    name: codelens-frontend
    runtime: static
    buildCommand: cd frontend && npm install && npm run build
    staticPublishPath: ./frontend/dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_API_URL
        fromService:
          type: web
          name: codelens-backend
          property: url
```

---

## Part 14: Automated Testing & Test Suite Architecture

### Test Statistics
- **76+ Unit Tests Passing** across 8 dedicated test suites in Python `unittest`.
- Executed via:
  ```bash
  python -c "import sys, unittest; sys.path.insert(0, 'backend'); runner = unittest.TextTestRunner(verbosity=2); suite = unittest.defaultTestLoader.loadTestsFromNames(['test_answer_grounding', 'test_context_resolution', 'test_cors_storage_config', 'test_inheritance_retrieval', 'test_js_parser', 'test_repository_parser', 'test_repository_persistence', 'test_search_retrieval']); runner.run(suite)"
  ```

### Test Coverage Highlights
1. `test_answer_grounding.py`: Positional line checks, symbol rescues, flagged vs. verified claims.
2. `test_js_parser.py`: Multi-language tokenization, TS parameter type stripping, arrow functions.
3. `test_repository_persistence.py`: Atomic JSON writes, 404 vs 410 error codes, workspace re-analysis.
4. `test_inheritance_retrieval.py`: Base class promotion, queue-based traversal cycle prevention.

---

## Part 15: The Weakness-Fix Matrix (Interview Stories: Before vs. After)

Interviewers love hearing: *"I measured a flaw, found the root cause, and re-engineered it."*

| # | What Was Broken Before | How I Diagnosed & Measured It | The Structural Solution |
|---|---|---|---|
| **1** | Only Python was analyzed. | Full-stack repos with React or Node showed empty dependency graphs. | Built `js_parser.py` with custom regex tokenizers matching the Python AST schema. |
| **2** | Dependent files resolved only 11 of 31 cases. | Ran CodeLens on its own backend; intra-package imports failed exact-string match. | Implemented 4-tier fallback: same-directory, parent-package, unique suffix, and extension matching. |
| **3** | Function slicing lost code on multi-line signatures. | Functions formatted with Black formatter had bodies truncated at the closing paren. | Added brace-depth tracking `{}` for C-style/JS code and line-boundary detection for Python. |
| **4** | Hard dependency on local Ollama GPU. | Deploying to free cloud tiers (Render) failed because Ollama was unavailable. | Added multi-provider dispatch for Gemini, Groq, and OpenAI via HTTP headers and UI settings. |
| **5** | Hardcoded Windows storage paths. | `E:/CodeLensData` broke when running on Linux containers. | Environment variable normalization: defaults to `/tmp/codelens_data` in cloud deployments. |
| **6** | Graph visualizer cluttered by test files. | Testing suites with 50 test files crowded out core architecture nodes. | Added interactive "Hide Tests" and "Connected Only" filter toggles in Graph Studio. |

---

## Part 16: Honest Limits & What to Say Like a Senior Engineer

1. **Static Analysis is an Approximation:**
   > *"Static analysis cannot evaluate runtime values, dynamic `getattr()` calls, or polymorphic monkey-patching. I don't pretend it's perfect—I explicitly flag ambiguous edges and explain to users that execution flow is a static approximation."*
2. **Lexical Grounding is Not Full Semantic Proof:**
   > *"The citation checker verifies lexical presence: it ensures the cited line exists and the named identifiers appear in that code block. It prevents hallucinations of fake functions and imaginary line numbers, but it does not formally verify logic semantics."*
3. **Single-Worker In-Memory Store:**
   > *"The current workspace cache uses an in-memory dictionary guarded by an `RLock`. If scaled across multiple Uvicorn worker processes or cluster nodes, this cache layer should be extracted to Redis, and metadata moved from `repositories.json` to PostgreSQL."*

---

## Part 17: Claims You Can Make vs. Claims You Must Never Make

| ✅ SAFE TO CLAIM (Supported by Code) | ❌ DO NOT CLAIM (Not in Codebase) |
|---|---|
| Multi-language static analysis (Python AST + JS/TS tokenizer) | Full Tree-Sitter semantic AST for JavaScript |
| Lexical RAG with whole-word matching & subclass expansion | Vector embeddings or vector databases (Pinecone, Chroma) |
| Multi-provider LLM support (Ollama, Gemini, Groq, OpenAI) | Autonomous multi-agent swarm architecture |
| Atomic JSON writes and path traversal security guards | Multi-tenant user auth database (Postgres/Supabase) |
| 4-tier dependency resolution with forward/reverse graphs | Dynamic runtime tracing / execution profiling |
| Dagre layout with orientation & connected-only filtering | WebSockets or real-time streaming tokens |
| 76+ automated regression tests | 100% test coverage across all UI edge-cases |

---

## Part 18: Master Interview Question Bank with High-Scoring Answers

### Q1: How does CodeLens parse code without running it?
**Answer:**
*"We use static analysis. For Python, we parse source code into an Abstract Syntax Tree using Python's standard `ast` module. For JavaScript and TypeScript, we use a regex-based tokenizer in `js_parser.py` that extracts imports, exports, classes, functions, arrow methods, and calls. Because the code is never executed or imported into the runtime, hostile code cannot execute attacks on the server, and repos don't need their dependencies installed."*

### Q2: Why did you choose lexical retrieval over vector embeddings for RAG?
**Answer:**
*"Code contains strong, unambiguous signal in symbol names and class hierarchies. Lexical retrieval is deterministic, lightweight, fast, and easy to debug. It requires no external vector database or embedding model, allowing CodeLens to run completely offline. To overcome lexical keyword limitations, I added class inheritance expansion so queries for base classes retrieve subclass implementations, and signature weighting so function headers outrank body mentions."*

### Q3: How do you prevent and catch LLM hallucinations?
**Answer:**
*"Through defense in depth across 5 layers: First, narrow retrieval to only top-relevant functions. Second, number every source line explicitly. Third, provide strict prompt rules forbidding external assumptions. Fourth, run a post-generation citation verifier that validates line existence and symbol presence, flagging unsupported claims. Fifth, enforce a refusal path if retrieval finds no relevant code."*

### Q4: How does your dependency analyzer resolve intra-package imports?
**Answer:**
*"Standard import strings often don't match file paths directly. I designed a 4-tier resolution engine: first, direct path lookup; second, same-directory lookup (`{file_dir}/{module}`); third, walking up parent package directories; and fourth, unique suffix matching across the workspace. This increased dependency resolution from 35% to nearly 100% on complex modular repositories."*

### Q5: How is CodeLens deployed to the cloud?
**Answer:**
*"We use a Render Blueprint (`render.yaml`) orchestrating a FastAPI backend web service and a React Vite static site. Configuration is handled through environment variables, with health checks running on `/health`. For AI inference in the cloud, CodeLens integrates directly with Google Gemini and Groq APIs, while frontend users can dynamically override the backend API URL and provide their own API keys via client settings."*
