last updated: 2026-09-20

# agent-core — Progress

Branch `feature/agent-core`, created off `feature/tool-gateway` (agent-core
needs to import `tool_gateway`, which isn't merged to the base branch yet).

- `agent_core/messages.py` — `Role`, `Message`, `ToolCallRequest`, `ToolSpec`,
  `Usage`, `LLMResponse` (pydantic v2). Provider-agnostic wire types; no
  provider SDK types leak past the adapter boundary.
- `agent_core/llm_provider.py` — abstract `LLMProvider.complete()` + `LLMProviderError`
  (adapters must wrap SDK exceptions in this).
- Tests: `tests/test_agent_core_messages.py`, 12/12 passing.
- `agent_core/providers/gemini.py` — `GeminiProvider`, backed by the new
  `google-genai` SDK (NOT the deprecated `google-generativeai` package).
  Translation kept as standalone functions (`_to_gemini_contents`,
  `_to_gemini_tools`, `_from_gemini_response`) so they're unit-testable
  without a network call. `complete()` wraps every SDK/parsing exception in
  `LLMProviderError`.
- Tests: `tests/test_agent_core_gemini.py`, 13/13 passing, all against a
  mocked `genai.Client` — no API key needed/used.
- Next: Claude adapter, then Groq adapter — one at a time, each fully
  tested before the next (same discipline as tool-gateway). No live-API
  testing here (no keys configured in this environment); live testing is
  Kumar's call once he has keys set.
