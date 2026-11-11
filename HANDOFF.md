# CodeLens — Project Handoff

Paused for later resume. This note reflects the actual repository state inspected on
2026-10-12 (not prior summaries).

- Git branch: `main`, tracking `origin/main`, up to date with it.
- Latest commit: `7665db1` (2026-10-11) "Improve code retrieval and LLM answer accuracy".
- **All Batch 1–3 work is UNCOMMITTED** (working-tree changes only). Nothing was staged,
  committed, or pushed by this session. See section 6.

---

## 1. Project architecture

**Frontend — React + Vite**
- React 19 + Vite 8 (`@vitejs/plugin-react`); graph UI via `@xyflow/react` + `@dagrejs/dagre`;
  code highlighting via `react-syntax-highlighter`. See `frontend/package.json`.
- Entry: `frontend/src/main.jsx` -> `frontend/src/App.jsx`.
- Backend base URL hardcoded in `frontend/src/App.jsx:9` -> `http://127.0.0.1:8000`.
- Vite config is default-only (`frontend/vite.config.js`); no dev proxy is configured.

**Backend — FastAPI**
- `backend/app/main.py` defines the FastAPI `app` (variable name: `app`).
- CORS allows `http://localhost:5173` (`backend/app/main.py:26`).
- Endpoints: `analyze/github`, `analyze/zip`, `file`, `repository/{id}`,
  `.../dependencies`, `.../call-graph`, `.../flow`, `.../search`, `.../context`,
  `.../ask`, `.../summary`, plus `/` and `/health`.

**Repository ingestion / parsing**
- `github_service.clone_repository`, `zip_service.extract_zip`,
  `repository_scanner.scan_repository`, `file_reader.read_file` (path-safety),
  `repository_store` (in-memory save/get).
- `code_parser.parse_python_file` uses the Python `ast` module (`import ast`, `ast.parse`)
  to extract functions, classes, methods, imports.
- `repository_parser.parse_repository` aggregates per-file analysis into `code_analysis`.
- `dependency_analyzer`, `architecture_analyzer` produce dependency/architecture metadata.

**Code search / context retrieval**
- `code_search.search_code(code_analysis, query, repo_path=None)` ranks files/matches.
- `context_builder.build_context(...)` selects source snippets for the LLM;
  `build_project_context(...)` builds the whole-project summary payload.
- Cross-file call relationships: `call_analyzer.build_call_graph` /
  `build_execution_flow` / `resolve_call_targets`.

**LLM integration — Ollama**
- `llm_service.ask_llm` and `llm_service.summarize_project` POST to
  `http://127.0.0.1:11434/api/generate` with model `qwen2.5-coder:3b`
  (`backend/app/services/llm_service.py:114-118` and `:185-188`).

---

## 2. Local development commands and model configuration

Verified from repository:
- Frontend scripts (`frontend/package.json`): `npm run dev` (Vite dev server, default
  `http://localhost:5173`), `npm run build`, `npm run lint`, `npm run preview`.
  Install with `npm install` in `frontend/`.
- Model/config: `qwen2.5-coder:3b` at `http://127.0.0.1:11434/api/generate` (Ollama).
- Tests use the Python standard library `unittest`. `pytest` is **not** installed
  (verified: `No module named pytest`). Run tests from `backend/` because imports use
  `app.services...`.
- Python 3.12.4.

UNVERIFIED (not defined in the repository):
- Backend run command. There is **no** `requirements.txt`, `pyproject.toml`, or run
  script. Inferred only (verify before use): from `E:\CodeLens`,
  `uvicorn backend.app.main:app --reload` (the code imports `from backend.app...`, so
  the process cwd must be the project root). Backend dependency list is likewise
  unverified; source imports include `fastapi`, `requests`, and multipart uploads
  (`python-multipart` is typically required for `UploadFile`).
- Whether Ollama is currently installed/running locally.

---

## 3. Completed work (Batches 1–3) — all UNCOMMITTED

**Batch 1 — call-chain resolution**
- `backend/app/services/call_analyzer.py`: call edges carry `targets`/`ambiguous`;
  added `resolve_call_targets(call)`; execution flow follows all candidate targets.
- `backend/app/services/context_builder.py`: method-aware `find_function_definition`,
  indentation-aware `get_function_source`, follows all call candidates.

**Batch 2 — natural-language retrieval**
- `backend/app/services/code_search.py`: `search_code(code_analysis, query, repo_path=None)`;
  body/docstring matching, weighted scoring, canonical (last-`def`) lines, deterministic ranking.
- `backend/app/services/context_builder.py`: size caps (`MAX_CONTEXT_FILES=5`,
  `MAX_ENTRIES_PER_FILE=40`, `MAX_SOURCE_LINES=60`), `_cap_source`, `_unique_code`;
  matched definitions surfaced before call-chain expansion.
- `backend/app/main.py`: `/context` and `/ask` now pass `repository["path"]` to `search_code`.
- `backend/app/services/llm_service.py`: prompt rules distinguishing shell/OS execution,
  framework command dispatch, and name-only "command" matches.

**Batch 3 — search precision, relevance ranking, grounding, citation honesty**
- `backend/app/services/code_search.py`: regex tokenizer, `\b...\b` word-boundary matching,
  expanded `STOP_WORDS`, per-function body relevance (header/docstring weighted),
  name-match relevance `1000`, promotion of methods belonging to a query-named class,
  and a boolean `named` signal set **only** when the query clearly identifies a repo path
  (no arbitrary score inflation).
- `backend/app/services/context_builder.py`: `_prioritized_matches` caps entries by
  relevance (named functions and source-body evidence), never by line number alone.
- `backend/app/services/llm_service.py`: extracted `build_prompt` with grounding rules
  ("answer strictly from Source blocks", "do not rely on prior knowledge", "if the named
  body is absent, say the context does not contain it"); `validate_citations` now marks
  citations not present in the retrieved source as
  `[path:line (unverified: line not in retrieved source)]` and appends a `Note:` instead
  of silently deleting them. Documented as an allow-list check, not semantic validation.
- Tests added: `backend/test_context_resolution.py` (Batch 1),
  `backend/test_search_retrieval.py` (Batch 2), `backend/test_answer_grounding.py` (Batch 3).

---

## 4. Regression tests and results (rerun just now)

Command 1 (relevant regression suites):
```
cd E:\CodeLens\backend
python -m unittest test_context_resolution test_search_retrieval test_answer_grounding
```
Result: `Ran 21 tests ... OK` (exit 0).
Breakdown: `test_context_resolution` = 8, `test_search_retrieval` = 4,
`test_answer_grounding` = 9.

Command 2 (import sanity):
```
cd E:\CodeLens
python -c "import backend.app.main"
```
Result: imports successfully (prints `import backend.app.main OK` in the wrapper used).

Caveat: `python -m unittest discover` is **not safe** here. The pre-existing
`backend/test_*.py` files (`test_code_parser.py`, `test_file_reader.py`,
`test_repository_parser.py`, `test_zip_service.py`, `test_github_service.py`) are
script-style (print-based; some clone a remote repo or extract zips). Discovery hung and
was terminated. Only the three unittest modules above constitute the regression suite.

---

## 5. Known limitations

- **Retrieval may omit `Group.invoke`** (`src/click/core.py:2052`) for broad Click queries.
  Class-hierarchy data (base classes) is not parsed, so methods of subclasses of a
  query-named class are not promoted.
- **Citation checking is positional, not semantic.** `validate_citations` only verifies
  that a cited file and line were retrieved into context; it does **not** verify that the
  cited source supports the claim. It is not semantic validation.
- **Live answer quality with `qwen2.5-coder:3b` has not been verified** by these tests.
  The regression tests assert retrieval, prompt content, and citation handling only; no
  test calls the live model.

---

## 6. Git state (committed vs uncommitted)

Committed:
- Branch `main` at `7665db1` (2026-10-11) "Improve code retrieval and LLM answer accuracy",
  up to date with `origin/main`. This commit contains an earlier, naive `search_code`
  (whitespace/substring matching, no `repo_path`) and a `method` branch in `build_context`.
  It does **not** contain the Batch 3 precision work or the citation validator.

Uncommitted — modified (working tree):
- `backend/app/main.py`
- `backend/app/services/call_analyzer.py`
- `backend/app/services/code_search.py`
- `backend/app/services/context_builder.py`
- `backend/app/services/llm_service.py`
- `frontend/src/App.css`
- `frontend/src/App.jsx`

Uncommitted — untracked:
- `backend/test_context_resolution.py`
- `backend/test_search_retrieval.py`
- `backend/test_answer_grounding.py`

Notes:
- The frontend changes (`App.css`, `App.jsx`) predate and are outside Batches 1–3; they
  were not touched by this work.
- Nothing is staged. Nothing has been committed or pushed.

---

## 7. Suggested next steps (priority order)

1. **Retrieve command-dispatch functions reliably.** Parse base classes in
   `code_parser`/`repository_parser`, then promote (or otherwise ensure inclusion of)
   methods such as `Group.invoke` when a superclass like `Command` is named in the query.
   Add a regression test using a subclass fixture.
2. **Verify real LLM answers end-to-end.** With Ollama running (`qwen2.5-coder:3b`), run
   the two motivating questions against the Click repo and inspect citations and
   grounding. Add an opt-in integration test that skips when Ollama is unavailable
   (do not make network calls part of the default suite).
3. **Reduce test-file noise** for implementation questions so `src/` modules are not
   crowded out by test files.
4. **Commit the uncommitted Batch 1–3 work** once reviewed (not done here).

---

### Reproduce / verify index

- Retrieval + context: `backend/app/services/code_search.py`,
  `backend/app/services/context_builder.py`.
- Call graph: `backend/app/services/call_analyzer.py`.
- Prompt + citations: `backend/app/services/llm_service.py`.
- Endpoints: `backend/app/main.py`.
- Tests: `backend/test_context_resolution.py`, `backend/test_search_retrieval.py`,
  `backend/test_answer_grounding.py`.
