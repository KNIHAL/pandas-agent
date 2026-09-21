last updated: 2026-09-21

# Decisions Log (append-only, dated, short)

- 2026-09-20 — Dropping CrewAI, building agent loop from scratch in Python. Why: no dependency on any agentic framework, full control over reasoning/tool-selection loop.
- 2026-09-20 — Adopted docs/ structure (OVERVIEW, HOW_TO_WORK, STATUS, DECISIONS, modules/*) for per-module dedicated chats. Why: avoid re-feeding full spec every chat, save tokens, keep each module self-contained.
- 2026-09-20 — Reuse `core/chart_generators/*` as-is (no CrewAI/MCP coupling in that code). Why: clean OOP, framework-independent already.
- 2026-09-20 — Module code directories use snake_case (e.g. `tool_gateway/`), not the kebab-case used by `docs/modules/<name>/`. Why: Python can't import a hyphenated package name; snake_case is the only workable choice for every future module's code dir.
- 2026-09-20 — `ToolGateway.get_contract(name)` added after tool-gateway was marked done, while building agent-core's Tool Gateway hook-up. Why: agent-core needs the full `ToolContract` (not just names from `list_tools()`) to build LLM-facing `ToolSpec`s.
- 2026-09-21 — execution-backend: legacy `core/execution.py` NOT reused — substring blacklist trivially bypassable, no timeout/memory/network limits, ad-hoc output shape. Rebuilt from scratch as `execution_backend/`.
- 2026-09-21 — LocalExecutor security = AST pre-check (validator.py, import allowlist + blocked builtin names + blocked dunder attrs) + restricted `__builtins__` in the exec'd subprocess, as defense-in-depth. Why: neither alone is sufficient — AST catches static patterns, restricted builtins narrows the runtime surface even if something slips past the AST check.
- 2026-09-21 — Timeout + memory limits enforced via subprocess (not threads), since Windows can't cap a thread's memory. Parent polls RSS via psutil and kills on breach.
- 2026-09-21 — Memory polling sums RSS across the whole process tree, not just the spawned PID. Why: on this machine, `.venv\Scripts\python.exe` is a launcher stub that re-execs the real interpreter as a child — monitoring only the parent PID measured ~4MB flat while the actual worker (with pandas imported + user allocations) ran in a grandchild process, silently defeating the memory limit.
- 2026-09-21 — Approved libs for V1: pandas, numpy, matplotlib, duckdb, scipy. statsmodels deliberately deferred until a specific module (investigation-engine) needs it.
