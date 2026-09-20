last updated: 2026-09-20

# Decisions Log (append-only, dated, short)

- 2026-09-20 — Dropping CrewAI, building agent loop from scratch in Python. Why: no dependency on any agentic framework, full control over reasoning/tool-selection loop.
- 2026-09-20 — Adopted docs/ structure (OVERVIEW, HOW_TO_WORK, STATUS, DECISIONS, modules/*) for per-module dedicated chats. Why: avoid re-feeding full spec every chat, save tokens, keep each module self-contained.
- 2026-09-20 — Reuse `core/chart_generators/*` as-is (no CrewAI/MCP coupling in that code). Why: clean OOP, framework-independent already.
